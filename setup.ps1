#Requires -Version 5.1
<#
.SYNOPSIS
  翻译（ScreenTranslator）一键环境安装 / 体检 / 按本机生成配置

.DESCRIPTION
  在项目根执行：
    .\setup.ps1                 # 完整安装
    .\setup.ps1 -Check          # 只检查
    .\setup.ps1 -CpuOnly        # 强制 CPU
    .\setup.ps1 -Gpu            # 强制 GPU 版 Paddle
    .\setup.ps1 -SkipPaddle       # 跳过 Paddle
    .\setup.ps1 -BuildLauncher    # 重建 翻译.exe
    .\setup.ps1 -DownloadRuntime  # 顺带下载模型/llama（见 scripts\download_runtime.ps1）
#>

param(
    [switch]$Check,
    [switch]$CpuOnly,
    [switch]$Gpu,
    [switch]$SkipPaddle,
    [switch]$BuildLauncher,
    [switch]$DownloadRuntime,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

function Write-Step([string]$msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg){ Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Err2([string]$msg) { Write-Host "  [X] $msg" -ForegroundColor Red }

function Test-NvidiaGpu {
    try {
        $cmd = Get-Command nvidia-smi -ErrorAction SilentlyContinue
        if (-not $cmd) { return $false }
        $out = & nvidia-smi -L 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        if ($null -eq $out) { return $false }
        return ($out -match "GPU")
    } catch {
        return $false
    }
}

function Get-CpuThreadHint {
    try {
        $n = [Environment]::ProcessorCount
        if ($n -lt 2) { return 2 }
        if ($n -gt 16) { return 16 }
        return [int]$n
    } catch {
        return 8
    }
}

function Find-Python {
    param([string]$Prefer)
    if ($Prefer -and (Test-Path -LiteralPath $Prefer)) {
        return (Resolve-Path -LiteralPath $Prefer).Path
    }
    foreach ($ver in @("3.12", "3.13", "3.11")) {
        try {
            $p = & py "-$ver" -c "import sys; print(sys.executable)" 2>$null
            if ($p) {
                $p = $p.ToString().Trim()
                if (Test-Path -LiteralPath $p) { return $p }
            }
        } catch {}
    }
    try {
        $p = & python -c "import sys; print(sys.executable)" 2>$null
        if ($p) {
            $p = $p.ToString().Trim()
            if (Test-Path -LiteralPath $p) { return $p }
        }
    } catch {}
    return $null
}

function Ensure-Venv {
    param([string]$BasePython)
    $venvPy = Join-Path $Root "venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPy) {
        Write-Ok "已有 venv: $venvPy"
        return $venvPy
    }
    Write-Step "创建 venv"
    Write-Host "  base: $BasePython"
    & $BasePython -m venv (Join-Path $Root "venv")
    if (-not (Test-Path -LiteralPath $venvPy)) {
        throw "venv 创建失败"
    }
    Write-Ok "venv 已创建"
    return $venvPy
}

function Install-PipPackages {
    param([string]$VenvPy)
    Write-Step "升级 pip 并安装 requirements.txt"
    & $VenvPy -m pip install -U pip setuptools wheel
    if ($LASTEXITCODE -ne 0) { throw "pip 升级失败" }
    & $VenvPy -m pip install -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "requirements 安装失败" }
    Write-Ok "基础依赖已安装"
}

function Install-Paddle {
    param(
        [string]$VenvPy,
        [bool]$WantGpu
    )
    if ($SkipPaddle) {
        Write-Warn2 "跳过 Paddle 安装（-SkipPaddle）"
        return
    }
    $kind = "CPU"
    if ($WantGpu) { $kind = "GPU" }
    Write-Step "安装 PaddlePaddle ($kind)"
    if ($WantGpu) {
        $idx = "https://www.paddlepaddle.org.cn/packages/stable/cu126/"
        Write-Host "  源: $idx"
        & $VenvPy -m pip install "paddlepaddle-gpu==3.3.1" -i $idx
        if ($LASTEXITCODE -ne 0) {
            Write-Warn2 "GPU 版安装失败，回退 CPU 版"
            & $VenvPy -m pip install "paddlepaddle==3.3.1" -i "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
        }
    } else {
        & $VenvPy -m pip install "paddlepaddle==3.3.1" -i "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Warn2 "Paddle 安装可能失败，请查看上方 pip 输出"
    } else {
        Write-Ok "Paddle 安装步骤完成"
    }
}

function Ensure-Config {
    param(
        [bool]$UseGpu,
        [int]$Threads
    )
    Write-Step "生成 / 更新 config.json"
    $ngl = 0
    if ($UseGpu) { $ngl = 99 }

    $py = Join-Path $Root "venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $py)) {
        $py = Find-Python -Prefer $Python
    }
    if (-not $py) { throw "无 Python，无法写 config" }

    $script = Join-Path $Root "scripts\setup_config.py"
    $flag = "0"
    if ($UseGpu) { $flag = "1" }
    & $py $script $Root $flag $Threads $ngl
    if ($LASTEXITCODE -ne 0) { throw "写 config 失败" }
    Write-Ok "config.json 已就绪 (n_gpu_layers=$ngl, threads=$Threads)"
}

function Test-Runtime {
    Write-Step "检查 runtime 资源"
    $ok = $true
    $llama = Join-Path $Root "runtime\llama\llama-server.exe"
    $model = Join-Path $Root "runtime\models\HY-MT1.5-1.8B-Q4_K_M.gguf"
    $ocr = Join-Path $Root "runtime\paddlex\official_models"

    if (Test-Path -LiteralPath $llama) {
        Write-Ok "llama-server: $llama"
    } else {
        Write-Err2 "缺少 $llama"
        $ok = $false
    }

    if (Test-Path -LiteralPath $model) {
        $mb = [math]::Round((Get-Item -LiteralPath $model).Length / 1MB, 1)
        Write-Ok "翻译模型: $model ($mb MB)"
    } else {
        Write-Err2 "缺少 $model"
        $ok = $false
    }

    if (Test-Path -LiteralPath $ocr) {
        $names = @(Get-ChildItem -LiteralPath $ocr -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name})
        Write-Ok ("OCR 模型目录: $ocr (" + ($names -join ", ") + ")")
    } else {
        Write-Err2 "缺少 $ocr"
        $ok = $false
    }

    if (-not $ok) {
        Write-Warn2 "runtime 不齐：请把完整 runtime/ 与本目录一起拷贝（脚本不下载大模型）。"
    }
    return $ok
}

function Test-Imports {
    param([string]$VenvPy)
    Write-Step "冒烟导入"
    if (-not (Test-Path -LiteralPath $VenvPy)) {
        Write-Warn2 "无 venv，跳过导入检查"
        return
    }
    $script = Join-Path $Root "scripts\smoke_import.py"
    & $VenvPy $script
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "app 导入成功"
    } else {
        Write-Err2 "app 导入失败"
    }
}

function Invoke-BuildLauncher {
    param([string]$VenvPy)
    Write-Step "重建 翻译.exe"
    $build = Join-Path $Root "build.ps1"
    if (Test-Path -LiteralPath $build) {
        & $build
        return
    }
    & $VenvPy -m pip install pyinstaller
    & $VenvPy -m PyInstaller --noconfirm --onefile --windowed `
        --name "翻译" `
        --icon (Join-Path $Root "icon.ico") `
        --distpath $Root `
        --workpath (Join-Path $Root "build") `
        --specpath $Root `
        (Join-Path $Root "launcher.py")
}

# ---------------- main ----------------
Write-Host "ScreenTranslator 一键安装 / 体检" -ForegroundColor White
Write-Host "目录: $Root"

$hasNvidia = Test-NvidiaGpu
if ($CpuOnly) {
    $useGpu = $false
    Write-Host "模式: 强制 CPU (-CpuOnly)"
} elseif ($Gpu) {
    $useGpu = $true
    Write-Host "模式: 强制 GPU (-Gpu)"
    if (-not $hasNvidia) {
        Write-Warn2 "未检测到 nvidia-smi，仍按 GPU 安装（可能失败）"
    }
} else {
    $useGpu = $hasNvidia
    if ($useGpu) {
        Write-Host "模式: 自动（检测到 NVIDIA → GPU）"
    } else {
        Write-Host "模式: 自动（无 NVIDIA → CPU）"
    }
}

$threads = Get-CpuThreadHint
$nglShow = 0
if ($useGpu) { $nglShow = 99 }
Write-Host "threads=$threads  n_gpu_layers=$nglShow"

$runtimeOk = Test-Runtime

if ($Check) {
    Write-Step "仅检查模式 (-Check)"
    $venvPy = Join-Path $Root "venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPy) {
        Test-Imports -VenvPy $venvPy
    } else {
        Write-Warn2 "尚未创建 venv，完整安装请运行: .\setup.ps1"
    }
    Write-Host ""
    if ($runtimeOk) {
        Write-Ok "体检结束"
        exit 0
    }
    Write-Warn2 "体检结束（runtime 有缺失）"
    exit 2
}

$basePy = Find-Python -Prefer $Python
if (-not $basePy) {
    Write-Err2 "未找到 Python 3.11/3.12/3.13"
    Write-Host "  安装: winget install Python.Python.3.12"
    Write-Host "  或:   https://www.python.org/downloads/"
    exit 1
}
Write-Ok "基础 Python: $basePy"

$venvPy = Ensure-Venv -BasePython $basePy
Install-PipPackages -VenvPy $venvPy
Install-Paddle -VenvPy $venvPy -WantGpu $useGpu
Ensure-Config -UseGpu $useGpu -Threads $threads
Test-Imports -VenvPy $venvPy

if ($DownloadRuntime) {
    Write-Step "下载 runtime（模型 / llama）"
    $dl = Join-Path $Root "scripts\download_runtime.ps1"
    if (-not (Test-Path -LiteralPath $dl)) {
        Write-Err2 "缺少 $dl"
    } else {
        $dlArgs = @()
        if ($CpuOnly -or -not $useGpu) { $dlArgs += "-CpuOnly" }
        # 装完 venv 后顺带预热 OCR 缓存
        $dlArgs += "-WarmOcr"
        & $dl @dlArgs
        $runtimeOk = Test-Runtime
    }
}

if ($BuildLauncher) {
    Invoke-BuildLauncher -VenvPy $venvPy
}

Write-Step "完成"
Write-Host ""
Write-Host '  启动: 双击 翻译.exe  或  venv\Scripts\pythonw.exe run.py'
Write-Host "  检查: .\setup.ps1 -Check"
Write-Host "  仅CPU: .\setup.ps1 -CpuOnly"
Write-Host '  下载资源: .\scripts\download_runtime.ps1  或  .\setup.ps1 -DownloadRuntime'
Write-Host '  说明: runtime/ 可用脚本下载或整夹拷贝；venv 请每台机器跑本脚本安装'
Write-Host ""

if (-not $runtimeOk) { exit 2 }
exit 0
