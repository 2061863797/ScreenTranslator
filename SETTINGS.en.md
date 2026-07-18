# Settings reference (English)

Chinese UI is default. Open **Settings** from the tray → **General → UI language → English** → **Save settings**.  
Config key: `ui_language` = `zh` | `en`.

This switches **all** UI: tray menu, Settings, History, translate window, window picker, subtitle/annotation control bars (not OCR/target language names).

---

## General

| Option | Config key | Description |
|--------|------------|-------------|
| **UI language** | `ui_language` | `zh` / `en` — Settings window labels only (not OCR/target language). |
| **Target language** | `target_language` | Default translation target (e.g. 简体中文, English). Source is auto-detected. |
| **Annotation color** | `annotate_text_color` | Hex `#RRGGBB` for annotation-mode translation text (window & region). |

---

## Hotkeys

| Option | Config key | Default |
|--------|------------|---------|
| Screenshot translate | `hotkey_screenshot` | `<alt>+q` |
| Selection translate | `hotkey_word` | `<alt>+w` |
| Screenshot OCR | `hotkey_silent_ocr` | `<alt>+s` |
| Window watch | `hotkey_window` | `<alt>+e` |
| Region watch | `hotkey_region_watch` | `<alt>+r` |

**Keyboard:** at least one of Ctrl/Alt/Shift + key (stored as pynput, e.g. `<ctrl>+t`).  
**Mouse side buttons:** click the field and press the side button → `mouse.x1` (Back) / `mouse.x2` (Forward); combos like `<ctrl>+mouse.x1` allowed.  
Esc cancels capture. Duplicates are blocked on save.

---

## Window continuous translate

| Option | Config key | Description |
|--------|------------|-------------|
| Poll interval | `window_watch_interval_ms` | How often to capture/OCR (ms). |
| Display mode | `window_watch_annotate` | `false` = subtitle bar outside window; `true` = per-line annotations. |
| Skip target language | `window_annotate_skip_target_lang` | Annotation only: don’t translate lines already in the target language. |

Also: floating bar can switch **Subtitle ↔ Annotation** while running (writes the same keys).

---

## Region continuous translate

| Option | Config key | Description |
|--------|------------|-------------|
| Poll interval | `region_watch_interval_ms` | Capture interval (ms). |
| Display mode | `region_watch_annotate` | Subtitle outside region vs annotations inside. |
| Skip target language | `region_annotate_skip_target_lang` | Same as window, but region-only. |

Region frame: drag title bar, resize edges, **Pin** locks geometry.

---

## Advanced

| Option | Config key | Description |
|--------|------------|-------------|
| max_tokens | `max_tokens` | Max generation length per request (default 512). |

Other llama server options (`n_gpu_layers`, `ctx_size`, `model_path`, …) live in `config.json` / `config.example.json`; edit the file or use `setup.ps1` defaults. Not all appear in the GUI.

---

## Log page

Live `app.log` tail. **Clear view** only clears the panel; **Open log file** opens the file on disk.

---

## Related docs

- [README.en.md](./README.en.md) — install & run  
- [runtime/README.en.md](./runtime/README.en.md) — models / llama / OCR  
- [README.md](./README.md) — 中文说明  

---

## Disclaimer

Documentation may be **AI-generated** and **incorrect**. Verify settings keys and behavior yourself.
