import re
import threading
import time
import unittest
from unittest.mock import Mock

from app.translator import Translator


class TranslatorTests(unittest.TestCase):
    def make_translator(self):
        return Translator(
            "http://127.0.0.1:9",
            {"ctx_size": 2048, "max_tokens": 512},
        )

    def test_long_text_is_split_without_data_loss(self):
        translator = self.make_translator()
        prompts = []

        def fake_chat(prompt, _max_tokens):
            prompts.append(prompt)
            return "译文"

        translator._chat = fake_chat
        source = "甲" * 2000
        result = translator.translate(source)
        self.assertGreater(len(prompts), 1)
        self.assertEqual(sum(p.count("甲") for p in prompts), len(source))
        self.assertEqual(len(result.splitlines()), len(prompts))

    def test_batch_budget_uses_full_input(self):
        translator = self.make_translator()
        seen = {}

        def fake_chat(_prompt, max_tokens):
            seen["max_tokens"] = max_tokens
            return "\n".join(f"{i}. 译文" for i in range(1, 11))

        translator._chat = fake_chat
        result = translator._translate_numbered_batch(["乙" * 60] * 10, "简体中文")
        self.assertEqual(len(result), 10)
        self.assertEqual(seen["max_tokens"], 512)

    def test_server_context_rejection_retries_smaller_without_loss(self):
        translator = self.make_translator()
        successful = []

        def fake_chat(prompt, _max_tokens):
            count = prompt.count("丙")
            if count > 100:
                raise RuntimeError("HTTP 400: exceed_context_size_error")
            successful.append(count)
            return "译文"

        translator._chat = fake_chat
        source = "丙" * 180
        result = translator.translate(source)
        self.assertEqual(sum(successful), len(source))
        self.assertEqual(len(result.splitlines()), len(successful))

    def test_numbered_context_rejection_falls_back_without_missing_lines(self):
        translator = self.make_translator()

        def fake_chat(prompt, _max_tokens):
            if prompt.count("丁") > 150:
                raise RuntimeError("HTTP 400: exceed_context_size_error")
            numbered = re.findall(r"(?m)^\d+\. ", prompt)
            if numbered:
                return "\n".join(
                    f"{i}. 译文" for i in range(1, len(numbered) + 1)
                )
            return "译文"

        translator._chat = fake_chat
        lines = [f"{i}-" + "丁" * 50 for i in range(8)]
        result = translator.translate_lines(lines)
        self.assertEqual(result, ["译文"] * len(lines))

    def test_single_line_fallback_surfaces_request_failure(self):
        translator = self.make_translator()
        translator._translate_numbered_batch = lambda *_args: None
        translator._chat = Mock(side_effect=ConnectionError("offline"))
        with self.assertRaisesRegex(ConnectionError, "offline"):
            translator.translate_lines(["唯一一行"])

    def test_shared_translator_serializes_requests(self):
        translator = self.make_translator()
        state_lock = threading.Lock()
        active = 0
        max_active = 0

        def fake_chat(_prompt, _max_tokens):
            nonlocal active, max_active
            with state_lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            with state_lock:
                active -= 1
            return "ok"

        translator._chat = fake_chat
        threads = [threading.Thread(target=translator.translate, args=(str(i),)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(max_active, 1)


if __name__ == "__main__":
    unittest.main()
