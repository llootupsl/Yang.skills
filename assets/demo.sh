#!/usr/bin/env bash
# 作者: 阿洋
# Yang.skills Demo Recording Script
# Simulates the full workflow from yang-init to yang-retro
# Usage: bash assets/demo.sh
# Compatible with vhs (https://github.com/charmbracelet/vhs) or asciinema

set -uo pipefail

# ── Colors ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

step() {
  echo ""
  echo -e "${BOLD}${CYAN}━━━ Step $1: $2 ━━━${RESET}"
  echo ""
}

info() {
  echo -e "  ${GREEN}✅${RESET} $1"
}

warn() {
  echo -e "  ${YELLOW}⚠️${RESET}  $1"
}

output() {
  echo -e "  $1"
}

pause() {
  sleep "${1:-0.8}"
}

# ── Header ──
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║        Yang.skills · 内容创作运营系统 Demo       ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${DIM}选题 → 评分 → 润色 → 盲预测 → 发布 → 复盘 → 进化${RESET}"
echo ""

pause 1

# ── Step 1: yang-init ──
step 1 "yang-init — 初始化项目"

output "${DIM}\$ /yang-init \"AI工具评测\"${RESET}"
pause 0.5

echo ""
output "${BOLD}🔍 环境检测${RESET}"
info "Python: 3.12.3"
info "虚拟环境: .venv 已激活"
pause 0.3

echo ""
output "${BOLD}📦 安装依赖 (tier=core)${RESET}"
info "pip install -r requirements-core.txt"
pause 0.3

echo ""
output "${BOLD}📊 数据湖初始化${RESET}"
info "project_data.db 已创建，11 张表就绪"
pause 0.3

echo ""
output "${BOLD}📋 用户信息采集${RESET}"
output "  平台: 抖音"
output "  垂直领域: AI工具评测"
output "  粉丝数: ~2000"
pause 0.3

echo ""
output "${BOLD}🧑 创作人设档案${RESET}"
output "  身份: 做了三年AI内容的创业者"
output "  核心价值观: 技术应该让人更有创造力"
output "  口癖: 讲真、真的、你敢信"
pause 0.5

echo ""
info "Yang.skills 已初始化"
output "  📁 项目目录: /Users/demo/my-content"
output "  📏 Rubric: opinion-video-fusion-zero"
output "  📱 平台: 抖音"
output "  🧑 创作人设：已建立"

pause 1

# ── Step 2: yang-seed ──
step 2 "yang-seed — 四通道选题"

output "${DIM}\$ 找选题${RESET}"
pause 0.5

echo ""
output "${BOLD}🌱 四通道选题启动${RESET}"
pause 0.3

output "  Channel A: Rubric导向 → 逆推 5 个高分选题方向"
output "  Channel B: 对标拉升 → ⚠️ 尚未发现对标账号，降级跳过"
output "  Channel C: 热点冲浪 → 获取热点 3 条，筛选相关 2 条"
output "  Channel D: 高赞评论 → ⚠️ 无评论数据，降级跳过"
pause 0.3

echo ""
output "${BOLD}🎯 本期推荐选题（Top 4）:${RESET}"
output "  1. 淘宝9块9的AI工具安装服务，到底在卖什么？ · 🅰"
output "  2. 用AI给简历"投毒"之后，我发现招聘系统是黑暗森林 · 🅱"
output "  3. 为什么你用AI写的东西总有一股"AI味"？ · 🅱"
output "  4. 5个免费AI工具帮你每天省3小时 · 🅲"
pause 0.3

echo ""
output "${DIM}  → 选第1个${RESET}"

pause 1

# ── Step 3: yang-score ──
step 3 "yang-score — 7维度评分"

output "${DIM}\$ 打分这篇 scripts/2025-06-10_taobao-ai-install.md${RESET}"
pause 0.5

echo ""
output "${BOLD}📊 Yang.skills 评分 · v4 3-Judge${RESET}"
echo ""
output "  ┌──────────┬──────┬──────┬──────┬──────┬──────────┐"
output "  │ 维度     │ 得分 │ 满分 │ 权重 │ 加权 │ 置信度   │"
output "  ├──────────┼──────┼──────┼──────┼──────┼──────────┤"
output "  │ 钩子力   │  4   │  5   │ 0.25 │ 1.00 │ high     │"
output "  │ 情绪力   │  4   │  5   │ 0.15 │ 0.60 │ high     │"
output "  │ 结构力   │  4   │  5   │ 0.15 │ 0.60 │ high     │"
output "  │ 文案力   │  5   │  5   │ 0.15 │ 0.75 │ high     │"
output "  │ 人设力   │  4   │  5   │ 0.10 │ 0.40 │ medium   │"
output "  │ 传播力   │  4   │  5   │ 0.10 │ 0.40 │ medium   │"
output "  │ 节奏力   │  3   │  5   │ 0.10 │ 0.30 │ low      │"
output "  ├──────────┼──────┼──────┼──────┼──────┼──────────┤"
output "  │ 总分     │      │      │      │4.05  │ /10.0    │"
output "  └──────────┴──────┴──────┴──────┴──────┴──────────┘"
echo ""
output "  Agreement Score: 0.86"
output "  等级: 🟡 良好"
pause 0.3

echo ""
output "${BOLD}改进建议:${RESET}"
output "  1. 节奏力 3分 → 中段转场偏突兀，建议增加扣主线句"
output "  2. 人设力 4分 → 可在结尾增加口癖强化人设戳点"

pause 1

# ── Step 4: yang-polish ──
step 4 "yang-polish — 活人感润色"

output "${DIM}\$ 润色 scripts/2025-06-10_taobao-ai-install.md${RESET}"
pause 0.5

echo ""
output "${BOLD}🖊️ 润色分析${RESET}"
output "  判定: 标准润色（L1+L2+L3）"
output "  L1：硬性规则检查（禁用词/标点/套话扫描）"
output "  L2：风格一致性（口语化节奏/论述打破/标点情绪化）"
output "  L3：内容质量（观点支撑/知识输出/文化升维）"
pause 0.3

echo ""
output "${BOLD}改动清单:${RESET}"
output "  1. [中段转场] 增加扣主线句过渡 → 节奏力预期 +1"
output "  2. [结尾] 注入口癖"讲真" → 人设力预期 +1"
output "  3. [情绪标点] "9块9？" → "9块9？？？" → 情绪具象化"
pause 0.3

echo ""
info "润色完成"
output "  L1 硬性规则：通过 7/7"
output "  L2 风格一致性：通过 12/15，修复 3 项"
output "  L3 内容质量：通过 8/8"

pause 1

# ── Step 5: yang-score (二次验证) ──
step 5 "yang-score — 二次验证"

output "${DIM}\$ 打分这篇 scripts/2025-06-10_taobao-ai-install.md${RESET}"
pause 0.5

echo ""
output "${BOLD}📊 二次评分结果${RESET}"
echo ""
output "  节奏力: 3 → ${GREEN}4${RESET}  (+1 ✅)"
output "  人设力: 4 → ${GREEN}5${RESET}  (+1 ✅)"
output "  总分:   4.05 → ${GREEN}4.25${RESET}"
echo ""
info "润色后节奏力 +1、人设力 +1，提分有效"

pause 1

# ── Step 6: yang-predict ──
step 6 "yang-predict — 盲预测"

output "${DIM}\$ 预测这条 scripts/2025-06-10_taobao-ai-install.md${RESET}"
pause 0.5

echo ""
output "${BOLD}🔒 盲预测协议生效${RESET}"
output "  1. 必须在看到任何实际数据之前完成预测"
output "  2. 一旦写入，"## 预测" 段永久不可修改"
output "  3. 复盘时只能追加 "## 复盘" 段"
pause 0.3

echo ""
output "${BOLD}📝 预测结果${RESET}"
echo ""
output "  ┌──────────┬──────────┬───────────────────┬──────────┐"
output "  │ 维度     │ 预测值   │ 置信区间          │ 置信度   │"
output "  ├──────────┼──────────┼───────────────────┼──────────┤"
output "  │ 播放量   │ 8,000    │ [4,800 - 11,200]  │ low      │"
output "  │ 点赞率   │ 4.5%     │ [2.7% - 6.3%]     │ low      │"
output "  │ 评论率   │ 0.8%     │ [0.5% - 1.1%]     │ low      │"
output "  │ 分享率   │ 1.2%     │ [0.7% - 1.7%]     │ low      │"
output "  │ 完播率   │ 38%      │ [23% - 53%]       │ low      │"
output "  │ 涨粉预估 │ 45       │ [27 - 63]         │ low      │"
output "  └──────────┴──────────┴───────────────────┴──────────┘"
echo ""
warn "calibration_samples = 0，标注 [低置信度]"

pause 1

# ── Step 7: yang-publish ──
step 7 "yang-publish — 发布登记"

output "${DIM}\$ 发布 scripts/2025-06-10_taobao-ai-install.md${RESET}"
pause 0.5

echo ""
info "发布元数据已登记"
output "  标题: 淘宝上卖9块9的AI工具安装服务，到底在卖什么？"
output "  平台: 抖音"
output "  发布时间: 2025-06-10T20:00:00+08:00"
echo ""
output "  ⏰ 建议在 T+3d（2025-06-13）后运行 yang-retro 进行复盘"

pause 1

# ── Step 8: yang-retro ──
step 8 "yang-retro — 数据回收与复盘 (T+3d)"

output "${DIM}\$ 复盘 predictions/2025-06-10_001_taobao-ai-install.md${RESET}"
pause 0.5

echo ""
output "${BOLD}🔄 复盘 · 2025-06-13${RESET}"
echo ""
output "  ┌──────────┬──────────┬──────────┬────────┬──────────────┐"
output "  │ 指标     │ 预测     │ 实际     │ 偏差   │ 在置信区间？ │"
output "  ├──────────┼──────────┼──────────┼────────┼──────────────┤"
output "  │ 播放量   │ 8,000    │ 12,500   │ +56%   │ ❌ 超出上限  │"
output "  │ 点赞率   │ 4.5%     │ 5.44%    │ +21%   │ ✅           │"
output "  │ 评论率   │ 0.8%     │ 1.16%    │ +45%   │ ❌ 超出上限  │"
output "  │ 分享率   │ 1.2%     │ 1.68%    │ +40%   │ ❌ 超出上限  │"
output "  │ 完播率   │ 38%      │ 35%      │ -8%    │ ✅           │"
output "  │ 涨粉     │ 45       │ 72       │ +60%   │ ❌ 超出上限  │"
output "  └──────────┴──────────┴──────────┴────────┴──────────────┘"
pause 0.3

echo ""
output "${BOLD}关键发现:${RESET}"
output "  1. 信息差类选题的传播力被系统性低估"
output "  2. rubric 传播力维度需增加"信息差强度"子因子"
output "  3. 完播率略低于预期，中段转场仍可优化"
pause 0.3

echo ""
output "${BOLD}本轮得分:${RESET}"
output "  预测准确度: 4/10"
output "  校准进度: calibration_samples +1 = 1"

pause 1

# ── Summary ──
echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "${BOLD}  ✅ 闭环已启动！${RESET}"
echo ""
echo -e "  ${GREEN}yang-init${RESET} → ${GREEN}yang-seed${RESET} → ${GREEN}yang-score${RESET} → ${GREEN}yang-polish${RESET} → ${GREEN}yang-predict${RESET} → ${GREEN}yang-publish${RESET} → ${GREEN}yang-retro${RESET}"
echo ""
echo -e "  校准样本: ${BOLD}1${RESET}"
echo -e "  下一步: 积累 10+ 校准样本后 → ${BOLD}/yang-bump${RESET}（升级 rubric）"
echo ""
echo -e "  ${DIM}选题 → 预测 → 发布 → 复盘 → 进化。每一轮都比上一轮准。${RESET}"
echo ""
