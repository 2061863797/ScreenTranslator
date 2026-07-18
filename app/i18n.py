# -*- coding: utf-8 -*-
"""全局界面语言：zh / en（设置里 ui_language，保存后全 UI 切换）。"""

from __future__ import annotations

_lang = "zh"

# 合并：设置窗 + 托盘 + 主界面浮层/对话框
_STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        # settings (same keys as before)
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
        "ui_lang_hint": "托盘、设置、历史、浮层控制条等全部界面；保存后立即切换。",
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
        "hk_win_full": "窗口持续翻译",
        "hk_region_full": "区域实时翻译",
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
        # tray
        "app_name": "翻译",
        "tray_history": "翻译历史…",
        "tray_settings": "设置…",
        "tray_open_log": "打开日志…",
        "tray_quit": "退出",
        "tray_tip": "翻译  截屏 {shot} | 划词 {word} | 窗口 {win} | 区域 {reg} | 取字 {ocr}",
        # messages
        "msg_wait_model": "正在等待翻译模型就绪…",
        "msg_server_fail": "翻译服务启动失败",
        "msg_preload_fail": "翻译：{name}加载失败",
        "msg_name_llama": "翻译模型",
        "msg_name_ocr": "OCR",
        "msg_ocr_copied": "已复制到剪贴板：\n{text}",
        "msg_ocr_title": "截图取字",
        "msg_word_empty": "未获取到选中文本",
        "msg_word_title": "划词翻译",
        "msg_error": "翻译：出错",
        "msg_running": "翻译已在运行中（托盘区）。\n请勿重复启动。",
        "msg_log_open_fail": "日志路径：\n{path}\n\n打开失败：{e}",
        "msg_no_text": "未识别到文字",
        # continuous UI
        "watch_start": "开始监视，等待识别文字…",
        "watch_switched_sub": "已切换为字幕条…",
        "sub_follow": "跟随",
        "sub_free": "自由",
        "sub_pinned": "固定",
        "sub_annotate": "备注",
        "sub_close": "关闭",
        "sub_close_tip": "停止持续翻译并关闭字幕",
        "sub_annotate_tip": "切换为备注模式（贴在原文旁）",
        "sub_drag_tip": "自由模式下拖动移动字幕",
        "sub_resize_tip": "拖动缩放译文框",
        "ann_label": "备注",
        "ann_subtitle": "字幕",
        "ann_subtitle_tip": "切换为字幕条模式（目标外侧）",
        "ann_skip": "跳过目标语",
        "ann_skip_tip": "开启后：已是目标语言的行不再翻译、不显示备注标签",
        "ann_close_tip": "停止持续翻译",
        "frame_pinned": "已固定 · 点右侧解锁",
        "frame_drag": "⠿ 拖动 · 拖边角缩放识别区",
        "frame_pin_on": "已固定",
        "frame_pin_off": "固定",
        # history
        "hist_title": "翻译历史",
        "hist_src": "原文",
        "hist_dst": "译文",
        "hist_tip": "双击一行可在翻译窗口中打开",
        # picker
        "pick_title": "选择要翻译的窗口",
        "pick_hint": "请选择要持续翻译的窗口（双击也可）",
        "pick_refresh": "刷新",
        "pick_ok": "开始翻译",
        "pick_cancel": "取消",
        # translate window
        "tw_title": "翻译",
        "tw_to": "译成：",
        "tw_placeholder": "输入任意语言的文本，或用划词/截屏热键送入…",
        "tw_out_ph": "译文",
        "tw_translate": "翻译",
        "tw_copy": "复制",
        "tw_busy": "翻译中…",
        "tw_fail": "翻译失败：{e}",
        "tw_server_fail": "翻译服务未就绪",
        "tw_pin": "固定",
        "tw_pinned": "已固定",
        # hotkey display
        "mouse_x1": "侧键1(后退)",
        "mouse_x2": "侧键2(前进)",
        "hk_need_mod": "键盘请加 Ctrl/Alt/Shift；侧键可直接按…",
        "hk_press": "请按快捷键或鼠标侧键…",
        "hk_placeholder": "点击后按快捷键或鼠标侧键…",
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
        "ui_lang_hint": "Tray, Settings, History, floating bars — all UI. Applies after Save.",
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
        "hk_shot": "Screenshot",
        "hk_word": "Selection",
        "hk_ocr": "OCR only",
        "hk_win": "Window watch",
        "hk_region": "Region watch",
        "hk_win_full": "Window live translate",
        "hk_region_full": "Region live translate",
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
        "app_name": "Translator",
        "tray_history": "History…",
        "tray_settings": "Settings…",
        "tray_open_log": "Open log…",
        "tray_quit": "Quit",
        "tray_tip": "Translator  Shot {shot} | Select {word} | Window {win} | Region {reg} | OCR {ocr}",
        "msg_wait_model": "Waiting for translation model…",
        "msg_server_fail": "Failed to start translation service",
        "msg_preload_fail": "Translator: {name} failed to load",
        "msg_name_llama": "translation model",
        "msg_name_ocr": "OCR",
        "msg_ocr_copied": "Copied to clipboard:\n{text}",
        "msg_ocr_title": "Screenshot OCR",
        "msg_word_empty": "No selected text",
        "msg_word_title": "Selection translate",
        "msg_error": "Translator: error",
        "msg_running": "Translator is already running (system tray).\nDo not start twice.",
        "msg_log_open_fail": "Log path:\n{path}\n\nFailed to open: {e}",
        "msg_no_text": "No text recognized",
        "watch_start": "Watching… waiting for text",
        "watch_switched_sub": "Switched to subtitle…",
        "sub_follow": "Follow",
        "sub_free": "Free",
        "sub_pinned": "Pin",
        "sub_annotate": "Notes",
        "sub_close": "Close",
        "sub_close_tip": "Stop continuous translate and close subtitle",
        "sub_annotate_tip": "Switch to annotation mode (next to source)",
        "sub_drag_tip": "Drag to move in Free mode",
        "sub_resize_tip": "Drag to resize",
        "ann_label": "Notes",
        "ann_subtitle": "Subtitle",
        "ann_subtitle_tip": "Switch to subtitle bar (outside target)",
        "ann_skip": "Skip target lang",
        "ann_skip_tip": "When on: skip lines already in the target language",
        "ann_close_tip": "Stop continuous translate",
        "frame_pinned": "Pinned · click to unlock",
        "frame_drag": "⠿ Drag · resize edges",
        "frame_pin_on": "Pinned",
        "frame_pin_off": "Pin",
        "hist_title": "History",
        "hist_src": "Source",
        "hist_dst": "Translation",
        "hist_tip": "Double-click a row to open in the translate window",
        "pick_title": "Select a window",
        "pick_hint": "Choose a window for continuous translate (double-click works)",
        "pick_refresh": "Refresh",
        "pick_ok": "Start",
        "pick_cancel": "Cancel",
        "tw_title": "Translate",
        "tw_to": "To:",
        "tw_placeholder": "Type or paste text, or use selection/screenshot hotkeys…",
        "tw_out_ph": "Translation",
        "tw_translate": "Translate",
        "tw_copy": "Copy",
        "tw_busy": "Translating…",
        "tw_fail": "Failed: {e}",
        "tw_server_fail": "Translation service not ready",
        "tw_pin": "Pin",
        "tw_pinned": "Pinned",
        "mouse_x1": "Side1(Back)",
        "mouse_x2": "Side2(Forward)",
        "hk_need_mod": "Add Ctrl/Alt/Shift for keys; side buttons alone OK…",
        "hk_press": "Press hotkey or mouse side button…",
        "hk_placeholder": "Click, then press hotkey or side button…",
    },
}


def normalize_lang(lang: str | None) -> str:
    return "en" if (lang or "").lower().startswith("en") else "zh"


def set_language(lang: str | None) -> str:
    global _lang
    _lang = normalize_lang(lang)
    return _lang


def get_language() -> str:
    return _lang


def t(key: str, **kwargs) -> str:
    """当前语言文案；缺 key 回退中文。"""
    table = _STRINGS.get(_lang) or _STRINGS["zh"]
    s = table.get(key) or _STRINGS["zh"].get(key) or key
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s


def t_lang(lang: str, key: str, **kwargs) -> str:
    """指定语言文案（设置窗刷新时用）。"""
    lang = normalize_lang(lang)
    table = _STRINGS.get(lang) or _STRINGS["zh"]
    s = table.get(key) or _STRINGS["zh"].get(key) or key
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s
