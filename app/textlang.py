# -*- coding: utf-8 -*-
"""轻量语种启发式：判断一行 OCR 是否已是目标语言（无需联网库）。

用于备注模式「跳过已是目标语」；宁可漏判多译，也不要误判该译却跳过。
"""

from __future__ import annotations

import re

# 统计用字符类
_RE_CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_RE_HIRA = re.compile(r"[\u3040-\u309f]")
_RE_KATA = re.compile(r"[\u30a0-\u30ff]")
_RE_HANGUL = re.compile(r"[\uac00-\ud7af\u1100-\u11ff]")
_RE_CYR = re.compile(r"[\u0400-\u04ff]")
_RE_ARAB = re.compile(r"[\u0600-\u06ff]")
_RE_THAI = re.compile(r"[\u0e00-\u0e7f]")
_RE_LATIN = re.compile(r"[A-Za-z\u00c0-\u024f]")

# 纯数字/符号/空白：不必翻译
_RE_NO_LETTER = re.compile(r"^[\d\s\W_]+$", re.UNICODE)


def _counts(text: str) -> dict[str, int]:
    return {
        "cjk": len(_RE_CJK.findall(text)),
        "hira": len(_RE_HIRA.findall(text)),
        "kata": len(_RE_KATA.findall(text)),
        "hangul": len(_RE_HANGUL.findall(text)),
        "cyr": len(_RE_CYR.findall(text)),
        "arab": len(_RE_ARAB.findall(text)),
        "thai": len(_RE_THAI.findall(text)),
        "latin": len(_RE_LATIN.findall(text)),
    }


def _letter_total(c: dict[str, int]) -> int:
    return sum(c.values())


def is_already_target_language(text: str, target_language: str) -> bool:
    """原文是否已可视为目标语言（跳过翻译）。

    - 纯数字/符号 → 视为无需译
    - 中文目标：以汉字为主，且几乎无假名/谚文等
    - 英语等拉丁语：以拉丁字母为主，且几乎无汉字/假名/谚文
    - 证据不足（过短、混杂）→ 返回 False（仍去翻译）
    """
    text = (text or "").strip()
    if not text:
        return True
    if _RE_NO_LETTER.match(text):
        return True

    target = (target_language or "").strip()
    c = _counts(text)
    total = _letter_total(c)
    if total <= 0:
        return True
    # 过短且只有 1～2 个字母：证据不足，不跳过（避免漏译）
    if total < 2 and len(text) < 4:
        return False

    ratio = {k: v / total for k, v in c.items()}

    if "中文" in target:
        # 简/繁体：汉字占优；允许少量英文缩写
        if c["hira"] or c["kata"] or c["hangul"] or c["cyr"] or c["arab"] or c["thai"]:
            return False
        return ratio["cjk"] >= 0.55

    if target in ("英语", "法语", "德语", "西班牙语", "葡萄牙语", "意大利语"):
        if c["cjk"] or c["hira"] or c["kata"] or c["hangul"] or c["cyr"] or c["arab"] or c["thai"]:
            return False
        return ratio["latin"] >= 0.7

    if target == "日语":
        # 假名是日语强特征；纯汉字也可能是中文，不跳过
        kana = c["hira"] + c["kata"]
        if kana >= 1 and (kana + c["cjk"]) / total >= 0.5:
            return True
        return False

    if target == "韩语":
        return ratio["hangul"] >= 0.55

    if target == "俄语":
        return ratio["cyr"] >= 0.55

    if target == "阿拉伯语":
        return ratio["arab"] >= 0.55

    if target == "泰语":
        return ratio["thai"] >= 0.55

    if target == "越南语":
        # 国语字以拉丁+声调为主
        if c["cjk"] or c["hira"] or c["hangul"]:
            return False
        return ratio["latin"] >= 0.65

    # 未知目标语：不跳过
    return False
