#!/usr/bin/env python3
# 作者: 阿洋
"""
bayesian_update.py — Bayesian posterior updater using Dirichlet-Multinomial model for Yang.skills v4.

Maintains a Dirichlet-Multinomial distribution over four playback-level buckets (A, B, C, D).
After each retrospective, updates the posterior by incrementing the alpha parameter for the
bucket that corresponds to the actual outcome.

Theory:
    Prior: P(B) ~ Dirichlet(alpha_A, alpha_B, alpha_C, alpha_D)
    Default alpha = [1.0, 1.0, 1.0, 1.0] (uniform prior)
    Update rule:
        - If video landed in bucket B_k:
          alpha_k += 1
    Posterior expectation: E[P(B_k)] = alpha_k / sum(alpha)

==========================================================================
输入/输出规范
==========================================================================

输入:
  --status          读取 .yang-state.json 中的 bayesian_alpha 字段，展示当前后验分布。
  --update          必须配合 --actual-bucket 使用，执行一次贝叶斯更新。
  --actual-bucket   实际落桶 (A/B/C/D)，更新时必填。
  --prediction-file 预测文件路径（可选），用于从文件中提取预测分布做对比。

输出:
  --status 模式:
    stdout: 各桶的后验期望概率（百分比）+ 累计更新次数
    格式: Bucket A: 15.2% | Bucket B: 38.1% | Bucket C: 31.4% | Bucket D: 15.3% | Updates: 42

  --update 模式:
    更新 .yang-state.json 中的 bayesian_alpha 字段
    stdout: 更新前后的分布对比
    格式: Updated: Bucket B alpha 12→13 | Posterior: A=14.3% B=37.1% C=30.0% D=18.6%

状态文件: .yang-state.json (项目根目录)
  存储格式: {"bayesian_alpha": [1.0, 1.0, 1.0, 1.0], "bayesian_updates": 0}

==========================================================================
先验分布选择指引
==========================================================================

1. 无信息先验 (Uniform): alpha = [1.0, 1.0, 1.0, 1.0]（默认）
   - 适用场景: 全新账号/新赛道，无历史数据参考。
   - 特点: 四桶等概率，完全由后续观测数据驱动。

2. 弱信息先验: alpha = [2.0, 3.0, 2.0, 1.0]
   - 适用场景: 有粗略行业基准（如多数视频落在B/C桶）。
   - 特点: 轻微偏向中间桶，但少量观测即可覆盖。

3. 经验先验: alpha 根据历史数据设定
   - 适用场景: 已有 50+ 条历史数据，可统计各桶频率作为先验。
   - 方法: alpha_k = 历史频率_k × 先验强度(建议5~10)
   - 注意: 先验强度越高，新数据对后验的影响越慢。

4. 切换先验的时机:
   - 累计更新 < 10 次: 使用无信息先验，避免先验偏见。
   - 累计更新 10~30 次: 可考虑弱信息先验。
   - 累计更新 > 30 次: 后验已充分收敛，先验选择影响可忽略。

==========================================================================
更新结果解读说明
==========================================================================

1. 后验期望 E[P(B_k)] = alpha_k / sum(alpha)
   - 含义: 给定当前观测，视频落在某桶的概率期望值。
   - 解读: 概率最高的桶为"最可能落桶"，但需关注置信区间。

2. 置信度评估:
   - sum(alpha) < 10: 低置信度，分布仍大幅波动，不宜做强决策。
   - 10 ≤ sum(alpha) < 30: 中等置信度，趋势已显现，可做方向性判断。
   - sum(alpha) ≥ 30: 高置信度，分布趋于稳定，可作为评分校准依据。

3. 分布偏移信号:
   - 某桶概率连续3次更新上升: 该桶可能被低估，评分标准偏严。
   - 某桶概率连续3次更新下降: 该桶可能被高估，评分标准偏松。
   - A/D桶概率之和 > 50%: 分布两极化，评分标准可能需要细分。

4. 与预测对比:
   - 若后验期望与预测分布偏差 > 15%: 评分体系需要校准。
   - 若后验期望与预测分布偏差 < 5%: 评分体系校准良好。

Usage:
    python tools/bayesian_update.py --status
    python tools/bayesian_update.py --update --actual-bucket B --prediction-file predictions/2026-05-15_001.md
==========================================================================
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
STATE_FILE = PROJECT_DIR / ".yang-state.json"

BUCKETS = ["A", "B", "C", "D"]

DEFAULT_DIRICHLET_ALPHA = [1.0, 1.0, 1.0, 1.0]

BUCKET_LABEL_PATTERN = re.compile(
    r"(?:Bucket|档次|区间)[：:\s]*[`]*([ABCD])[`]*",
    re.IGNORECASE,
)

BUCKET_DIST_PATTERN = re.compile(
    r"([ABCD])\s*[:：]\s*(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


def load_state() -> Optional[dict]:
    """Load .yang-state.json. Return dict or None."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as e:
        print(f"error: 无法读取 {STATE_FILE}: {e}", file=sys.stderr)
        return None


def save_state(state: dict):
    """Atomically save state (write to .tmp, then rename)."""
    tmp_path = STATE_FILE.with_suffix(STATE_FILE.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, STATE_FILE)
    except OSError as e:
        print(f"error: 无法写入 {STATE_FILE}: {e}", file=sys.stderr)
        raise


def _migrate_legacy_state(state: dict) -> dict:
    """Detect and migrate legacy Beta-Binomial bucket_params to Dirichlet-Multinomial dirichlet_alpha."""
    if "dirichlet_alpha" in state:
        return state

    bp = state.get("bucket_params")
    if bp is None:
        return state

    if not isinstance(bp, dict):
        return state

    alphas = []
    for b in BUCKETS:
        entry = bp.get(b, {})
        if isinstance(entry, dict) and "alpha" in entry:
            alphas.append(float(entry["alpha"]))
        else:
            alphas.append(1.0)

    state["dirichlet_alpha"] = alphas
    print(
        f"info: 检测到旧格式 bucket_params，已自动迁移为 dirichlet_alpha: {alphas}",
        file=sys.stderr,
    )
    return state


def _extract_predicted_distribution(prediction_text: str) -> Optional[dict[str, float]]:
    """Extract predicted bucket probability distribution from a prediction file.

    Returns dict like {"A": 0.25, "B": 0.40, "C": 0.25, "D": 0.10} or None.
    """
    dist: dict[str, float] = {}
    for match in BUCKET_DIST_PATTERN.finditer(prediction_text):
        bucket = match.group(1).upper()
        pct = float(match.group(2))
        dist[bucket] = pct / 100.0

    if len(dist) >= 2:
        total = sum(dist.values())
        if total > 0:
            return {k: v / total for k, v in dist.items()}

    bucket_match = BUCKET_LABEL_PATTERN.search(prediction_text)
    if bucket_match:
        primary = bucket_match.group(1).upper()
        result = {"A": 0.1, "B": 0.1, "C": 0.1, "D": 0.1}
        result[primary] = 0.7
        return result

    return None


def update(actual_bucket: str, prediction_file: str):
    """Update dirichlet_alpha after retro.

    Dirichlet-Multinomial update:
        - If video landed in bucket B_k:
          alpha_k += 1
    """
    actual_bucket = actual_bucket.upper()
    if actual_bucket not in BUCKETS:
        print(f"error: 无效的 bucket: {actual_bucket}，应为 A/B/C/D", file=sys.stderr)
        sys.exit(1)

    pred_path = Path(prediction_file)
    if not pred_path.is_file():
        print(f"error: 预测文件不存在: {prediction_file}", file=sys.stderr)
        sys.exit(1)

    try:
        pred_text = pred_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: 无法读取预测文件: {e}", file=sys.stderr)
        sys.exit(1)

    pred_dist = _extract_predicted_distribution(pred_text)
    if pred_dist:
        pred_primary = max(pred_dist, key=lambda k: pred_dist.get(k, 0))
        print(
            f"预测分布: "
            + " | ".join(
                f"{b}: {pred_dist.get(b, 0)*100:.0f}%"
                for b in BUCKETS
            ),
            file=sys.stderr,
        )
        print(f"预测主区间: {pred_primary}，实际区间: {actual_bucket}", file=sys.stderr)

    state = load_state()
    if state is None:
        state = {
            "dirichlet_alpha": list(DEFAULT_DIRICHLET_ALPHA),
            "calibration_samples": 0,
            "bayesian_last_updated": None,
        }

    state = _migrate_legacy_state(state)

    da = state.setdefault("dirichlet_alpha", list(DEFAULT_DIRICHLET_ALPHA))
    k = BUCKETS.index(actual_bucket)
    da[k] += 1

    old_count = state.get("calibration_samples", 0)
    state["calibration_samples"] = old_count + 1
    state["bayesian_last_updated"] = datetime.now(timezone.utc).isoformat()

    save_state(state)

    total_alpha = sum(da)

    print(f"\n更新完成 (样本 #{state['calibration_samples']})", file=sys.stderr)
    print(f"实际区间: {actual_bucket}", file=sys.stderr)
    print(f"{'Bucket':<8} {'Alpha':<8} {'期望概率':<12} {'变化':<8}")
    print("-" * 40)

    for i, b in enumerate(BUCKETS):
        alpha = da[i]
        expected = alpha / total_alpha
        change = "↑ alpha" if b == actual_bucket else "—"
        print(
            f"{b:<8} {alpha:<8.1f} "
            f"{expected:<12.4f} {change:<8}"
        )


def status():
    """Print current Dirichlet-Multinomial distribution and calibration statistics."""
    state = load_state()
    if state is None:
        print("错误: .yang-state.json 不存在")
        print("请先运行 --update 进行一次校准更新来初始化状态文件")
        return

    state = _migrate_legacy_state(state)

    da = state.get("dirichlet_alpha", list(DEFAULT_DIRICHLET_ALPHA))
    cs = state.get("calibration_samples", 0)
    last_updated = state.get("bayesian_last_updated", "从未更新")

    total_alpha = sum(da)

    print(f"Dirichlet-Multinomial 状态")
    print(f"校准样本数:  {cs}")
    print(f"最后更新:    {last_updated}")
    print(f"总 Alpha:     {total_alpha:.1f}")
    print()
    print(f"{'Bucket':<8} {'Alpha':<8} {'期望概率':<12}")
    print("-" * 30)

    expected_sum = 0.0
    for i, b in enumerate(BUCKETS):
        alpha = da[i]
        expected = alpha / total_alpha
        expected_sum += expected
        print(
            f"{b:<8} {alpha:<8.1f} "
            f"{expected:<12.4f}"
        )

    print("-" * 30)
    print(f"{'合计':<8} {'':<8} {expected_sum:<12.4f}")

    print()
    print("解读: 期望概率 = alpha[k] / sum(alpha)，总和必为 1.0")
    print("      alpha ↑ → 该区间出现的置信度增强")
    print("      每次更新只增加对应 bucket 的 alpha，不影响其他 bucket")


def main():
    parser = argparse.ArgumentParser(
        description="Bayesian Posterior Updater for Yang.skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="执行贝叶斯后验更新",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="打印当前先验分布",
    )
    parser.add_argument(
        "--actual-bucket",
        type=str,
        choices=["A", "B", "C", "D"],
        help="视频实际播放量区间",
    )
    parser.add_argument(
        "--prediction-file",
        type=str,
        help="预测文件路径（用于提取预测分布）",
    )

    args = parser.parse_args()

    if args.update:
        if not args.actual_bucket or not args.prediction_file:
            print(
                "错误: --update 需要 --actual-bucket 和 --prediction-file",
                file=sys.stderr,
            )
            parser.print_help()
            sys.exit(1)
        update(args.actual_bucket, args.prediction_file)
    elif args.status:
        status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()