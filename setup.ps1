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

function Test-SupportedPython {
    param([string]$Exe)
    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) { return $false }
    try {
        & $Exe -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12),(3,13)) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-Python {
    param([string]$Prefer)
    if ($Prefer -and (Test-Path -LiteralPath $Prefer)) {
        $resolved = (Resolve-Path -LiteralPath $Prefer).Path
        if (Test-SupportedPython $resolved) { return $resolved }
        Write-Warn2 "指定的 Python 版本不受支持（仅 3.11～3.13）: $resolved"
        return $null
    }
    foreach ($ver in @("3.12", "3.13", "3.11")) {
        try {
            $p = & py "-$ver" -c "import sys; print(sys.executable)" 2>$null
            if ($p) {
                $p = $p.ToString().Trim()
                if ((Test-Path -LiteralPath $p) -and (Test-SupportedPython $p)) { return $p }
            }
        } catch {}
    }
    try {
        $p = & python -c "import sys; print(sys.executable)" 2>$null
        if ($p) {
            $p = $p.ToString().Trim()
            if ((Test-Path -LiteralPath $p) -and (Test-SupportedPython $p)) { return $p }
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
        & $VenvPy -m pip uninstall -y paddlepaddle 2>$null
        $idx = "https://www.paddlepaddle.org.cn/packages/stable/cu129/"
        Write-Host "  源: $idx"
        & $VenvPy -c "import paddle; raise SystemExit(0 if paddle.__version__ == '3.3.1' and str(paddle.version.cuda()).startswith('12.9') else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "已有匹配的 Paddle GPU 3.3.1 / CUDA 12.9"
        } else {
            & $VenvPy -m pip install --upgrade --force-reinstall "paddlepaddle-gpu==3.3.1" -i $idx
        }
        if ($LASTEXITCODE -ne 0) {
            Write-Warn2 "GPU 版安装失败，回退 CPU 版"
            & $VenvPy -m pip uninstall -y paddlepaddle-gpu 2>$null
            & $VenvPy -m pip install "paddlepaddle==3.3.1" -i "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
        }
    } else {
        & $VenvPy -m pip uninstall -y paddlepaddle-gpu 2>$null
        & $VenvPy -m pip install "paddlepaddle==3.3.1" -i "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Paddle 安装失败，请查看上方 pip 输出"
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
    $defaultModel = Join-Path $Root "runtime\models\HY-MT1.5-1.8B-Q4_K_M.gguf"
    $model = $defaultModel
    $configFile = Join-Path $Root "config.json"
    if (Test-Path -LiteralPath $configFile) {
        try {
            # Windows PowerShell 5.1 对无 BOM UTF-8 的默认解码不可靠，必须显式指定。
            $configData = Get-Content -LiteralPath $configFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $configuredModel = $configData.model_path
            if ($configuredModel -is [string] -and -not [string]::IsNullOrWhiteSpace($configuredModel)) {
                if ([System.IO.Path]::IsPathRooted($configuredModel)) {
                    $model = [System.IO.Path]::GetFullPath($configuredModel)
                } else {
                    $model = [System.IO.Path]::GetFullPath((Join-Path $Root $configuredModel))
                }
            }
        } catch {
            Write-Warn2 "config.json 的 model_path 无法读取，改为检查默认模型"
            $model = $defaultModel
        }
    }
    $isDefaultModel = [string]::Equals(
        [System.IO.Path]::GetFullPath($model),
        [System.IO.Path]::GetFullPath($defaultModel),
        [System.StringComparison]::OrdinalIgnoreCase
    )
    $ocr = Join-Path $Root "runtime\paddlex\official_models"

    if (Test-Path -LiteralPath $llama) {
        $oldEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $llama --version 1>$null 2>$null
        $llamaCode = $LASTEXITCODE
        $ErrorActionPreference = $oldEap
        if ($llamaCode -eq 0) {
            Write-Ok "llama-server: $llama"
        } else {
            Write-Err2 "llama-server 无法运行或依赖 DLL 不完整: $llama"
            $ok = $false
        }
    } else {
        Write-Err2 "缺少 $llama"
        $ok = $false
    }

    if (Test-Path -LiteralPath $model) {
        $mb = [math]::Round((Get-Item -LiteralPath $model).Length / 1MB, 1)
        $fs = [System.IO.File]::OpenRead($model)
        try {
            $magicBytes = New-Object byte[] 4
            [void]$fs.Read($magicBytes, 0, 4)
            $magic = [System.Text.Encoding]::ASCII.GetString($magicBytes)
        } finally { $fs.Dispose() }
        if ($magic -ne "GGUF" -or $mb -le 0) {
            Write-Err2 "翻译模型文件不完整或不是 GGUF: $model"
            $ok = $false
        } elseif ($isDefaultModel -and $mb -gt 100) {
            $expectedModelSha = "4383ac0c3c8e476de98ff979c2a3f069f8c4fb385e7860cf2d28da896cc477c7"
            $actualModelSha = (Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actualModelSha -eq $expectedModelSha) {
                Write-Ok "翻译模型: $model ($mb MB，SHA256 正确)"
            } else {
                Write-Err2 "翻译模型 SHA256 不匹配: $model"
                $ok = $false
            }
        } elseif ($isDefaultModel) {
            Write-Err2 "默认翻译模型文件不完整: $model"
            $ok = $false
        } else {
            Write-Ok "自定义翻译模型: $model ($mb MB，GGUF 文件头正确)"
        }
    } else {
        Write-Err2 "缺少 $model"
        $ok = $false
    }

    $ocrRequired = @("PP-OCRv6_medium_det", "PP-OCRv6_medium_rec")
    $ocrReady = $true
    foreach ($name in $ocrRequired) {
        $dir = Join-Path $ocr $name
        if (-not (Test-Path -LiteralPath $dir) -or -not (Get-ChildItem -LiteralPath $dir -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1)) {
            $ocrReady = $false
        }
    }
    if ($ocrReady) {
        $names = @(Get-ChildItem -LiteralPath $ocr -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name})
        Write-Ok ("OCR 模型目录: $ocr (" + ($names -join ", ") + ")")
    } else {
        Write-Err2 "缺少 $ocr"
        $ok = $false
    }

    if (-not $ok) {
        Write-Warn2 "runtime 不齐：请把 Releases 的 models、llama 两个包解压到 runtime 目录（OCR 随源码；也可用 -DownloadRuntime）。"
    }
    return $ok
}

function Test-Imports {
    param([string]$VenvPy)
    Write-Step "冒烟导入"
    if (-not (Test-Path -LiteralPath $VenvPy)) {
        throw "缺少 venv，无法检查 Python 依赖"
    }
    $script = Join-Path $Root "scripts\smoke_import.py"
    & $VenvPy $script
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "app 导入成功"
    } else {
        throw "真实依赖或 app.main 导入失败"
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
    $checkOk = $runtimeOk
    $venvPy = Join-Path $Root "venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPy) {
        if (-not (Test-SupportedPython $venvPy)) {
            throw "venv Python 版本不受支持（仅 3.11～3.13）"
        }
        Test-Imports -VenvPy $venvPy
    } else {
        Write-Err2 "尚未创建 venv，完整安装请运行: .\setup.ps1"
        $checkOk = $false
    }
    Write-Host ""
    if ($checkOk) {
        Write-Ok "体检结束"
        exit 0
    }
    Write-Warn2 "体检结束（运行环境或 runtime 有缺失）"
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
if (-not (Test-SupportedPython $venvPy)) {
    throw "现有 venv 不是受支持的 Python 3.11～3.13；请删除 venv 后重新运行 setup.ps1"
}
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
Write-Host '  说明: models/llama 用 Release 两包或脚本下载；paddlex 随源码；venv 每机跑本脚本'
Write-Host ""

if (-not $runtimeOk) { exit 2 }
exit 0
