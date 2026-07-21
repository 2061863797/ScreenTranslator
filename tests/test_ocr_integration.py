import json
import unittest
import unicodedata
from pathlib import Path

import cv2

from app.config import DEFAULTS
from app.ocr_engine import OcrEngine
from app.paths import RUNTIME_OCR


ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / "tests" / "fixtures" / "ocr_baseline.json"


def _normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return "".join(character for character in text if character.isalnum())


class OcrBaselineDefinitionTests(unittest.TestCase):
    def test_every_baseline_image_is_tracked_in_the_repository(self):
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(baseline["cases"]), 4)
        for case in baseline["cases"]:
            self.assertTrue((ROOT / case["image"]).is_file(), case["image"])
            self.assertTrue(case["anchors"], case["image"])


class RealOcrRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = (
            RUNTIME_OCR / "manifest.json",
            RUNTIME_OCR / "det.onnx",
            RUNTIME_OCR / "rec.onnx",
            RUNTIME_OCR / "characters.txt",
        )
        if not all(path.is_file() for path in required):
            raise unittest.SkipTest("源码 CI 不包含 Release OCR 资源")
        cfg = dict(DEFAULTS)
        cfg["ocr_provider"] = "auto"
        cls.engine = OcrEngine(cfg)
        cls.engine.preload()
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    def test_documented_screenshots_keep_text_and_box_coverage(self):
        for case in self.baseline["cases"]:
            with self.subTest(image=case["image"]):
                image = cv2.imread(str(ROOT / case["image"]), cv2.IMREAD_COLOR)
                self.assertIsNotNone(image)
                height, width = image.shape[:2]
                lines = self.engine.recognize(image)
                self.assertGreaterEqual(len(lines), case["min_lines"])
                self.assertLessEqual(len(lines), case["max_lines"])
                combined = _normalized("\n".join(line.text for line in lines))
                for anchor in case["anchors"]:
                    self.assertIn(_normalized(anchor), combined)
                for line in lines:
                    x1, y1, x2, y2 = line.box
                    self.assertTrue(0 <= x1 < x2 <= width, line)
                    self.assertTrue(0 <= y1 < y2 <= height, line)

    def test_character_table_capabilities_are_explicit(self):
        characters = (RUNTIME_OCR / "characters.txt").read_text(
            encoding="utf-8"
        )
        self.assertTrue(any("A" <= char <= "z" for char in characters))
        self.assertTrue(any("\u3400" <= char <= "\u9fff" for char in characters))
        self.assertTrue(any("\u3040" <= char <= "\u30ff" for char in characters))
        self.assertFalse(any("\uac00" <= char <= "\ud7af" for char in characters))


if __name__ == "__main__":
    unittest.main()
