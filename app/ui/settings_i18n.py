# -*- coding: utf-8 -*-
"""设置窗口文案：zh / en。"""

from __future__ import annotations

# 键 → 中文 / 英文
STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        "win_title": "设置",
        "title": "设置",
        "subtitle": "ScreenTranslator · 本地离线",
        "close": "关闭",
        "save": "保存设置",
        "nav_general": "常规",
        "nav_hotkeys": "热键",
        "nav_window": "窗口翻译",
        "nav_region": "区域翻译",
        "nav_advanced": "高级",
        "nav_log": "日志",
        "ui_lang": "界面语言",
        "ui_lang_hint": "仅影响本设置窗口文案；保存后立即切换。",
        "card_general": "常规",
        "card_general_hint": "全局默认目标语言；源语言自动识别。翻译结果窗内也可临时切换。",
        "target_lang": "目标语言",
        "ann_color": "备注译文颜色",
        "ann_color_tip": "备注模式译文颜色，#RRGGBB；窗口与区域共用",
        "ann_color_pick": "选色",
        "ann_color_preview": "当前颜色预览",
        "ann_color_dlg": "备注译文颜色",
        "ann_color_note": "备注译文颜色对窗口/区域备注模式均生效，保存后立即应用。",
        "card_hotkeys": "全局热键",
        "card_hotkeys_hint": (
            "点击输入框后：键盘组合键（需含 Ctrl/Alt/Shift，Esc 取消）；"
            "或直接按鼠标侧键（侧键1=后退 / 侧键2=前进，也可 Ctrl+侧键）。"
        ),
        "hk_shot": "截屏翻译",
        "hk_word": "划词翻译",
        "hk_ocr": "截图取字",
        "hk_win": "窗口持续",
        "hk_region": "区域实时",
        "card_window": "窗口持续翻译",
        "card_window_hint": "字幕条显示在目标窗口外侧不遮挡；备注按行贴在原文旁。",
        "interval": "监视间隔",
        "display_mode": "显示模式",
        "ms_suffix": " 毫秒",
        "mode_sub_win": "字幕条（整段译，窗口外侧不遮挡）",
        "mode_ann_win": "备注（按行译，贴在原文旁）",
        "mode_sub_reg": "字幕条（整段译，识别区外侧）",
        "mode_ann_reg": "备注（按行译，贴在原文旁）",
        "tip_win_mode": "字幕条：译文在目标窗口下方外侧，不遮挡。备注：与区域相同，译文贴在窗口内原文旁。",
        "tip_reg_mode": "字幕条=识别区下方整段译文；备注=译文贴在识别区内原文旁。",
        "card_win_ann": "备注选项",
        "card_win_ann_hint": "仅窗口备注模式生效，与区域设置互不影响。",
        "skip_target": "不翻译已是目标语言的文字",
        "skip_win_tip": "仅窗口备注模式：已是目标语言的行不再送模型、不叠备注。也可在备注条切换（仅影响窗口）。",
        "card_region": "区域实时翻译",
        "card_region_hint": "识别框可拖顶栏移动、拖边角缩放；点「固定」锁定。",
        "card_reg_ann": "备注选项",
        "card_reg_ann_hint": "仅区域备注模式生效，与窗口设置互不影响。",
        "skip_reg_tip": "仅区域备注模式：已是目标语言的行不再送模型、不叠备注。也可在备注条切换（仅影响区域）。",
        "card_advanced": "模型与生成",
        "card_advanced_hint": "max_tokens 为单次翻译生成上限；过小可能截断，过大略增延迟。",
        "max_tokens_tip": "单次翻译最大生成长度；过小可能截断，过大略增延迟",
        "card_log": "运行日志",
        "card_log_hint": "文件：{log} · 清空显示不会删除磁盘日志。",
        "log_placeholder": "运行日志将显示在这里…",
        "log_bottom": "滚到底",
        "log_clear": "清空显示",
        "log_open": "打开日志文件",
        "log_title": "日志",
        "log_open_fail": "路径：\n{path}\n\n打开失败：{err}",
        "hk_conflict_title": "热键冲突",
        "hk_conflict_body": "以下热键重复，请修改后再保存：\n\n{list}",
        "saved_toast": "设置已保存",
        "lang_zh": "中文",
        "lang_en": "English",
    },
    "en": {
        "win_title": "Settings",
        "title": "Settings",
        "subtitle": "ScreenTranslator · Offline local",
        "close": "Close",
        "save": "Save settings",
        "nav_general": "General",
        "nav_hotkeys": "Hotkeys",
        "nav_window": "Window watch",
        "nav_region": "Region watch",
        "nav_advanced": "Advanced",
        "nav_log": "Log",
        "ui_lang": "UI language",
        "ui_lang_hint": "Affects this Settings window only; applies after Save.",
        "card_general": "General",
        "card_general_hint": (
            "Default target language. Source is auto-detected. "
            "You can also change language in the result window."
        ),
        "target_lang": "Target language",
        "ann_color": "Annotation color",
        "ann_color_tip": "Annotation text color (#RRGGBB); shared by window & region modes",
        "ann_color_pick": "Pick",
        "ann_color_preview": "Color preview",
        "ann_color_dlg": "Annotation text color",
        "ann_color_note": (
            "Annotation color applies to both window and region modes; "
            "takes effect after Save."
        ),
        "card_hotkeys": "Global hotkeys",
        "card_hotkeys_hint": (
            "Click a field, then press a keyboard combo (requires Ctrl/Alt/Shift; Esc cancels), "
            "or a mouse side button (X1=Back / X2=Forward; Ctrl+side button also works)."
        ),
        "hk_shot": "Screenshot translate",
        "hk_word": "Selection translate",
        "hk_ocr": "Screenshot OCR",
        "hk_win": "Window watch",
        "hk_region": "Region watch",
        "card_window": "Window continuous translate",
        "card_window_hint": (
            "Subtitle bar sits outside the target window; "
            "annotation places lines next to source text."
        ),
        "interval": "Poll interval",
        "display_mode": "Display mode",
        "ms_suffix": " ms",
        "mode_sub_win": "Subtitle (full text, outside window)",
        "mode_ann_win": "Annotation (per-line, next to source)",
        "mode_sub_reg": "Subtitle (full text, outside region)",
        "mode_ann_reg": "Annotation (per-line, next to source)",
        "tip_win_mode": (
            "Subtitle: translation below the window, non-covering. "
            "Annotation: lines next to OCR boxes inside the window."
        ),
        "tip_reg_mode": (
            "Subtitle = full text under the region; "
            "Annotation = lines next to source inside the region."
        ),
        "card_win_ann": "Annotation options",
        "card_win_ann_hint": "Window annotation mode only; independent of region settings.",
        "skip_target": "Skip text already in target language",
        "skip_win_tip": (
            "Window annotation only: skip model call and labels for target-language lines. "
            "Also toggleable on the annotation bar (window session only)."
        ),
        "card_region": "Region continuous translate",
        "card_region_hint": (
            "Drag the top bar to move, edges to resize; click Pin to lock."
        ),
        "card_reg_ann": "Annotation options",
        "card_reg_ann_hint": "Region annotation mode only; independent of window settings.",
        "skip_reg_tip": (
            "Region annotation only: skip model call and labels for target-language lines. "
            "Also toggleable on the annotation bar (region session only)."
        ),
        "card_advanced": "Model & generation",
        "card_advanced_hint": (
            "max_tokens is the max generation length per request; "
            "too small truncates, too large may add latency."
        ),
        "max_tokens_tip": "Max tokens per translation; too small truncates, too large may slow down",
        "card_log": "Runtime log",
        "card_log_hint": "File: {log} · Clearing the view does not delete the log file.",
        "log_placeholder": "Runtime logs appear here…",
        "log_bottom": "Scroll to end",
        "log_clear": "Clear view",
        "log_open": "Open log file",
        "log_title": "Log",
        "log_open_fail": "Path:\n{path}\n\nFailed to open: {err}",
        "hk_conflict_title": "Hotkey conflict",
        "hk_conflict_body": "Duplicate hotkeys; fix before saving:\n\n{list}",
        "saved_toast": "Settings saved",
        "lang_zh": "中文",
        "lang_en": "English",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = "en" if (lang or "").lower().startswith("en") else "zh"
    table = STRINGS.get(lang) or STRINGS["zh"]
    s = table.get(key) or STRINGS["zh"].get(key) or key
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s
