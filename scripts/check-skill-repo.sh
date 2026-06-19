#!/usr/bin/env bash
# 作者: 阿洋
# check-skill-repo.sh — Yang.skills 仓库结构完整性检查
# 验证 Skill 仓库的目录结构、frontmatter 字段、必需文件等
# 用法: bash scripts/check-skill-repo.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check_file() {
    local label="$1"
    local path="$2"
    local required="${3:-true}"

    if [ -f "$path" ]; then
        local size
        size=$(wc -c < "$path")
        if [ "$size" -gt 0 ]; then
            echo -e "${GREEN}✓${NC} $label ($path)"
            PASS=$((PASS + 1))
        else
            echo -e "${RED}✗${NC} $label ($path) — 文件为空"
            FAIL=$((FAIL + 1))
        fi
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗${NC} $label ($path) — 缺失"
            FAIL=$((FAIL + 1))
        else
            echo -e "${YELLOW}⚠${NC} $label ($path) — 可选，未找到"
            WARN=$((WARN + 1))
        fi
    fi
}

check_dir() {
    local label="$1"
    local path="$2"
    local required="${3:-true}"

    if [ -d "$path" ]; then
        echo -e "${GREEN}✓${NC} $label ($path/)"
        PASS=$((PASS + 1))
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗${NC} $label ($path/) — 目录缺失"
            FAIL=$((FAIL + 1))
        else
            echo -e "${YELLOW}⚠${NC} $label ($path/) — 可选，未找到"
            WARN=$((WARN + 1))
        fi
    fi
}

check_frontmatter_field() {
    local label="$1"
    local file="$2"
    local field="$3"
    local required="${4:-true}"

    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC} $label — 文件 $file 不存在"
        FAIL=$((FAIL + 1))
        return
    fi

    # Extract frontmatter (between --- markers)
    local in_fm=false
    local found=false
    while IFS= read -r line; do
        if [ "$line" = "---" ]; then
            if [ "$in_fm" = "true" ]; then
                break
            fi
            in_fm=true
            continue
        fi
        if [ "$in_fm" = "true" ]; then
            if [[ "$line" == "$field:"* ]]; then
                found=true
                break
            fi
        fi
    done < "$file"

    if [ "$found" = "true" ]; then
        echo -e "${GREEN}✓${NC} $label — $field 字段存在"
        PASS=$((PASS + 1))
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗${NC} $label — $field 字段缺失"
            FAIL=$((FAIL + 1))
        else
            echo -e "${YELLOW}⚠${NC} $label — $field 字段缺失（可选）"
            WARN=$((WARN + 1))
        fi
    fi
}

echo "========================================="
echo " Yang.skills 仓库结构完整性检查"
echo "========================================="
echo ""

# ── 根级必需文件 ──
echo "── 根级必需文件 ──"
check_file "主 SKILL.md" "SKILL.md"
check_file "test-prompts.json" "test-prompts.json" "false"

# ── 子 skill 目录 ──
echo ""
echo "── 子 Skill 目录 ──"
SKILLS=(yang-score yang-predict yang-polish yang-retro yang-bump)
for skill in "${SKILLS[@]}"; do
    check_dir "$skill" "skills/$skill"
    check_file "$skill/SKILL.md" "skills/$skill/SKILL.md"
done

# ── Frontmatter 必需字段 ──
echo ""
echo "── 根 SKILL.md Frontmatter ──"
check_frontmatter_field "根 SKILL.md" "SKILL.md" "name"
check_frontmatter_field "根 SKILL.md" "SKILL.md" "version"
check_frontmatter_field "根 SKILL.md" "SKILL.md" "description"
check_frontmatter_field "根 SKILL.md" "SKILL.md" "author"
check_frontmatter_field "根 SKILL.md" "SKILL.md" "test-prompts" "false"
check_frontmatter_field "根 SKILL.md" "SKILL.md" "has-examples" "false"
check_frontmatter_field "根 SKILL.md" "SKILL.md" "has-before-after" "false"

# ── 子 skill Frontmatter 必需字段 ──
echo ""
echo "── 子 Skill Frontmatter ──"
for skill in "${SKILLS[@]}"; do
    check_frontmatter_field "$skill" "skills/$skill/SKILL.md" "name"
    check_frontmatter_field "$skill" "skills/$skill/SKILL.md" "version"
    check_frontmatter_field "$skill" "skills/$skill/SKILL.md" "description"
    check_frontmatter_field "$skill" "skills/$skill/SKILL.md" "author"
done

# ── 共享协议目录 ──
echo ""
echo "── 共享资源 ──"
check_dir "shared-protocols" "shared-protocols"
check_file "blind-prediction-protocol" "shared-protocols/blind-prediction-protocol.md" "false"

# ── 脚本目录 ──
echo ""
echo "── 脚本 ──"
check_dir "scripts" "scripts"
check_file "check-health.sh" "scripts/check-health.sh" "false"

# ── 结果汇总 ──
echo ""
echo "========================================="
echo -e " 结果: ${GREEN}$PASS 通过${NC} | ${RED}$FAIL 失败${NC} | ${YELLOW}$WARN 警告${NC}"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}检查未通过，请修复上述失败项。${NC}"
    exit 1
else
    echo -e "${GREEN}所有必需检查通过！${NC}"
    exit 0
fi
