# -*- coding: utf-8 -*-
"""HY-MT1.5 翻译客户端：走 llama-server 的 OpenAI 兼容接口。

混元 MT 系列使用固定提示词模板，源语言无需指定（模型自动识别），
只需给出目标语言。
"""

import re
import time
from collections import OrderedDict

import requests

from .applog import get_logger

_log = get_logger("translate")

# 混元翻译模型官方推荐模板：目标语言为中文时用中文提示，其余用英文提示
_PROMPT_ZH = "把下面的文本翻译成{target}，不要额外解释。\n\n{text}"
_PROMPT_EN = "Translate the following segment into {target}, without additional explanation.\n\n{text}"

# 多行编号翻译：强制与输入行数对齐，减少备注模式「行数对不上→逐行重翻」
_PROMPT_LINES_ZH = (
    "把下面编号的每一行翻译成{target}。"
    "严格按相同编号逐行输出，不要合并/拆分行，不要额外解释。\n\n{text}"
)
_PROMPT_LINES_EN = (
    "Translate each numbered line into {target}. "
    "Output the same numbers line by line; do not merge/split lines; no extra explanation.\n\n{text}"
)

# 界面语言名 → 提示词中使用的语言名（英文提示用英文名）
_LANG_EN_NAME = {
    "简体中文": "Simplified Chinese",
    "繁体中文": "Traditional Chinese",
    "英语": "English",
    "日语": "Japanese",
    "韩语": "Korean",
    "法语": "French",
    "德语": "German",
    "俄语": "Russian",
    "西班牙语": "Spanish",
    "葡萄牙语": "Portuguese",
    "意大利语": "Italian",
    "泰语": "Thai",
    "越南语": "Vietnamese",
    "阿拉伯语": "Arabic",
}

_LINE_NUM_RE = re.compile(r"^\s*(\d+)[\.\)\、\:\：]\s*(.*)$")


class Translator:
    def __init__(self, base_url: str, cfg: dict | None = None, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # 共享配置引用，设置改 max_tokens 后立即生效
        self._cfg = cfg if cfg is not None else {}
        self._session = requests.Session()
        # 单行译文 LRU：备注模式增量翻译时命中率高
        self._line_cache: OrderedDict[tuple[str, str], str] = OrderedDict()
        self._line_cache_max = 256

    def _cache_get(self, text: str, target: str) -> str | None:
        key = (text, target)
        if key in self._line_cache:
            self._line_cache.move_to_end(key)
            return self._line_cache[key]
        return None

    def _cache_put(self, text: str, target: str, tr: str) -> None:
        if not text or not tr:
            return
        key = (text, target)
        self._line_cache[key] = tr
        self._line_cache.move_to_end(key)
        while len(self._line_cache) > self._line_cache_max:
            self._line_cache.popitem(last=False)

    def translate(self, text: str, target_language: str = "简体中文") -> str:
        """自动识别源语言，翻译为 target_language。"""
        text = text.strip()
        if not text:
            return ""
        if "中文" in target_language:
            prompt = _PROMPT_ZH.format(target=target_language, text=text)
        else:
            en_name = _LANG_EN_NAME.get(target_language, target_language)
            prompt = _PROMPT_EN.format(target=en_name, text=text)

        max_tokens = self._effective_max_tokens(text)

        preview = text.replace("\n", " ")[:80]
        t0 = time.time()
        try:
            resp = self._session.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,   # 翻译任务用低温度保证稳定
                    "top_p": 0.8,
                    "max_tokens": max_tokens,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            out = resp.json()["choices"][0]["message"]["content"].strip()
            _log.info(
                "翻译成功 target=%s max_tokens=%s chars=%d→%d %.2fs | %s",
                target_language, max_tokens, len(text), len(out),
                time.time() - t0, preview,
            )
            return out
        except Exception as e:
            _log.error(
                "翻译失败 target=%s max_tokens=%s %.2fs | %s | %s",
                target_language, max_tokens, time.time() - t0, preview, e,
            )
            raise

    def _effective_max_tokens(self, text: str) -> int:
        """按配置上限，并结合原文长度收紧，避免过长预留拖慢调度。"""
        cap = int(self._cfg.get("max_tokens", 512))
        cap = max(64, min(cap, 8192))
        # 中英混排粗估：译文通常不长于原文的 ~2 倍 + 余量
        est = max(64, min(cap, len(text) * 2 + 64))
        return est

    def _translate_prompt(self, prompt: str, target_language: str, preview: str) -> str:
        max_tokens = self._effective_max_tokens(preview)
        t0 = time.time()
        try:
            resp = self._session.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "max_tokens": max_tokens,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            out = resp.json()["choices"][0]["message"]["content"].strip()
            _log.info(
                "翻译成功 target=%s chars~%d→%d %.2fs | %s",
                target_language, len(preview), len(out),
                time.time() - t0, preview[:80],
            )
            return out
        except Exception as e:
            _log.error(
                "翻译失败 target=%s %.2fs | %s | %s",
                target_language, time.time() - t0, preview[:80], e,
            )
            raise

    @staticmethod
    def _parse_numbered(result: str, n: int) -> list[str] | None:
        """解析「1. xxx」形式输出；成功则返回长度 n 的列表。"""
        by_num: dict[int, str] = {}
        plain: list[str] = []
        for raw in result.splitlines():
            s = raw.strip()
            if not s:
                continue
            m = _LINE_NUM_RE.match(s)
            if m:
                idx = int(m.group(1))
                by_num[idx] = m.group(2).strip()
            else:
                plain.append(s)
        if len(by_num) >= n and all(i in by_num for i in range(1, n + 1)):
            return [by_num[i] for i in range(1, n + 1)]
        # 无编号但行数刚好
        if len(plain) == n:
            return plain
        if len(by_num) == n:
            # 编号从 0 或其它起点
            keys = sorted(by_num.keys())
            return [by_num[k] for k in keys]
        return None

    def _translate_numbered_batch(
        self, batch: list[str], target_language: str
    ) -> list[str] | None:
        """编号批量翻译一批行；解析失败返回 None。"""
        if not batch:
            return []
        if len(batch) == 1:
            tr = self.translate(batch[0], target_language)
            return [tr]

        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(batch))
        if "中文" in target_language:
            prompt = _PROMPT_LINES_ZH.format(target=target_language, text=numbered)
        else:
            en_name = _LANG_EN_NAME.get(target_language, target_language)
            prompt = _PROMPT_LINES_EN.format(target=en_name, text=numbered)
        raw = self._translate_prompt(
            prompt, target_language, preview=numbered.replace("\n", " ")[:80]
        )
        parsed = self._parse_numbered(raw, len(batch))
        if parsed is not None:
            return parsed
        # 兼容旧逻辑：按换行切
        out_lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
        # 去掉可能残留的编号前缀
        cleaned = []
        for ln in out_lines:
            m = _LINE_NUM_RE.match(ln)
            cleaned.append(m.group(2).strip() if m else ln)
        if len(cleaned) == len(batch):
            return cleaned
        return None

    def translate_lines(self, lines: list[str], target_language: str = "简体中文") -> list[str]:
        """按行批量翻译（编号对齐一次请求；失败则分块，再逐行）。

        备注模式会频繁多行 OCR：优先一次请求，避免动辄 N 次 llama 调用。
        命中行缓存的原文直接复用。
        """
        clean = [ln.strip() for ln in lines]
        results = ["" for _ in lines]
        need: list[tuple[int, str]] = []
        hits = 0
        for i, ln in enumerate(clean):
            if not ln:
                continue
            cached = self._cache_get(ln, target_language)
            if cached is not None:
                results[i] = cached
                hits += 1
            else:
                need.append((i, ln))
        if not need:
            return results

        # 先整批编号翻译
        batch_src = [ln for _, ln in need]
        parsed = self._translate_numbered_batch(batch_src, target_language)
        if parsed is not None:
            for (i, src), tr in zip(need, parsed):
                results[i] = tr
                self._cache_put(src, target_language, tr)
            _log.info(
                "行译完成 mode=batch lines=%d cache_hit=%d",
                len(need), hits,
            )
            return results

        # 分块（每块最多 6 行），比全量逐行快很多
        chunk_size = 6
        failed: list[tuple[int, str]] = []
        for start in range(0, len(need), chunk_size):
            chunk = need[start : start + chunk_size]
            chunk_src = [ln for _, ln in chunk]
            got = self._translate_numbered_batch(chunk_src, target_language)
            if got is not None:
                for (i, src), tr in zip(chunk, got):
                    results[i] = tr
                    self._cache_put(src, target_language, tr)
            else:
                failed.extend(chunk)

        # 仍失败的才逐行
        for i, src in failed:
            try:
                tr = self.translate(src, target_language)
            except Exception:
                tr = ""
            results[i] = tr
            if tr:
                self._cache_put(src, target_language, tr)
        _log.info(
            "行译完成 mode=fallback need=%d failed_to_single=%d cache_hit=%d",
            len(need), len(failed), hits,
        )
        return results
