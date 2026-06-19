#!/usr/bin/env bash
# 作者: 阿洋
# quick-score.sh — 快速评分脚本
# 封装 yang-score 的常用调用，支持单文件/批量/最近文件评分
# 用法:
#   bash scripts/quick-score.sh <脚本路径>          # 评分单个脚本
#   bash scripts/quick-score.sh --latest            # 评分 scripts/ 下最新修改的脚本
#   bash scripts/quick-score.sh --batch             # 批量评分 scripts/ 下所有未评分脚本
#   bash scripts/quick-score.sh --batch --force     # 批量评分所有脚本（含已评分）

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目目录（脚本所在目录的上级）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# 参数解析
MODE="single"
FORCE=false
TARGET=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --latest)
            MODE="latest"
            shift
            ;;
        --batch)
            MODE="batch"
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "用法: bash scripts/quick-score.sh [选项] [脚本路径]"
            echo ""
            echo "选项:"
            echo "  <脚本路径>     评分指定的脚本文件"
            echo "  --latest       评分 scripts/ 下最新修改的脚本"
            echo "  --batch        批量评分 scripts/ 下所有未评分脚本"
            echo "  --force        与 --batch 配合，重新评分已评分脚本"
            echo "  --help         显示帮助信息"
            echo ""
            echo "示例:"
            echo "  bash scripts/quick-score.sh scripts/my-draft.md"
            echo "  bash scripts/quick-score.sh --latest"
            echo "  bash scripts/quick-score.sh --batch"
            exit 0
            ;;
        *)
            TARGET="$1"
            MODE="single"
            shift
            ;;
    esac
done

# 前置检查
check_prerequisites() {
    if [ ! -f "$PROJECT_DIR/.yang-state.json" ]; then
        echo -e "${RED}❌ 项目未初始化。请先运行 yang-init${NC}"
        exit 1
    fi

    if [ ! -f "$PROJECT_DIR/rubric_notes.md" ]; then
        echo -e "${RED}❌ rubric_notes.md 不存在。请先运行 yang-init${NC}"
        exit 1
    fi
}

# 检查脚本是否已评分（尾部包含评分块）
is_scored() {
    local file="$1"
    grep -q "### 📊 Yang.skills 评分" "$file" 2>/dev/null
}

# 执行评分
do_score() {
    local file="$1"
    local basename
    basename=$(basename "$file")

    if is_scored "$file" && [ "$FORCE" = false ]; then
        echo -e "${YELLOW}⏭️  已评分，跳过: $basename${NC}（使用 --force 重新评分）"
        return 0
    fi

    echo -e "${CYAN}📊 评分: $basename${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 调用 yang-score
    # 这里使用 Claude Code 的 skill 触发机制
    # 实际使用时，用户应在 Claude Code 对话中运行 yang-score
    echo ""
    echo "请在 Claude Code 中运行以下命令："
    echo ""
    echo -e "${GREEN}  打分这篇 $file${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# 单文件模式
score_single() {
    if [ -z "$TARGET" ]; then
        echo -e "${RED}❌ 请指定脚本文件路径${NC}"
        echo "用法: bash scripts/quick-score.sh <脚本路径>"
        exit 1
    fi

    if [ ! -f "$TARGET" ]; then
        echo -e "${RED}❌ 文件不存在: $TARGET${NC}"
        exit 1
    fi

    do_score "$TARGET"
}

# 最新文件模式
score_latest() {
    if [ ! -d "$SCRIPTS_DIR" ]; then
        echo -e "${RED}❌ scripts/ 目录不存在${NC}"
        exit 1
    fi

    local latest
    latest=$(find "$SCRIPTS_DIR" -maxdepth 1 -name "*.md" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

    if [ -z "$latest" ]; then
        echo -e "${RED}❌ scripts/ 目录下没有 .md 脚本文件${NC}"
        exit 1
    fi

    echo -e "${CYAN}📁 最新脚本: $(basename "$latest")${NC}"
    do_score "$latest"
}

# 批量模式
score_batch() {
    if [ ! -d "$SCRIPTS_DIR" ]; then
        echo -e "${RED}❌ scripts/ 目录不存在${NC}"
        exit 1
    fi

    local total=0
    local scored=0
    local skipped=0

    for file in "$SCRIPTS_DIR"/*.md; do
        [ -f "$file" ] || continue
        total=$((total + 1))

        if is_scored "$file" && [ "$FORCE" = false ]; then
            skipped=$((skipped + 1))
            continue
        fi

        do_score "$file"
        scored=$((scored + 1))
    done

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 批量评分汇总"
    echo "  总脚本数: $total"
    echo -e "  ${GREEN}待评分: $scored${NC}"
    echo -e "  ${YELLOW}已评分(跳过): $skipped${NC}"

    if [ "$scored" -eq 0 ]; then
        echo ""
        echo -e "${YELLOW}💡 所有脚本均已评分。使用 --force 重新评分。${NC}"
    fi
}

# 主流程
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Yang.skills 快速评分"
echo "📁 项目目录: $PROJECT_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

check_prerequisites

case "$MODE" in
    single)
        score_single
        ;;
    latest)
        score_latest
        ;;
    batch)
        score_batch
        ;;
esac
