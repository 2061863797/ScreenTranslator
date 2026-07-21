import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts import build_ocr_runtime


class OcrRuntimeBuilderTests(unittest.TestCase):
    def _args(self, root: Path):
        files = {}
        for name in ("det.onnx", "det.yml", "rec.onnx", "rec.yml"):
            path = root / name
            path.write_bytes(name.encode("ascii"))
            files[name] = path
        return SimpleNamespace(
            det=files["det.onnx"],
            det_yml=files["det.yml"],
            rec=files["rec.onnx"],
            rec_yml=files["rec.yml"],
            model_version="",
            det_limit_side_len=64,
            det_limit_type="min",
            det_multiple=32,
            det_thresh=None,
            det_box_thresh=None,
            det_max_candidates=None,
            det_unclip_ratio=None,
            det_min_size=3,
            rec_batch_size=8,
        )

    @staticmethod
    def _configs():
        det = {
            "Global": {"model_name": "PP-OCRv6_medium_det"},
            "PreProcess": {
                "transform_ops": [
                    {"DecodeImage": {"img_mode": "BGR"}},
                    {
                        "NormalizeImage": {
                            "scale": "1./255.",
                            "mean": [0.485, 0.456, 0.406],
                            "std": [0.229, 0.224, 0.225],
                        }
                    },
                ]
            },
            "PostProcess": {
                "name": "DBPostProcess",
                "thresh": 0.2,
                "box_thresh": 0.45,
                "max_candidates": 3000,
                "unclip_ratio": 1.4,
            },
        }
        rec = {
            "Global": {"model_name": "PP-OCRv6_medium_rec"},
            "Hpi": {
                "backend_configs": {
                    "paddle_infer": {
                        "trt_dynamic_shapes": {
                            "x": [[1, 3, 48, 160], [8, 3, 48, 3200]]
                        }
                    }
                }
            },
            "PreProcess": {
                "transform_ops": [
                    {"RecResizeImg": {"image_shape": [3, 48, 320]}}
                ]
            },
            "PostProcess": {
                "name": "CTCLabelDecode",
                "character_dict": ["A", "日", "テ", "본"],
            },
        }
        return det, rec

    @staticmethod
    def _model_info(kind: str):
        if kind == "det":
            return {
                "input_name": "actual_det_input",
                "input_shape": [None, 3, None, None],
                "input_type": "tensor(float)",
                "output_name": "actual_det_output",
                "output_shape": [None, 1, None, None],
                "output_type": "tensor(float)",
                "opsets": {"ai.onnx": 19},
            }
        return {
            "input_name": "actual_rec_input",
            "input_shape": [None, 3, 48, None],
            "input_type": "tensor(float)",
            "output_name": "actual_rec_output",
            "output_shape": [None, None, 6],
            "output_type": "tensor(float)",
            "opsets": {"ai.onnx": 19},
        }

    def test_manifest_comes_from_yml_and_actual_onnx_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = self._args(root)
            det, rec = self._configs()
            with mock.patch(
                "scripts.build_ocr_runtime._inspect_onnx",
                side_effect=[self._model_info("det"), self._model_info("rec")],
            ):
                manifest, characters = build_ocr_runtime._build_manifest(
                    args, det, rec
                )

        self.assertEqual(manifest["model_version"], "PP-OCRv6-medium")
        self.assertEqual(manifest["opset"], {"det": 19, "rec": 19})
        self.assertEqual(manifest["det"]["input_name"], "actual_det_input")
        self.assertEqual(manifest["det"]["postprocess"]["thresh"], 0.2)
        self.assertEqual(manifest["rec"]["max_width"], 3200)
        self.assertEqual(
            manifest["source"]["supported_scripts"],
            ["latin", "han", "kana", "hangul"],
        )
        self.assertEqual(characters.decode("utf-8"), "A\n日\nテ\n본\n \n")

    def test_character_count_must_match_recognition_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = self._args(root)
            det, rec = self._configs()
            bad_rec_info = self._model_info("rec")
            bad_rec_info["output_shape"] = [None, None, 99]
            with mock.patch(
                "scripts.build_ocr_runtime._inspect_onnx",
                side_effect=[self._model_info("det"), bad_rec_info],
            ):
                with self.assertRaisesRegex(ValueError, "字符表"):
                    build_ocr_runtime._build_manifest(args, det, rec)

    def test_reads_default_onnx_opset_from_protobuf(self):
        # ModelProto.opset_import(8) -> OperatorSetIdProto.version(2) = 19
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "tiny.onnx"
            model.write_bytes(b"\x42\x02\x10\x13")
            self.assertEqual(
                build_ocr_runtime._read_opsets(model),
                {"ai.onnx": 19},
            )

    def test_build_dependency_is_not_installed_for_end_users(self):
        root = Path(__file__).resolve().parent.parent
        runtime_requirements = (root / "requirements.txt").read_text(
            encoding="utf-8"
        )
        build_requirements = (root / "requirements-ocr-build.txt").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("PyYAML", runtime_requirements)
        self.assertIn("PyYAML", build_requirements)
        self.assertIn("onnxruntime", build_requirements)


if __name__ == "__main__":
    unittest.main()
