#Requires -Version 5.1
<#
.SYNOPSIS
  下载 ScreenTranslator 运行资源到 runtime/（翻译模型 + llama-server；OCR 可选预热）

.DESCRIPTION
  来源（官方）：
  - 翻译模型 GGUF: https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF
  - llama-server:  https://github.com/ggml-org/llama.cpp/releases
  - OCR 模型:      源码已带 runtime/paddlex/official_models；-WarmOcr 可补拉/校验
                   项目说明 https://github.com/PaddlePaddle/PaddleOCR

  用法（在项目根）：
    .\scripts\download_runtime.ps1
    .\scripts\download_runtime.ps1 -CpuOnly          # 下 CPU 版 llama
    .\scripts\download_runtime.ps1 -SkipModel        # 已有 gguf
    .\scripts\download_runtime.ps1 -SkipLlama
    .\scripts\download_runtime.ps1 -WarmOcr          # 需已装 venv+Paddle，预热 OCR 缓存
    .\scripts\download_runtime.ps1 -Force            # 覆盖已有文件
#>

param(
    [switch]$CpuOnly,
    [switch]$SkipModel,
    [switch]$SkipLlama,
    [switch]$WarmOcr,
    [switch]$Force,
    # 可选：指定 llama.cpp release tag，如 b10058；空则取最新
    [string]$LlamaTag = "",
    # 量化档：Q4_K_M（推荐）/ Q6_K / Q8_0
    [ValidateSet("Q4_K_M", "Q6_K", "Q8_0")]
    [string]$Quant = "Q4_K_M"
)

$ErrorActionPreference = "Stop"
# scripts/ 的上一级 = 项目根
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

function Write-Step([string]$m) { Write-Host ""; Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok([string]$m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn2([string]$m){ Write-Host "  [!] $m" -ForegroundColor Yellow }
function Write-Err2([string]$m) { Write-Host "  [X] $m" -ForegroundColor Red }

function Get-File(
    [string]$Url,
    [string]$OutPath,
    [string]$ExpectedSha256 = "",
    [long]$MinBytes = 1
) {
    $dir = Split-Path $OutPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Write-Host "  GET $Url"
    Write-Host "  ->  $OutPath"
    # TLS
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    # 跟随重定向；大文件用 WebClient 显示简单进度
    $part = "$OutPath.part"
    if (Test-Path -LiteralPath $part) { Remove-Item -LiteralPath $part -Force }
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "ScreenTranslator-setup")
    try {
        $wc.DownloadFile($Url, $part)
    } finally {
        $wc.Dispose()
    }
    if (-not (Test-Path -LiteralPath $part)) { throw "下载失败: $OutPath" }
    $length = (Get-Item -LiteralPath $part).Length
    if ($length -lt $MinBytes) {
        Remove-Item -LiteralPath $part -Force
        throw "下载文件过小（$length bytes）: $OutPath"
    }
    if ($ExpectedSha256) {
        $actual = (Get-FileHash -LiteralPath $part -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $ExpectedSha256.ToLowerInvariant()) {
            Remove-Item -LiteralPath $part -Force
            throw "SHA256 校验失败: $OutPath"
        }
    }
    Move-Item -LiteralPath $part -Destination $OutPath -Force
    $mb = [math]::Round($length / 1MB, 1)
    Write-Ok ("完成 {0} MB" -f $mb)
}

function Test-Gguf([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    if ((Get-Item -LiteralPath $Path).Length -lt 100MB) { return $false }
    $fs = [System.IO.File]::OpenRead($Path)
    try {
        $b = New-Object byte[] 4
        [void]$fs.Read($b, 0, 4)
        return ([System.Text.Encoding]::ASCII.GetString($b) -eq "GGUF")
    } finally { $fs.Dispose() }
}

function Test-Nvidia {
    try {
        $c = Get-Command nvidia-smi -ErrorAction SilentlyContinue
        if (-not $c) { return $false }
        $o = & nvidia-smi -L 2>$null
        return ($LASTEXITCODE -eq 0 -and $o -match "GPU")
    } catch { return $false }
}

# ---------- 1) HY-MT GGUF ----------
if (-not $SkipModel) {
    Write-Step "翻译模型 HY-MT1.5-1.8B ($Quant)"
    $name = "HY-MT1.5-1.8B-$Quant.gguf"
    $dest = Join-Path $Root "runtime\models\$name"
    $knownSha = ""
    if ($name -eq "HY-MT1.5-1.8B-Q4_K_M.gguf") {
        $knownSha = "4383ac0c3c8e476de98ff979c2a3f069f8c4fb385e7860cf2d28da896cc477c7"
    }
    $existingValid = Test-Gguf $dest
    if ($existingValid -and $knownSha) {
        $existingValid = ((Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant() -eq $knownSha)
    }
    if ((Test-Path $dest) -and -not $Force -and $existingValid) {
        Write-Ok "已存在且格式有效，跳过: $dest （-Force 可重下）"
    } else {
        # HuggingFace resolve 直链（需能访问 huggingface.co）
        $url = "https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF/resolve/main/$name"
        try {
            $sha = ""
            $sha = $knownSha
            try {
                $meta = Invoke-RestMethod -Uri "https://huggingface.co/api/models/tencent/HY-MT1.5-1.8B-GGUF?blobs=true" -Headers @{"User-Agent"="ScreenTranslator-setup"}
                $entry = @($meta.siblings) | Where-Object { $_.rfilename -eq $name } | Select-Object -First 1
                if ($entry.lfs.sha256) { $sha = [string]$entry.lfs.sha256 }
            } catch {
                Write-Warn2 "未取得 HuggingFace SHA256，将使用 GGUF 格式与大小校验"
            }
            Get-File $url $dest $sha 100MB
            if (-not (Test-Gguf $dest)) { throw "下载结果不是有效 GGUF" }
        } catch {
            Write-Err2 "自动下载失败: $_"
            Write-Warn2 "请手动下载后放到 runtime\models\ :"
            Write-Host "  页面: https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF/tree/main"
            Write-Host "  推荐: HY-MT1.5-1.8B-Q4_K_M.gguf （约 1.1GB）"
            Write-Host "  直链: $url"
            throw
        }
    }
    # 若量化不是默认 Q4，提示改 config
    if ($Quant -ne "Q4_K_M") {
        Write-Warn2 "当前量化 $Quant，请在 config.json 中把 model_path 设为 runtime/models/$name"
    }
} else {
    Write-Warn2 "跳过模型下载 (-SkipModel)"
}

# ---------- 2) llama.cpp 预编译 ----------
if (-not $SkipLlama) {
    Write-Step "llama-server（llama.cpp Releases）"
    $llamaDir = Join-Path $Root "runtime\llama"
    $server = Join-Path $llamaDir "llama-server.exe"
    if ((Test-Path $server) -and -not $Force) {
        $oldEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $server --version 1>$null 2>$null
        $serverCode = $LASTEXITCODE
        $ErrorActionPreference = $oldEap
        if ($serverCode -ne 0) {
            throw "现有 llama-server 无法运行；请使用 -Force 重新下载"
        }
        Write-Ok "已存在且可运行 llama-server.exe，跳过 （-Force 可重下）"
    } else {
        $wantCuda = (-not $CpuOnly) -and (Test-Nvidia)
        if ($CpuOnly) {
            Write-Host "  变体: Windows x64 CPU"
        } elseif ($wantCuda) {
            Write-Host "  变体: Windows x64 CUDA 12.4（需较新 NVIDIA 驱动）"
        } else {
            Write-Host "  变体: 未检测到 GPU → Windows x64 CPU"
            $wantCuda = $false
        }

        Write-Host "  查询 GitHub Releases..."
        $api = "https://api.github.com/repos/ggml-org/llama.cpp/releases"
        if ($LlamaTag) {
            $api = "https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$LlamaTag"
        } else {
            $api = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
        }
        $headers = @{
            "User-Agent" = "ScreenTranslator-setup"
            "Accept"     = "application/vnd.github+json"
        }
        try {
            $rel = Invoke-RestMethod -Uri $api -Headers $headers
        } catch {
            Write-Err2 "无法访问 GitHub API: $_"
            Write-Warn2 "请手动从 https://github.com/ggml-org/llama.cpp/releases 下载 Windows 压缩包，解压到 runtime\llama\"
            throw
        }
        $tag = $rel.tag_name
        Write-Host "  release: $tag"

        $assets = @($rel.assets)
        function Pick-Asset([string]$pattern) {
            return $assets | Where-Object { $_.name -match $pattern } | Select-Object -First 1
        }

        if ($wantCuda) {
            $bin = Pick-Asset "bin-win-cuda-12\.4-x64\.zip$"
            if (-not $bin) { $bin = Pick-Asset "bin-win-cuda-12.*-x64\.zip$" }
            $rt  = Pick-Asset "cudart-llama-bin-win-cuda-12\.4-x64\.zip$"
            if (-not $rt)  { $rt  = Pick-Asset "cudart-llama-bin-win-cuda-12.*-x64\.zip$" }
        } else {
            $bin = Pick-Asset "bin-win-cpu-x64\.zip$"
            $rt  = $null
        }
        if (-not $bin) {
            Write-Err2 "在 release $tag 中未找到匹配的 Windows zip，请打开 Releases 页手动选："
            Write-Host "  https://github.com/ggml-org/llama.cpp/releases/tag/$tag"
            throw "无匹配 asset"
        }

        $safeTag = $tag -replace '[^A-Za-z0-9._-]', '_'
        $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
        $tmp = [System.IO.Path]::GetFullPath((Join-Path $tempRoot "st_llama_$safeTag"))
        if (-not $tmp.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "临时目录越界: $tmp"
        }
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $tmp | Out-Null

        $binZip = Join-Path $tmp $bin.name
        $binSha = if ($bin.digest -match '^sha256:(.+)$') { $Matches[1] } else { "" }
        Get-File $bin.browser_download_url $binZip $binSha 1MB
        if ($rt) {
            $rtZip = Join-Path $tmp $rt.name
            $rtSha = if ($rt.digest -match '^sha256:(.+)$') { $Matches[1] } else { "" }
            Get-File $rt.browser_download_url $rtZip $rtSha 1MB
        }

        if (-not (Test-Path $llamaDir)) { New-Item -ItemType Directory -Force -Path $llamaDir | Out-Null }
        # 解压到临时再拷 exe/dll 到 llamaDir（避免嵌套目录）
        $extract = Join-Path $tmp "extract"
        New-Item -ItemType Directory -Force -Path $extract | Out-Null
        Expand-Archive -LiteralPath $binZip -DestinationPath $extract -Force
        if ($rt) {
            Expand-Archive -LiteralPath $rtZip -DestinationPath $extract -Force
        }
        Get-ChildItem $extract -Recurse -Include *.exe,*.dll | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $llamaDir $_.Name) -Force
        }
        if (-not (Test-Path (Join-Path $llamaDir "llama-server.exe"))) {
            # 有的包在子目录且名字一致；再搜一层
            $found = Get-ChildItem $extract -Recurse -Filter "llama-server.exe" | Select-Object -First 1
            if ($found) {
                Copy-Item $found.FullName (Join-Path $llamaDir "llama-server.exe") -Force
                Get-ChildItem $found.DirectoryName -Filter *.dll | ForEach-Object {
                    Copy-Item $_.FullName (Join-Path $llamaDir $_.Name) -Force
                }
            }
        }
        if (-not (Test-Path (Join-Path $llamaDir "llama-server.exe"))) {
            throw "解压后未找到 llama-server.exe，请检查 zip 结构"
        }
        Write-Ok "llama 已安装到 $llamaDir"
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Warn2 "跳过 llama 下载 (-SkipLlama)"
}

# ---------- 3) OCR 预热（可选）----------
if ($WarmOcr) {
    Write-Step "OCR 模型预热（PaddleOCR → runtime/paddlex）"
    $py = Join-Path $Root "venv\Scripts\python.exe"
    if (-not (Test-Path $py)) {
        Write-Warn2 "无 venv，请先 .\setup.ps1 再 -WarmOcr"
    } else {
        $code = @"
import os, sys
from pathlib import Path
root = Path(r'$($Root.Replace('\','\\'))')
pdx = root / 'runtime' / 'paddlex'
pdx.mkdir(parents=True, exist_ok=True)
os.environ['PADDLE_PDX_CACHE_HOME'] = str(pdx)
sys.path.insert(0, str(root))
from paddleocr import PaddleOCR
print('init PaddleOCR...')
PaddleOCR(use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
print('ocr cache ready', pdx)
"@
        $tmpPy = Join-Path $env:TEMP "st_warm_ocr.py"
        # UTF8 no BOM issues: use python -c via file utf8
        [System.IO.File]::WriteAllText($tmpPy, $code, [System.Text.UTF8Encoding]::new($false))
        & $py $tmpPy
        if ($LASTEXITCODE -eq 0) { Write-Ok "OCR 缓存应在 runtime\paddlex\official_models" }
        else { Write-Warn2 "OCR 预热失败（可稍后首次截屏时自动下）" }
        Remove-Item $tmpPy -ErrorAction SilentlyContinue
    }
} else {
    Write-Host ""
    Write-Host "  OCR: 源码应已带 runtime\paddlex\official_models；缺则 -WarmOcr 或首次截屏补拉"
    Write-Host "       说明: https://github.com/PaddlePaddle/PaddleOCR"
}

Write-Step "完成"
Write-Host @"

  目录:
    runtime\models\   HY-MT *.gguf     （Release models 包 / 本脚本）
    runtime\llama\    llama-server + DLL（Release llama 包 / 本脚本）
    runtime\paddlex\  OCR（随源码；可选 -WarmOcr）

  官方地址:
    模型  https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF
    推理  https://github.com/ggml-org/llama.cpp/releases
    OCR   https://github.com/PaddlePaddle/PaddleOCR

  若 HuggingFace / GitHub 访问失败，请用浏览器手动下载后按 runtime\README.md 放置。

"@
exit 0
