#!/usr/bin/env bash
# 作者: 阿洋
# check-health.sh — Yang.skills 系统健康检查脚本
# 检查 .yang-state.json、rubric_notes.md、predictions/ 等核心文件是否存在且有效
# 用法: bash scripts/check-health.sh [项目目录]

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 项目目录（默认当前目录）
PROJECT_DIR="${1:-.}"

# 计数器
PASS=0
FAIL=0
WARN=0

check_file() {
    local label="$1"
    local path="$2"
    local required="${3:-true}"  # true=必须存在, false=可选

    if [ -f "$path" ]; then
        local size
        size=$(wc -c < "$path")
        if [ "$size" -gt 0 ]; then
            echo -e "  ${GREEN}✅${NC} $label ($path, ${size} bytes)"
            PASS=$((PASS + 1))
        else
            echo -e "  ${RED}❌${NC} $label ($path, 文件为空)"
            FAIL=$((FAIL + 1))
        fi
    else
        if [ "$required" = "true" ]; then
            echo -e "  ${RED}❌${NC} $label ($path, 不存在)"
            FAIL=$((FAIL + 1))
        else
            echo -e "  ${YELLOW}⚠️${NC} $label ($path, 不存在[可选])"
            WARN=$((WARN + 1))
        fi
    fi
}

check_dir() {
    local label="$1"
    local path="$2"
    local required="${3:-true}"

    if [ -d "$path" ]; then
        local count
        count=$(find "$path" -maxdepth 1 -type f | wc -l)
        echo -e "  ${GREEN}✅${NC} $label ($path, ${count} 个文件)"
        PASS=$((PASS + 1))
    else
        if [ "$required" = "true" ]; then
            echo -e "  ${RED}❌${NC} $label ($path, 不存在)"
            FAIL=$((FAIL + 1))
        else
            echo -e "  ${YELLOW}⚠️${NC} $label ($path, 不存在[可选])"
            WARN=$((WARN + 1))
        fi
    fi
}

check_json_field() {
    local label="$1"
    local path="$2"
    local field="$3"
    local expected="$4"

    if [ ! -f "$path" ]; then
        return
    fi

    local value
    value=$(python3 -c "import json; d=json.load(open('$path')); print(d.get('$field', 'NOT_FOUND'))" 2>/dev/null || echo "PARSE_ERROR")

    if [ "$value" = "$expected" ]; then
        echo -e "  ${GREEN}✅${NC} $label: $value"
        PASS=$((PASS + 1))
    elif [ "$value" = "NOT_FOUND" ] || [ "$value" = "PARSE_ERROR" ]; then
        echo -e "  ${RED}❌${NC} $label: 读取失败 ($value)"
        FAIL=$((FAIL + 1))
    else
        echo -e "  ${YELLOW}⚠️${NC} $label: $value (期望: $expected)"
        WARN=$((WARN + 1))
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏥 Yang.skills 系统健康检查"
echo "📁 项目目录: $PROJECT_DIR"
echo "🕐 检查时间: $(date -Iseconds)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. 核心状态文件 ──
echo "📋 核心状态文件"
check_file ".yang-state.json" "$PROJECT_DIR/.yang-state.json" true
check_file "rubric_notes.md" "$PROJECT_DIR/rubric_notes.md" true
check_file "WORKFLOW.md" "$PROJECT_DIR/WORKFLOW.md" true
check_file "STATUS.md" "$PROJECT_DIR/STATUS.md" true
check_file "candidates.md" "$PROJECT_DIR/candidates.md" true
check_file "benchmark.md" "$PROJECT_DIR/benchmark.md" false
echo ""

# ── 2. 状态文件关键字段 ──
echo "🔍 状态文件关键字段"
check_json_field "schema_version" "$PROJECT_DIR/.yang-state.json" "schema_version" "v2.1"
check_json_field "rubric_version" "$PROJECT_DIR/.yang-state.json" "rubric_version" "v0"
echo ""

# ── 3. 目录结构 ──
echo "📂 目录结构"
check_dir "scripts/" "$PROJECT_DIR/scripts" true
check_dir "predictions/" "$PROJECT_DIR/predictions" true
check_dir "videos/" "$PROJECT_DIR/videos" true
check_dir "samples/" "$PROJECT_DIR/samples" false
check_dir "videos/benchmark/" "$PROJECT_DIR/videos/benchmark" false
echo ""

# ── 4. 人设档案 ──
echo "👤 人设档案"
check_file ".yang-persona.md" "$PROJECT_DIR/.yang-persona.md" false
if [ -f "$PROJECT_DIR/.yang-state.json" ]; then
    persona_exists=$(python3 -c "import json; d=json.load(open('$PROJECT_DIR/.yang-state.json')); print(d.get('persona_exists', False))" 2>/dev/null || echo "false")
    persona_file_exists="false"
    [ -f "$PROJECT_DIR/.yang-persona.md" ] && persona_file_exists="true"
    if [ "$persona_exists" = "$persona_file_exists" ]; then
        echo -e "  ${GREEN}✅${NC} 人设状态一致性 (state: $persona_exists, file: $persona_file_exists)"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌${NC} 人设状态不一致 (state: $persona_exists, file: $persona_file_exists)"
        FAIL=$((FAIL + 1))
    fi
fi
echo ""

# ── 5. Hook 安装 ──
echo "🪝 Hook 安装状态"
check_dir ".claude/hooks/" "$PROJECT_DIR/.claude/hooks" false
check_file ".claude/settings.json" "$PROJECT_DIR/.claude/settings.json" false
if [ -d "$PROJECT_DIR/.claude/hooks" ]; then
    for hook in prediction-immutability.sh session-start.sh log-event.sh bump-trigger-monitor.sh; do
        check_file "hook: $hook" "$PROJECT_DIR/.claude/hooks/$hook" false
    done
fi
echo ""

# ── 6. 数据库 ──
echo "🗄️ 数据库"
check_file "project_data.db" "$PROJECT_DIR/project_data.db" false
if [ -f "$PROJECT_DIR/project_data.db" ]; then
    table_count=$(sqlite3 "$PROJECT_DIR/project_data.db" ".tables" 2>/dev/null | wc -w || echo "0")
    if [ "$table_count" -ge 11 ]; then
        echo -e "  ${GREEN}✅${NC} 数据库表数量: $table_count (≥11)"
        PASS=$((PASS + 1))
    else
        echo -e "  ${YELLOW}⚠️${NC} 数据库表数量: $table_count (<11，可能初始化不完整)"
        WARN=$((WARN + 1))
    fi
fi
echo ""

# ── 7. 校准状态 ──
echo "📊 校准状态"
if [ -f "$PROJECT_DIR/.yang-state.json" ]; then
    cal_samples=$(python3 -c "import json; d=json.load(open('$PROJECT_DIR/.yang-state.json')); print(d.get('calibration_samples', 0))" 2>/dev/null || echo "0")
    pending_retros=$(python3 -c "import json; d=json.load(open('$PROJECT_DIR/.yang-state.json')); print(len(d.get('pending_retros', [])))" 2>/dev/null || echo "0")

    echo -e "  ℹ️  校准样本数: $cal_samples"
    echo -e "  ℹ️  待复盘数: $pending_retros"

    if [ "$cal_samples" -ge 10 ]; then
        echo -e "  ${GREEN}✅${NC} 校准就绪 (≥10 样本，可执行 yang-bump)"
        PASS=$((PASS + 1))
    elif [ "$cal_samples" -ge 5 ]; then
        echo -e "  ${YELLOW}⚠️${NC} 校准进行中 ($cal_samples/10 样本)"
        WARN=$((WARN + 1))
    else
        echo -e "  ${YELLOW}⚠️${NC} 校准不足 ($cal_samples/10 样本，需继续积累)"
        WARN=$((WARN + 1))
    fi

    if [ "$pending_retros" -gt 0 ]; then
        echo -e "  ${YELLOW}⚠️${NC} 有 $pending_retros 条待复盘内容，建议尽快运行 yang-retro"
        WARN=$((WARN + 1))
    fi
fi
echo ""

# ── 8. 预测文件完整性 ──
echo "📝 预测文件完整性"
if [ -d "$PROJECT_DIR/predictions" ]; then
    pred_count=$(find "$PROJECT_DIR/predictions" -maxdepth 1 -name "*.md" -type f | wc -l)
    echo -e "  ℹ️  预测文件数: $pred_count"
    PASS=$((PASS + 1))

    # 检查是否有预测文件缺少 ## 预测 段
    broken=0
    for f in "$PROJECT_DIR/predictions"/*.md; do
        [ -f "$f" ] || continue
        if ! grep -q "## 预测" "$f" 2>/dev/null; then
            echo -e "  ${RED}❌${NC} 预测文件缺少 ## 预测 段: $(basename "$f")"
            broken=$((broken + 1))
        fi
    done
    if [ "$broken" -eq 0 ]; then
        echo -e "  ${GREEN}✅${NC} 所有预测文件包含 ## 预测 段"
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + broken))
    fi
else
    echo -e "  ℹ️  predictions/ 目录不存在（尚未进行预测）"
fi
echo ""

# ── 9. 模板残留检查 ──
echo "🔧 模板变量残留检查"
if [ -f "$PROJECT_DIR/rubric_notes.md" ]; then
    placeholder_count=$(grep -c '$$' "$PROJECT_DIR/rubric_notes.md" 2>/dev/null || echo "0")
    if [ "$placeholder_count" -eq 0 ]; then
        echo -e "  ${GREEN}✅${NC} rubric_notes.md 无模板占位符残留"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌${NC} rubric_notes.md 有 $placeholder_count 处模板占位符残留"
        FAIL=$((FAIL + 1))
    fi
fi
echo ""

# ── 汇总 ──
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏥 健康检查汇总"
echo -e "  ${GREEN}✅ 通过: $PASS${NC}"
echo -e "  ${RED}❌ 失败: $FAIL${NC}"
echo -e "  ${YELLOW}⚠️ 警告: $WARN${NC}"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}🎉 系统健康！所有必要检查项均通过。${NC}"
    if [ "$WARN" -gt 0 ]; then
        echo -e "${YELLOW}💡 有 $WARN 个警告项，建议检查但不影响核心功能。${NC}"
    fi
    exit 0
else
    echo -e "${RED}🚨 系统存在 $FAIL 个问题，请修复后重新检查。${NC}"
    echo ""
    echo "修复建议:"
    echo "  - 缺少核心文件 → 运行 yang-init 重新初始化"
    echo "  - 模板占位符残留 → 检查 yang-init 是否正确替换了变量"
    echo "  - 人设状态不一致 → 检查 .yang-state.json 和 .yang-persona.md"
    exit 1
fi
