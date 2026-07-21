import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from app.ocr_engine import OcrEngine, OcrLine, OcrResourceError


class OcrEngineTests(unittest.TestCase):
    def test_ctc_decode_removes_blank_and_repeated_indexes(self):
        engine = OcrEngine({})
        engine._characters = ["", "你", "好", " "]
        logits = np.zeros((1, 6, 4), dtype=np.float32)
        for step, index in enumerate((1, 1, 0, 2, 2, 3)):
            logits[0, step, index] = 0.9
        self.assertEqual(engine._decode(logits)[0][0], "你好 ")

    def test_recognition_batch_is_normalized_and_padded(self):
        engine = OcrEngine({})
        engine._manifest = {
            "rec": {"image_shape": [3, 48, 320], "max_width": 3200}
        }
        crop = np.full((24, 60, 3), 255, dtype=np.uint8)
        batch = engine._rec_batch([crop])
        self.assertEqual(batch.shape, (1, 3, 48, 320))
        self.assertAlmostEqual(float(batch[0, 0, 0, 0]), 1.0)
        self.assertAlmostEqual(float(batch[0, 0, 0, -1]), 0.0)

    def test_manifest_rejects_changed_model_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {}
            for name, value in (("det.onnx", b"det"), ("rec.onnx", b"rec"), ("characters.txt", b"a\n")):
                (root / name).write_bytes(value)
                files[name] = {
                    "sha256": hashlib.sha256(value).hexdigest(),
                    "size": len(value),
                }
            (root / "manifest.json").write_text(
                json.dumps({
                    "schema_version": 1,
                    "files": files,
                    "det": {
                        "input_name": "x",
                        "output_name": "y",
                        "resize": {"limit_side_len": 64, "limit_type": "min", "multiple": 32},
                        "normalize": {
                            "scale": 1 / 255,
                            "mean": [0.5, 0.5, 0.5],
                            "std": [0.5, 0.5, 0.5],
                            "channel_order": "bgr",
                        },
                        "postprocess": {
                            "thresh": 0.3,
                            "box_thresh": 0.6,
                            "max_candidates": 100,
                            "unclip_ratio": 1.5,
                            "min_size": 3,
                        },
                    },
                    "rec": {
                        "input_name": "x",
                        "output_name": "y",
                        "image_shape": [3, 48, 320],
                        "max_width": 3200,
                        "batch_size": 8,
                        "decoder": "ctc",
                        "blank_index": 0,
                    },
                }),
                encoding="utf-8",
            )
            (root / "det.onnx").write_bytes(b"bad")
            with mock.patch("app.ocr_engine.RUNTIME_OCR", root):
                with self.assertRaises(OcrResourceError):
                    OcrEngine({})._load_manifest()

    def test_manifest_rejects_incompatible_recognition_shape(self):
        manifest = {
            "files": {
                name: {"sha256": "0" * 64, "size": 1}
                for name in ("det.onnx", "rec.onnx", "characters.txt")
            },
            "det": {
                "input_name": "x",
                "output_name": "y",
                "resize": {"limit_side_len": 64, "limit_type": "min", "multiple": 32},
                "normalize": {
                    "scale": 1 / 255,
                    "mean": [0.5, 0.5, 0.5],
                    "std": [0.5, 0.5, 0.5],
                    "channel_order": "bgr",
                },
                "postprocess": {
                    "thresh": 0.3,
                    "box_thresh": 0.6,
                    "max_candidates": 100,
                    "unclip_ratio": 1.5,
                    "min_size": 3,
                },
            },
            "rec": {
                "input_name": "x",
                "output_name": "y",
                "image_shape": [1, 48, 320],
                "batch_size": 8,
                "decoder": "ctc",
                "blank_index": 0,
            },
        }
        with self.assertRaisesRegex(OcrResourceError, "识别输入规格"):
            OcrEngine._validate_manifest(manifest)

    def test_directml_runtime_failure_falls_back_only_once(self):
        engine = OcrEngine({})
        engine._provider = "DmlExecutionProvider"
        engine._create_sessions = mock.Mock(side_effect=lambda provider: setattr(engine, "_provider", "CPUExecutionProvider"))
        engine._fallback_cpu(RuntimeError("dml"))
        self.assertTrue(engine._fell_back)
        engine._create_sessions.assert_called_once_with("cpu")

    def test_directml_initialization_failure_falls_back_to_cpu(self):
        engine = OcrEngine({"ocr_provider": "auto"})
        engine._manifest = {}
        engine._load_manifest = mock.Mock(return_value={})
        calls = []

        def create(provider):
            calls.append(provider)
            if provider == "auto":
                raise RuntimeError("dml init")
            engine._provider = "CPUExecutionProvider"
            engine._det_session = mock.Mock()
            engine._rec_session = mock.Mock()

        engine._create_sessions = create
        with mock.patch("app.ocr_engine.RUNTIME_OCR") as root:
            root.__truediv__.return_value.read_text.return_value = "a\n"
            engine._ensure_loaded()
        self.assertEqual(calls, ["auto", "cpu"])
        self.assertTrue(engine._fell_back)

    def test_public_contract_is_unchanged(self):
        line = OcrLine("text", 0.9, (1, 2, 3, 4))
        self.assertEqual(OcrEngine.lines_to_text([line]), "text")

    def test_preload_runs_detection_and_recognition_warmup_once(self):
        engine = OcrEngine({})
        engine._manifest = {
            "det": {
                "input_name": "det_in",
                "output_name": "det_out",
                "resize": {"limit_side_len": 64, "multiple": 32},
            },
            "rec": {
                "input_name": "rec_in",
                "output_name": "rec_out",
                "image_shape": [3, 48, 320],
            },
        }
        engine._det_session = mock.Mock()
        engine._rec_session = mock.Mock()

        engine.preload()
        engine.preload()

        engine._det_session.run.assert_called_once()
        engine._rec_session.run.assert_called_once()
        self.assertEqual(
            engine._det_session.run.call_args.args[1]["det_in"].shape,
            (1, 3, 64, 64),
        )
        self.assertEqual(
            engine._rec_session.run.call_args.args[1]["rec_in"].shape,
            (1, 3, 48, 320),
        )
