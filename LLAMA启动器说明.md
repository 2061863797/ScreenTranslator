# llama 启动器（可选）

根目录 **`启动llama.bat`** → 打开 `runtime\llama\llama启动.exe`，用于单独启动 / 调参 llama-server。  
日常翻译请用 **`run.py` / `翻译.exe`**。

1. 双击 `启动llama.bat`  
2. 模型选：`runtime\models\HY-MT1.5-1.8B-Q4_K_M.gguf`  
3. 无独显：GPU 层填 **0**；端口建议 **8080**  
4. 确认并启动  

须与 `runtime\llama\` 下 DLL 同目录运行（bat 已处理）。  
勿与软件内已占用的同一端口重复开两个 server。

参数保存在 `runtime\llama\launcher_config.json`。

**说明可能由 AI 生成，请自行核对。**
