# -*- coding: utf-8 -*-
"""把官方 PP-OCRv6 ONNX 模型整理成可发布的 runtime/ocr。"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OCR 构建环境缺少 PyYAML；请先安装 requirements-ocr-build.txt"
        ) from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"模型配置不是 YAML 对象：{path}")
    return data


def _transform(config: dict[str, Any], name: str) -> dict[str, Any]:
    operations = config.get("PreProcess", {}).get("transform_ops", [])
    for operation in operations:
        if isinstance(operation, dict) and name in operation:
            value = operation[name]
            return value if isinstance(value, dict) else {}
    raise ValueError(f"模型配置缺少预处理步骤：{name}")


def _number(value: Any) -> float:
    if isinstance(value, str) and "/" in value:
        numerator, denominator = value.rstrip(".").split("/", 1)
        return float(numerator.rstrip(".")) / float(denominator.rstrip("."))
    return float(value)


def _read_varint(data: bytes, position: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while position < len(data) and shift < 70:
        byte = data[position]
        position += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, position
        shift += 7
    raise ValueError("ONNX protobuf varint 损坏")


def _protobuf_fields(data: bytes):
    position = 0
    while position < len(data):
        tag, position = _read_varint(data, position)
        field, wire = tag >> 3, tag & 7
        if wire == 0:
            value, position = _read_varint(data, position)
        elif wire == 1:
            value, position = data[position : position + 8], position + 8
        elif wire == 2:
            size, position = _read_varint(data, position)
            value, position = data[position : position + size], position + size
        elif wire == 5:
            value, position = data[position : position + 4], position + 4
        else:
            raise ValueError(f"ONNX protobuf 使用了不支持的 wire type：{wire}")
        if position > len(data):
            raise ValueError("ONNX protobuf 字段越界")
        yield field, wire, value


def _read_opsets(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for field, wire, payload in _protobuf_fields(path.read_bytes()):
        if field != 8 or wire != 2:
            continue
        domain = "ai.onnx"
        version: int | None = None
        for sub_field, sub_wire, value in _protobuf_fields(payload):
            if sub_field == 1 and sub_wire == 2:
                domain = value.decode("utf-8") or "ai.onnx"
            elif sub_field == 2 and sub_wire == 0:
                version = int(value)
        if version is not None:
            result[domain] = version
    if "ai.onnx" not in result:
        raise ValueError(f"ONNX 文件没有默认 opset：{path}")
    return result


def _inspect_onnx(path: Path) -> dict[str, Any]:
    try:
        import onnxruntime as ort
    except ModuleNotFoundError as exc:
        raise RuntimeError("OCR 构建环境缺少 ONNX Runtime") from exc
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    inputs, outputs = session.get_inputs(), session.get_outputs()
    if len(inputs) != 1 or len(outputs) != 1:
        raise ValueError(f"OCR ONNX 必须各有一个输入和输出：{path}")
    model_input, model_output = inputs[0], outputs[0]
    return {
        "input_name": model_input.name,
        "input_shape": list(model_input.shape),
        "input_type": model_input.type,
        "output_name": model_output.name,
        "output_shape": list(model_output.shape),
        "output_type": model_output.type,
        "opsets": _read_opsets(path),
    }


def _fixed_dimension(shape: list[Any], index: int) -> int | None:
    try:
        value = shape[index]
    except IndexError:
        return None
    return value if isinstance(value, int) and value > 0 else None


def _validate_models(
    det_info: dict[str, Any],
    rec_info: dict[str, Any],
    rec_shape: list[int],
    characters: list[str],
) -> None:
    if det_info["input_type"] != "tensor(float)" or det_info["output_type"] != "tensor(float)":
        raise ValueError("检测 ONNX 输入输出必须是 float tensor")
    if rec_info["input_type"] != "tensor(float)" or rec_info["output_type"] != "tensor(float)":
        raise ValueError("识别 ONNX 输入输出必须是 float tensor")
    if len(det_info["input_shape"]) != 4 or _fixed_dimension(det_info["input_shape"], 1) != 3:
        raise ValueError(f"检测 ONNX 输入规格不兼容：{det_info['input_shape']}")
    if len(det_info["output_shape"]) != 4 or _fixed_dimension(det_info["output_shape"], 1) != 1:
        raise ValueError(f"检测 ONNX 输出规格不兼容：{det_info['output_shape']}")
    if len(rec_info["input_shape"]) != 4:
        raise ValueError(f"识别 ONNX 输入规格不兼容：{rec_info['input_shape']}")
    if _fixed_dimension(rec_info["input_shape"], 1) != rec_shape[0]:
        raise ValueError("识别 ONNX 通道数与 YML 不一致")
    if _fixed_dimension(rec_info["input_shape"], 2) != rec_shape[1]:
        raise ValueError("识别 ONNX 高度与 YML 不一致")
    class_count = _fixed_dimension(rec_info["output_shape"], -1)
    if class_count is not None and class_count != len(characters) + 1:
        raise ValueError(
            f"识别字符表与 ONNX 类别数不一致：{len(characters)}+1 != {class_count}"
        )


def _model_version(det_name: str, rec_name: str, override: str) -> str:
    if override:
        return override
    det_base = det_name.removesuffix("_det")
    rec_base = rec_name.removesuffix("_rec")
    if det_base != rec_base:
        raise ValueError(f"检测与识别模型系列不同：{det_name} / {rec_name}")
    return det_base.replace("_", "-")


def _rec_max_width(config: dict[str, Any], default: int) -> int:
    shapes = (
        config.get("Hpi", {})
        .get("backend_configs", {})
        .get("paddle_infer", {})
        .get("trt_dynamic_shapes", {})
        .get("x", [])
    )
    widths = [shape[-1] for shape in shapes if isinstance(shape, list) and shape and isinstance(shape[-1], int)]
    return max([default, *widths])


def _supported_scripts(characters: list[str]) -> list[str]:
    codepoints = {ord(char) for item in characters for char in item}
    ranges = (
        ("latin", ((0x0041, 0x007A),)),
        ("han", ((0x3400, 0x9FFF),)),
        ("kana", ((0x3040, 0x30FF),)),
        ("hangul", ((0xAC00, 0xD7AF),)),
    )
    return [
        name
        for name, blocks in ranges
        if any(start <= point <= end for point in codepoints for start, end in blocks)
    ]


def _build_manifest(args, det_cfg: dict[str, Any], rec_cfg: dict[str, Any]) -> tuple[dict, bytes]:
    det_name = str(det_cfg.get("Global", {}).get("model_name") or "").strip()
    rec_name = str(rec_cfg.get("Global", {}).get("model_name") or "").strip()
    if not det_name.endswith("_det") or not rec_name.endswith("_rec"):
        raise ValueError("YML 缺少有效的检测/识别 model_name")

    post = det_cfg.get("PostProcess", {})
    if post.get("name") != "DBPostProcess":
        raise ValueError(f"仅支持 DBPostProcess，实际为 {post.get('name')}")
    decoder = rec_cfg.get("PostProcess", {})
    if decoder.get("name") != "CTCLabelDecode":
        raise ValueError(f"仅支持 CTCLabelDecode，实际为 {decoder.get('name')}")
    characters = decoder.get("character_dict")
    if not isinstance(characters, list) or not characters or not all(isinstance(item, str) for item in characters):
        raise ValueError("识别 YML 缺少有效 character_dict")
    characters = list(characters)
    if " " not in characters:
        characters.append(" ")

    decode = _transform(det_cfg, "DecodeImage")
    normalize = _transform(det_cfg, "NormalizeImage")
    rec_resize = _transform(rec_cfg, "RecResizeImg")
    rec_shape = [int(value) for value in rec_resize.get("image_shape", [])]
    if len(rec_shape) != 3 or min(rec_shape) <= 0:
        raise ValueError(f"识别 YML image_shape 无效：{rec_shape}")

    det_info = _inspect_onnx(args.det)
    rec_info = _inspect_onnx(args.rec)
    _validate_models(det_info, rec_info, rec_shape, characters)
    det_opset = det_info["opsets"]["ai.onnx"]
    rec_opset = rec_info["opsets"]["ai.onnx"]

    character_bytes = ("\n".join(characters) + "\n").encode("utf-8")
    manifest = {
        "schema_version": 1,
        "model_version": _model_version(det_name, rec_name, args.model_version),
        "opset": {"det": det_opset, "rec": rec_opset},
        "opsets": {"det": det_info["opsets"], "rec": rec_info["opsets"]},
        "source": {
            "det_model_name": det_name,
            "rec_model_name": rec_name,
            "det_config_sha256": _sha256(args.det_yml),
            "rec_config_sha256": _sha256(args.rec_yml),
            "supported_scripts": _supported_scripts(characters),
        },
        "files": {
            "det.onnx": {"sha256": _sha256(args.det), "size": args.det.stat().st_size},
            "rec.onnx": {"sha256": _sha256(args.rec), "size": args.rec.stat().st_size},
            "characters.txt": {
                "sha256": hashlib.sha256(character_bytes).hexdigest(),
                "size": len(character_bytes),
            },
        },
        "det": {
            "input_name": det_info["input_name"],
            "output_name": det_info["output_name"],
            "input_shape": det_info["input_shape"],
            "output_shape": det_info["output_shape"],
            "resize": {
                "limit_side_len": args.det_limit_side_len,
                "limit_type": args.det_limit_type,
                "multiple": args.det_multiple,
            },
            "normalize": {
                "scale": _number(normalize.get("scale", 1.0 / 255.0)),
                "mean": [_number(value) for value in normalize.get("mean", [])],
                "std": [_number(value) for value in normalize.get("std", [])],
                "channel_order": str(decode.get("img_mode", "BGR")).lower(),
            },
            "postprocess": {
                "thresh": post.get("thresh") if args.det_thresh is None else args.det_thresh,
                "box_thresh": post.get("box_thresh") if args.det_box_thresh is None else args.det_box_thresh,
                "max_candidates": post.get("max_candidates") if args.det_max_candidates is None else args.det_max_candidates,
                "unclip_ratio": post.get("unclip_ratio") if args.det_unclip_ratio is None else args.det_unclip_ratio,
                "min_size": args.det_min_size,
            },
        },
        "rec": {
            "input_name": rec_info["input_name"],
            "output_name": rec_info["output_name"],
            "input_shape": rec_info["input_shape"],
            "output_shape": rec_info["output_shape"],
            "image_shape": rec_shape,
            "max_width": _rec_max_width(rec_cfg, rec_shape[2]),
            "batch_size": args.rec_batch_size,
            "decoder": "ctc",
            "blank_index": 0,
        },
    }
    if len(manifest["det"]["normalize"]["mean"]) != 3 or len(manifest["det"]["normalize"]["std"]) != 3:
        raise ValueError("检测 YML 的归一化参数必须各有三个通道")
    built_post = manifest["det"]["postprocess"]
    if not 0 <= float(built_post["thresh"]) <= 1:
        raise ValueError("检测二值化阈值必须在 0～1")
    if not 0 <= float(built_post["box_thresh"]) <= 1:
        raise ValueError("检测框阈值必须在 0～1")
    if int(built_post["max_candidates"]) <= 0:
        raise ValueError("检测最大候选数必须为正整数")
    if float(built_post["unclip_ratio"]) <= 0:
        raise ValueError("检测扩框比例必须为正数")
    return manifest, character_bytes


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--det", required=True, type=Path)
    parser.add_argument("--det-yml", required=True, type=Path)
    parser.add_argument("--rec", required=True, type=Path)
    parser.add_argument("--rec-yml", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model-version", default="")
    parser.add_argument("--det-limit-side-len", type=int, default=64)
    parser.add_argument("--det-limit-type", choices=("min", "max"), default="min")
    parser.add_argument("--det-multiple", type=int, default=32)
    parser.add_argument("--det-thresh", type=float)
    parser.add_argument("--det-box-thresh", type=float)
    parser.add_argument("--det-max-candidates", type=int)
    parser.add_argument("--det-unclip-ratio", type=float)
    parser.add_argument("--det-min-size", type=int, default=3)
    parser.add_argument("--rec-batch-size", type=int, default=8)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    for path in (args.det, args.det_yml, args.rec, args.rec_yml):
        if not path.is_file():
            raise FileNotFoundError(path)
    if min(args.det_limit_side_len, args.det_multiple, args.det_min_size, args.rec_batch_size) <= 0:
        raise ValueError("尺寸、倍数和批量参数必须为正整数")

    det_cfg = _load_yaml(args.det_yml)
    rec_cfg = _load_yaml(args.rec_yml)
    manifest, character_bytes = _build_manifest(args, det_cfg, rec_cfg)

    args.output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.det, args.output / "det.onnx")
    shutil.copy2(args.rec, args.output / "rec.onnx")
    (args.output / "characters.txt").write_bytes(character_bytes)
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"已生成 {args.output}，模型={manifest['model_version']}，"
        f"opset={manifest['opset']}，字符数={len(character_bytes.decode('utf-8').splitlines())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
