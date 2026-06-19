#!/bin/bash
# 作者: 阿洋
# Bump触发监控：每次复盘完成后检查校准池是否达到Bump阈值
# 触发：on_retro_complete

STATE_FILE="${1:-.yang-state.json}"

if [ ! -f "$STATE_FILE" ]; then
  echo "[bump-trigger-monitor] State file not found: $STATE_FILE"
  exit 1
fi

calibration_samples=$(python3 -c "
import json
try:
    with open('$STATE_FILE') as f:
        d = json.load(f)
    if isinstance(d, dict):
        calibration_samples = d.get('calibration_samples', d.get('stats', {}).get('calibration_samples', 0))
    else:
        calibration_samples = 0
    print(calibration_samples)
except Exception as e:
    print(0)
" 2>/dev/null || echo 0)

MIN_SAMPLES=10

echo "[bump-trigger-monitor] Calibration samples: $calibration_samples / min $MIN_SAMPLES"

if [ "$calibration_samples" -ge "$MIN_SAMPLES" ]; then
  echo "  ✅ Bump 可用！校准池有 $calibration_samples 条样本（≥$MIN_SAMPLES）"
  echo "  建议用户执行 '升级 rubric' 触发 Bump"
else
  remaining=$((MIN_SAMPLES - calibration_samples))
  echo "  ⏳ Bump 不可用，还需要 $remaining 条样本"
fi