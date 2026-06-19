#!/bin/bash
# 作者: 阿洋
# 会话启动钩子：检查环境状态、更新看板
# 触发：on_session_start

STATE_FILE="${1:-.yang-state.json}"
RUBRIC_FILE="${2:-rubric_notes.md}"

echo "─────────────────────────────────────"
echo "  Yang.skills · 会话启动检查"
echo "─────────────────────────────────────"

if [ -f "$STATE_FILE" ]; then
  python3 -c "
import json
import sys
try:
    with open('$STATE_FILE') as f:
        d = json.load(f)
    total_predictions = d.get('total_predictions', 0)
    total_published = d.get('total_published', 0)
    pending_retros = d.get('pending_retros', [])
    pending_count = len(pending_retros) if isinstance(pending_retros, list) else 0
    rubric_bumps = d.get('rubric_bumps', 0)
    calibration_samples = d.get('calibration_samples', 0)
    print(f'  📊 总预测: {total_predictions} | 已发布: {total_published} | 待复盘: {pending_count}')
    print(f'  🔧 Rubric bumps: {rubric_bumps} | 校准样本: {calibration_samples}')
except Exception as e:
    print(f'  ⚠️ 状态文件读取失败: {e}', file=sys.stderr)
"
else
  echo "  ⚠️ 项目未初始化，运行 '初始化' 开始"
fi

echo "─────────────────────────────────────"