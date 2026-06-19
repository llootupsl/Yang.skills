# Yang.skills Installer for Windows (PowerShell)
# 用法: .\install.ps1 [-Target <path>] [-SkipClone] [-Tier core|media|full]
#
# 参数说明:
#   -Target <path>     指定安装目标路径（默认: 当前目录）
#   -SkipClone         跳过 Git 克隆步骤，使用当前目录作为安装源
#   -Tier core|media|full  选择依赖安装层级（默认: core）
#       core   : 仅安装核心闭环依赖（requirements-core.txt）
#       media  : 核心依赖 + 媒体处理依赖（requirements-media.txt）
#                并提示运行 `playwright install chromium`
#       full   : 核心依赖 + 媒体依赖 + 全量依赖（requirements-full.txt）

param(
    [string]$Target = ".",
    [switch]$SkipClone,
    [ValidateSet("core","media","full")]
    [string]$Tier = "core"
)

$ErrorActionPreference = "Stop"
# 仓库地址与 .claude-plugin/marketplace.json 中的 repository 字段保持一致
$Repo = "https://github.com/LearnPrompt/Yang.skills.git"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Yang.skills · 全能内容创作运营超级Skills包" -ForegroundColor Cyan
Write-Host "  Installer v2.0 (tier=$Tier)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# [1/5] 检查环境
Write-Host "[1/5] 检查环境..." -ForegroundColor Green
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ Git 已安装"
} else {
    Write-Host "  ✗ 未找到 Git。请先安装 Git。" -ForegroundColor Red
    Write-Host "  https://git-scm.com/download/win"
    exit 1
}

# Python 检查（优先 python，回退 py）
$PythonBin = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonBin = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonBin = "py"
} else {
    Write-Host "  ✗ 未找到 Python。请先安装 Python 3.8+。" -ForegroundColor Red
    Write-Host "  https://www.python.org/downloads/windows/"
    exit 1
}
Write-Host "  ✓ Python 已安装 ($PythonBin)"

# pip 检查
try {
    & $PythonBin -m pip --version | Out-Null
    Write-Host "  ✓ pip 已安装"
} catch {
    Write-Host "  ✗ 未找到 pip。请重新安装 Python 并勾选 pip 选项。" -ForegroundColor Red
    exit 1
}

# [2/5] 下载 Yang.skills
if (-not $SkipClone) {
    Write-Host "[2/5] 下载 Yang.skills..." -ForegroundColor Green
    
    $InstallDir = Join-Path $Target "Yang.skills"
    
    if (Test-Path $InstallDir) {
        Write-Host "  ! Yang.skills 已存在于 $InstallDir" -ForegroundColor Yellow
        Write-Host "  正在更新..."
        Push-Location $InstallDir
        git pull origin main
        Pop-Location
        Write-Host "  ✓ 已更新到最新版本"
    } else {
        Write-Host "  从 GitHub 克隆..."
        git clone $Repo $InstallDir
        Write-Host "  ✓ 下载完成 -> $InstallDir"
    }
} else {
    $InstallDir = $Target
    Write-Host "[2/5] 跳过下载 (-SkipClone)，使用当前目录: $InstallDir" -ForegroundColor Green
}

# [3/5] 验证文件完整性
Write-Host "[3/5] 验证文件完整性..." -ForegroundColor Green

$RequiredFiles = @(
    "SKILL.md"
    "skills/yang-init/SKILL.md"
    "skills/yang-seed/SKILL.md"
    "skills/yang-score/SKILL.md"
    "skills/yang-predict/SKILL.md"
    "skills/yang-retro/SKILL.md"
    "skills/yang-bump/SKILL.md"
    "knowledge/ansir/SKILL.md"
    "shared-protocols/blind-prediction-protocol.md"
)

$Missing = @()
foreach ($file in $RequiredFiles) {
    if (-not (Test-Path (Join-Path $InstallDir $file))) {
        $Missing += $file
    }
}

if ($Missing.Count -gt 0) {
    Write-Host "  ✗ 缺失文件:" -ForegroundColor Red
    foreach ($f in $Missing) {
        Write-Host "    - $f"
    }
    Write-Host "  请重新克隆或检查网络连接。"
    exit 1
}
Write-Host "  ✓ 核心文件验证通过"

# [4/5] 安装 Python 依赖
Write-Host "[4/5] 安装 Python 依赖 (tier=$Tier)..." -ForegroundColor Green

Push-Location $InstallDir
try {
    switch ($Tier) {
        "core" {
            Write-Host "  安装核心依赖: requirements-core.txt"
            & $PythonBin -m pip install -r requirements-core.txt
        }
        "media" {
            Write-Host "  安装核心依赖: requirements-core.txt"
            & $PythonBin -m pip install -r requirements-core.txt
            Write-Host "  安装媒体依赖: requirements-media.txt"
            & $PythonBin -m pip install -r requirements-media.txt
            Write-Host "  ! 媒体层级需要浏览器内核，请手动执行:" -ForegroundColor Yellow
            Write-Host "     playwright install chromium" -ForegroundColor Yellow
        }
        "full" {
            Write-Host "  安装核心依赖: requirements-core.txt"
            & $PythonBin -m pip install -r requirements-core.txt
            Write-Host "  安装媒体依赖: requirements-media.txt"
            & $PythonBin -m pip install -r requirements-media.txt
            Write-Host "  安装全量依赖: requirements-full.txt"
            & $PythonBin -m pip install -r requirements-full.txt
        }
    }
    Write-Host "  ✓ Python 依赖安装完成"
} finally {
    Pop-Location
}

# [5/5] 安装完成
Write-Host "[5/5] 安装完成！" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  下一步:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. 进入你的内容项目目录"
Write-Host "  2. 告诉你的 AI 助手加载 Yang.skills:"
Write-Host ""
Write-Host "     将 Yang.skills 目录配置为技能目录，然后说:"
Write-Host ""
Write-Host "     /yang-init" -ForegroundColor Yellow
Write-Host ""
Write-Host "  这会创建:"
Write-Host "    .yang-state.json     - 运行时状态文件"
Write-Host "    rubric_notes.md      - 评分规则"
Write-Host "    candidates.md        - 选题候选池"
Write-Host "    predictions/         - 预测日志目录"
Write-Host "    scripts/             - 脚本草稿目录"
Write-Host ""
Write-Host "  然后你可以:"
Write-Host "    /yang-learn-from  → 导入对标账号"
Write-Host "    /yang-seed        → 生成选题"
Write-Host "    /yang-score       → 给稿子打分"
Write-Host "    /yang-predict     → 盲预测播放量"
Write-Host "    /yang-retro       → 3天后复盘"
Write-Host ""
Write-Host "  Yang.skills 安装路径: $InstallDir" -ForegroundColor Cyan
Write-Host "  已安装依赖层级: $Tier" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

exit 0
