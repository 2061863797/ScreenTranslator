@echo off
chcp 65001 >nul
set "LLAMA_DIR=%~dp0runtime\llama"
set "LAUNCHER=%LLAMA_DIR%\llama启动.exe"

if not exist "%LAUNCHER%" (
    echo 未找到: %LAUNCHER%
    echo 请确认 runtime\llama\llama启动.exe 存在。
    pause
    exit /b 1
)

cd /d "%LLAMA_DIR%"
start "llama-launcher" "%LAUNCHER%"
exit /b 0
