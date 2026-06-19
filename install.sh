#!/bin/bash
# 作者: 阿洋
# ============================================================================
# Yang.skills Installer for macOS / Linux
# ============================================================================
#
# 用法: bash install.sh [--target <path>] [--skip-clone] [--tier core|media|full]
#
# 参数说明:
#   --target <path>          指定安装目标路径（默认: 当前目录）
#   --skip-clone             跳过 Git 克隆步骤，使用当前目录作为安装源
#   --tier core|media|full   选择依赖安装层级（默认: core）
#       core   : 仅安装核心闭环依赖（requirements-core.txt）
#       media  : 核心依赖 + 媒体处理依赖（requirements-media.txt）
#                并提示运行 `playwright install chromium`
#       full   : 核心依赖 + 媒体依赖 + 全量依赖（requirements-full.txt）
#
# 安装步骤概览:
#   [1/5] 检查环境 —— 验证 Git / Python / pip 是否已安装
#   [2/5] 下载 Yang.skills —— 从 GitHub 克隆或更新已有安装
#   [3/5] 验证文件完整性 —— 检查核心 SKILL.md 文件是否存在
#   [4/5] 安装 Python 依赖 —— 根据 --tier 执行 pip install
#   [5/5] 安装完成 —— 输出下一步指引
#
# 常见安装失败排查:
#   1. "未找到 Git" → 安装 Git:
#      macOS:   brew install git
#      Ubuntu:  sudo apt install git
#      CentOS:  sudo yum install git
#
#   2. "克隆失败/超时" → 检查网络连接或使用 --skip-clone:
#      bash install.sh --skip-clone
#      （需先将项目手动下载到目标目录）
#
#   3. "缺失文件" → 重新克隆:
#      rm -rf Yang.skills
#      bash install.sh
#
#   4. "权限不足" → 确保对目标目录有写权限:
#      chmod +w <target_path>
#
#   5. "pip install 失败" → 建议使用虚拟环境:
#      python3 -m venv .venv && source .venv/bin/activate
#      bash install.sh --skip-clone --tier core
#
# 安装后验证命令:
#   ls Yang.skills/SKILL.md                    # 检查主入口文件
#   ls Yang.skills/skills/yang-init/SKILL.md   # 检查初始化 skill
#   ls Yang.skills/shared-protocols/            # 检查共享协议目录
#   cat Yang.skills/.yang-state.json 2>/dev/null || echo "尚未初始化，请运行 yang-init"
#
# ============================================================================

set -euo pipefail

# 安装配置
TARGET_PATH="."                      # 默认安装到当前目录
SKIP_CLONE=false                     # 是否跳过克隆步骤
TIER="core"                          # 依赖层级：core | media | full
# 仓库地址与 .claude-plugin/marketplace.json 中的 repository 字段保持一致
REPO="https://github.com/LearnPrompt/Yang.skills.git"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --target)
            TARGET_PATH="$2"          # 指定安装目标路径
            shift 2
            ;;
        --skip-clone)
            SKIP_CLONE=true           # 跳过克隆，使用当前目录
            shift
            ;;
        --tier)
            TIER="$2"                 # 依赖层级
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            echo "用法: bash install.sh [--target <path>] [--skip-clone] [--tier core|media|full]"
            exit 1
            ;;
    esac
done

# 校验 tier 参数取值
case "$TIER" in
    core|media|full)
        ;;
    *)
        echo "错误: --tier 仅支持 core | media | full，当前值: $TIER"
        exit 1
        ;;
esac

echo "========================================"
echo "  Yang.skills · 全能内容创作运营超级Skills包"
echo "  Installer v2.0 (tier=$TIER)"
echo "========================================"
echo ""
# ──────────────────────────────────────────────────────────────
# [1/5] 检查环境
# 作用：验证 Git / Python / pip 是否已安装
# 预期输出：✓ Git 已安装 / ✓ Python 已安装 / ✓ pip 已安装
# 失败时：✗ 未找到对应工具 + 安装提示
# ──────────────────────────────────────────────────────────────
echo -e "\033[32m[1/5] 检查环境...\033[0m"
if command -v git &> /dev/null; then
    echo "  ✓ Git 已安装"
else
    echo "  ✗ 未找到 Git。请先安装 Git。"
    echo "  macOS: brew install git"
    echo "  Ubuntu/Debian: sudo apt install git"
    exit 1
fi

# Python 检查（优先 python3，回退 python）
PYTHON_BIN=""
if command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
elif command -v python &> /dev/null; then
    PYTHON_BIN="python"
else
    echo "  ✗ 未找到 Python。请先安装 Python 3.8+。"
    echo "  macOS: brew install python"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    exit 1
fi
echo "  ✓ Python 已安装 ($PYTHON_BIN)"

# pip 检查
if "$PYTHON_BIN" -m pip --version &> /dev/null; then
    echo "  ✓ pip 已安装"
else
    echo "  ✗ 未找到 pip。请先安装 pip。"
    echo "  Ubuntu/Debian: sudo apt install python3-pip"
    exit 1
fi

# ──────────────────────────────────────────────────────────────
# [2/5] 下载 Yang.skills
# 作用：从 GitHub 克隆项目，或更新已有安装
# 预期输出：
#   新安装：✓ 下载完成 -> <安装路径>
#   已存在：✓ 已更新到最新版本
#   --skip-clone：跳过下载，使用当前目录
# 排查：克隆失败通常是网络问题，可使用 --skip-clone 手动下载
# ──────────────────────────────────────────────────────────────
if [ "$SKIP_CLONE" = false ]; then
    echo -e "\033[32m[2/5] 下载 Yang.skills...\033[0m"
    
    INSTALL_DIR="$TARGET_PATH/Yang.skills"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo "  ! Yang.skills 已存在于 $INSTALL_DIR"
        echo "  正在更新..."
        cd "$INSTALL_DIR"
        git pull origin main
        cd - > /dev/null
        echo "  ✓ 已更新到最新版本"
    else
        echo "  从 GitHub 克隆..."
        git clone "$REPO" "$INSTALL_DIR"
        echo "  ✓ 下载完成 -> $INSTALL_DIR"
    fi
else
    INSTALL_DIR="$TARGET_PATH"
    echo -e "\033[32m[2/5] 跳过下载 (--skip-clone)，使用当前目录: $INSTALL_DIR\033[0m"
fi

# ──────────────────────────────────────────────────────────────
# [3/5] 验证文件完整性
# 作用：检查核心 SKILL.md 文件是否全部存在
# 预期输出：✓ 核心文件验证通过
# 失败时：✗ 缺失文件列表 + 重新克隆建议
# 排查：如果核心文件缺失，通常是克隆不完整，建议删除目录后重新安装
# ──────────────────────────────────────────────────────────────
echo -e "\033[32m[3/5] 验证文件完整性...\033[0m"

# 核心文件清单：这些文件是 Yang.skills 运行的最低要求
# 如果缺少任何一个，系统将无法正常初始化或运行核心闭环
REQUIRED_FILES=(
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

# 逐个检查核心文件是否存在
MISSING=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$INSTALL_DIR/$file" ]; then
        MISSING+=("$file")
    fi
done

# 如果有缺失文件，输出错误并退出
if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "\033[31m  ✗ 缺失文件:\033[0m"
    for f in "${MISSING[@]}"; do
        echo "    - $f"
    done
    echo "  请重新克隆或检查网络连接。"
    exit 1
fi
echo "  ✓ 核心文件验证通过"

# ──────────────────────────────────────────────────────────────
# [4/5] 安装 Python 依赖
# 作用：根据 --tier 参数执行对应的 pip install
# 层级说明:
#   core  : requirements-core.txt（核心闭环唯一必需依赖 requests）
#   media : core + requirements-media.txt（playwright/yt-dlp/whisper 等）
#           安装后需手动执行 `playwright install chromium`
#   full  : core + media + requirements-full.txt（graphrag 等全量依赖）
# 排查：pip install 失败建议使用虚拟环境，或加 --user 参数
# ──────────────────────────────────────────────────────────────
echo -e "\033[32m[4/5] 安装 Python 依赖 (tier=$TIER)...\033[0m"

cd "$INSTALL_DIR"

case "$TIER" in
    core)
        echo "  安装核心依赖: requirements-core.txt"
        "$PYTHON_BIN" -m pip install -r requirements-core.txt
        ;;
    media)
        echo "  安装核心依赖: requirements-core.txt"
        "$PYTHON_BIN" -m pip install -r requirements-core.txt
        echo "  安装媒体依赖: requirements-media.txt"
        "$PYTHON_BIN" -m pip install -r requirements-media.txt
        echo -e "\033[33m  ! 媒体层级需要浏览器内核，请手动执行:\033[0m"
        echo -e "     \033[33mplaywright install chromium\033[0m"
        ;;
    full)
        echo "  安装核心依赖: requirements-core.txt"
        "$PYTHON_BIN" -m pip install -r requirements-core.txt
        echo "  安装媒体依赖: requirements-media.txt"
        "$PYTHON_BIN" -m pip install -r requirements-media.txt
        echo "  安装全量依赖: requirements-full.txt"
        "$PYTHON_BIN" -m pip install -r requirements-full.txt
        ;;
esac

echo "  ✓ Python 依赖安装完成"

cd - > /dev/null

# ──────────────────────────────────────────────────────────────
# [5/5] 安装完成
# 作用：输出安装路径和下一步操作指引
# 预期输出：安装路径 + 初始化命令 + 可用 skill 列表
# ──────────────────────────────────────────────────────────────
echo -e "\033[32m[5/5] 安装完成！\033[0m"
echo ""
echo "========================================"
echo "  下一步:"
echo "========================================"
echo ""
echo "  1. 进入你的内容项目目录"
echo "  2. 告诉你的 AI 助手加载 Yang.skills:"
echo ""
echo "     将 Yang.skills 目录配置为技能目录，然后说:"
echo ""
echo -e "     \033[33m/yang-init\033[0m"
echo ""
echo "  这会创建:"
echo "    .yang-state.json     - 运行时状态文件"
echo "    rubric_notes.md      - 评分规则"
echo "    candidates.md        - 选题候选池"
echo "    predictions/         - 预测日志目录"
echo "    scripts/             - 脚本草稿目录"
echo ""
echo "  然后你可以:"
echo "    /yang-learn-from  → 导入对标账号"
echo "    /yang-seed        → 生成选题"
echo "    /yang-score       → 给稿子打分"
echo "    /yang-predict     → 盲预测播放量"
echo "    /yang-retro       → 3天后复盘"
echo ""
echo "  Yang.skills 安装路径: $INSTALL_DIR"
echo "  已安装依赖层级: $TIER"
echo ""
echo "========================================"
echo "  安装后验证命令（可选）："
echo "========================================"
echo ""
echo "  # 验证主入口文件存在"
echo "  ls $INSTALL_DIR/SKILL.md"
echo ""
echo "  # 验证初始化 skill 存在"
echo "  ls $INSTALL_DIR/skills/yang-init/SKILL.md"
echo ""
echo "  # 验证共享协议目录存在"
echo "  ls $INSTALL_DIR/shared-protocols/"
echo ""
echo "  # 检查是否已初始化（未初始化会提示运行 yang-init）"
echo "  cat .yang-state.json 2>/dev/null || echo '尚未初始化，请运行 yang-init'"
echo ""
echo "========================================"

exit 0
