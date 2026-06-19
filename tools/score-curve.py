#!/usr/bin/env python3
# 作者: 阿洋
"""
score-curve.py — predict accuracy convergence chart for Yang.skills.

Reads predictions/*.md (in the user's project), pairs each prediction's
center-of-bucket estimate against actual plays from the retrospective section,
and plots rolling-mean prediction error over time. The chart shows whether the
rubric is calibrating (error narrows) or drifting (error widens).

==========================================================================
收敛曲线判定标准
==========================================================================

什么算"收敛"：
  1. 滚动平均误差连续 5 个样本单调递减（或持平），且最终误差 ≤ 初始误差的 50%。
  2. 最近 10 个样本的误差标准差 < 初始 10 个样本标准差的 30%。
  3. 滚动平均误差曲线斜率趋近于 0（|slope| < 0.5万/样本）。

收敛等级：
  - 强收敛: 同时满足以上3条 → 评分体系校准良好，可信赖预测结果。
  - 弱收敛: 满足1~2条 → 评分体系有改善趋势，但仍需观察。
  - 未收敛: 均不满足 → 评分体系需要调整，预测结果参考价值有限。
  - 样本不足: 总样本 < 10 → 无法判定收敛性，需积累更多数据。

==========================================================================
曲线异常识别规则
==========================================================================

1. 误差突增（单点异常）:
   - 判定: 单个样本误差 > 滚动平均误差的 3 倍。
   - 可能原因: 预测文件中桶区间选择错误、实际播放数据异常（如被推荐）、
     回溯数据录入错误。
   - 处理: 检查该样本的预测文件和回溯数据，确认无误后可标记为异常点排除。

2. 持续发散（趋势异常）:
   - 判定: 滚动平均误差连续 5 个样本递增。
   - 可能原因: 平台算法变更导致播放量分布偏移、评分标准过时、
     新赛道/新账号类型与历史数据不匹配。
   - 处理: 检查近期是否有平台规则变更，考虑重置贝叶斯先验重新校准。

3. 震荡不收敛（波动异常）:
   - 判定: 误差在高位反复波动，最近 20 个样本的标准差 > 均值的 50%。
   - 可能原因: 评分标准过于粗粒度（桶区间太宽）、预测与实际系统性错配。
   - 处理: 考虑细分桶区间，或检查预测方法是否存在系统性偏差。

4. 数据缺失（断点异常）:
   - 判定: 时间轴上出现 > 7 天的间隔。
   - 可能原因: 未持续做回溯更新。
   - 处理: 补充缺失期间的回溯数据，断点前后分别评估收敛性。

==========================================================================
输出图表解读指引
==========================================================================

图表结构:
  - X轴: 样本序号（按时间排列，从早到晚）
  - Y轴: 预测误差（万播放量），即 |预测中枢 - 实际播放|
  - 主线: 滚动平均误差（默认窗口=5）
  - 散点: 各样本的原始误差
  - 参考线: 零误差线（理想目标）

如何读图:
  1. 曲线整体趋势:
     - 下行 → 评分体系在改善，预测越来越准。
     - 水平 → 评分体系稳定但未改善，可能已达当前粒度上限。
     - 上行 → 评分体系在恶化，需要调整评分标准。

  2. 散点分布:
     - 散点贴近主线 → 预测稳定性好。
     - 散点远离主线 → 预测波动大，可能存在异常样本。

  3. 曲线末端（最近5~10个样本）:
     - 末端收敛 → 当前评分体系可靠。
     - 末端发散 → 近期评分体系出现问题，需重点关注。

  4. 误差绝对值参考:
     - 误差 < 5万: 优秀（预测与实际高度吻合）
     - 误差 5~15万: 良好（在合理范围内）
     - 误差 15~30万: 一般（需要改善）
     - 误差 > 30万: 较差（评分体系需要重大调整）

==========================================================================
Usage:
    python tools/score-curve.py [--predictions DIR] [--out PATH] [--window N]

Defaults:
    --predictions  ./predictions
    --out          score-curve.png
    --window       5  (rolling-mean window in samples)

Dependencies: stdlib only for parsing; matplotlib for plotting (optional —
if absent, prints a CSV table to stdout instead).
==========================================================================
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Bucket center mapping (the "中枢" if the prediction file doesn't spell it out
# explicitly). Units: 万 (10,000 plays). Adjust per platform if needed.
BUCKET_CENTERS = {
    "<5w": 2.5,
    "5-30w": 17.5,
    "30-100w": 65.0,
    "100-150w": 125.0,
    ">150w": 200.0,
}

PREDICTION_HEADER_RE = re.compile(r"^\*\*Bucket\*\*:\s*`?([^`\n]+?)`?\s*$", re.MULTILINE)
CENTER_RE = re.compile(r"中枢\s*[~约]?\s*(\d+(?:\.\d+)?)\s*w", re.IGNORECASE)
ACTUAL_PLAYS_RE = re.compile(r"播放[：:]\s*\*?\*?(\d+(?:\.\d+)?)\s*w", re.IGNORECASE)
DATE_FROM_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_")


@dataclass
class Sample:
    file: Path
    date: datetime
    bucket: Optional[str]
    predicted_center_w: Optional[float]
    actual_plays_w: Optional[float]

    @property
    def has_retro(self) -> bool:
        return self.actual_plays_w is not None

    @property
    def signed_error_pct(self) -> Optional[float]:
        """(actual - predicted) / predicted, in percent."""
        if self.predicted_center_w is None or self.actual_plays_w is None or self.predicted_center_w == 0:
            return None
        return (self.actual_plays_w - self.predicted_center_w) / self.predicted_center_w * 100

    @property
    def abs_error_pct(self) -> Optional[float]:
        sep = self.signed_error_pct
        return abs(sep) if sep is not None else None


def parse_prediction_file(path: Path) -> Sample:
    text = path.read_text(encoding="utf-8")

    # Date from filename (YYYY-MM-DD_<id>_<short>.md)
    m = DATE_FROM_FILENAME_RE.search(path.name)
    if not m:
        raise ValueError(f"{path.name}: filename does not start with YYYY-MM-DD_")
    date = datetime.strptime(m.group(1), "%Y-%m-%d")

    # Split prediction vs retro section
    pred_section, _, retro_section = text.partition("## 复盘")

    # Bucket from prediction section
    bm = PREDICTION_HEADER_RE.search(pred_section)
    bucket = bm.group(1).strip() if bm else None

    # Predicted center: prefer explicit "中枢 ~50w", fall back to bucket midpoint
    cm = CENTER_RE.search(pred_section)
    if cm:
        predicted_center_w = float(cm.group(1))
    elif bucket and bucket in BUCKET_CENTERS:
        predicted_center_w = BUCKET_CENTERS[bucket]
    else:
        predicted_center_w = None

    # Actual plays from retro section
    actual_plays_w = None
    if retro_section.strip():
        am = ACTUAL_PLAYS_RE.search(retro_section)
        if am:
            actual_plays_w = float(am.group(1))

    return Sample(
        file=path,
        date=date,
        bucket=bucket,
        predicted_center_w=predicted_center_w,
        actual_plays_w=actual_plays_w,
    )


def collect_samples(predictions_dir: Path) -> list[Sample]:
    state_path = predictions_dir.parent / ".yang-state.json"
    if state_path.exists():
        try:
            import json
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            records = state.get("calibration_records", [])
            if len(records) >= 3:
                return _samples_from_calibration_records(records, predictions_dir)
        except Exception as e:
            print(f"info: calibration_records 读取失败，回退到 Markdown 解析: {e}", file=sys.stderr)

    samples: list[Sample] = []
    for path in sorted(predictions_dir.glob("*.md")):
        try:
            samples.append(parse_prediction_file(path))
        except (ValueError, OSError) as e:
            print(f"warn: skipping {path.name}: {e}", file=sys.stderr)
    return samples


def _samples_from_calibration_records(records: list[dict], predictions_dir: Path) -> list[Sample]:
    samples: list[Sample] = []
    for rec in records:
        try:
            date_str = rec.get("retro_at", "")[:10]
            if not date_str:
                continue
            date = datetime.strptime(date_str, "%Y-%m-%d")
            bucket = rec.get("predicted_bucket")
            pc = rec.get("predicted_composite")
            predicted_center_w = float(pc) if pc is not None else (BUCKET_CENTERS.get(bucket) if bucket else None)
            actual_plays_w = None
            ap = rec.get("actual_plays")
            if ap is not None:
                actual_plays_w = float(ap) / 10000.0
            vid = rec.get("video_id", "unknown")
            fake_path = predictions_dir / f"{date_str}_{vid}.md"
            samples.append(Sample(
                file=fake_path,
                date=date,
                bucket=bucket,
                predicted_center_w=predicted_center_w,
                actual_plays_w=actual_plays_w,
            ))
        except (ValueError, OSError, TypeError):
            continue
    print(f"info: 从 calibration_records 加载了 {len(samples)} 条结构化数据", file=sys.stderr)
    return samples


def rolling_mean(values: list[float], window: int) -> list[float]:
    if not values:
        return []
    out = []
    for i in range(len(values)):
        lo = max(0, i - window + 1)
        chunk = values[lo : i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def render_chart(samples: list[Sample], out_path: Path, window: int) -> bool:
    """Returns True on success, False if matplotlib is unavailable."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
    except ImportError:
        return False

    # Try to find a CJK-capable font so Chinese labels render. Falls back silently
    # to default if none available — labels will show as boxes but the chart still works.
    for cand in ("PingFang SC", "Heiti SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", "WenQuanYi Zen Hei"):
        try:
            if any(cand.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
                plt.rcParams["font.sans-serif"] = [cand] + plt.rcParams.get("font.sans-serif", [])
                plt.rcParams["axes.unicode_minus"] = False
                break
        except Exception:
            pass

    samples_with_retro = [s for s in samples if s.has_retro and s.abs_error_pct is not None]
    if not samples_with_retro:
        print("error: no samples with retro data — nothing to plot", file=sys.stderr)
        return True  # signal "we did our part"; nothing to plot is not a missing-deps issue

    samples_with_retro.sort(key=lambda s: s.date)
    abs_errors = [s.abs_error_pct for s in samples_with_retro]
    signed_errors = [s.signed_error_pct for s in samples_with_retro]
    rolling = rolling_mean(abs_errors, window)
    indices = list(range(1, len(samples_with_retro) + 1))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(indices, abs_errors, alpha=0.3, label=f"|误差%| 单篇", color="steelblue")
    ax.plot(indices, rolling, marker="o", linewidth=2, label=f"|误差%| 滚动 {window} 篇均值", color="firebrick")
    ax.axhline(50, linestyle="--", linewidth=1, color="gray", label="cold-start 期参考线 (±50%)")
    ax.axhline(25, linestyle=":", linewidth=1, color="green", label="校准成熟期目标 (±25%)")

    ax.set_xlabel("第 N 篇校准样本")
    ax.set_ylabel("|预测中枢偏差%|")
    ax.set_title("Yang.skills — 预测精度收敛曲线")
    ax.set_xticks(indices)
    ax.set_xticklabels([s.date.strftime("%m-%d") for s in samples_with_retro], rotation=45, ha="right")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return True


def render_csv(samples: list[Sample]) -> None:
    """Fallback when matplotlib is unavailable."""
    writer = csv.writer(sys.stdout)
    writer.writerow(["file", "date", "bucket", "predicted_center_w", "actual_plays_w", "signed_error_pct"])
    for s in sorted(samples, key=lambda x: x.date):
        writer.writerow(
            [
                s.file.name,
                s.date.date().isoformat(),
                s.bucket or "",
                s.predicted_center_w if s.predicted_center_w is not None else "",
                s.actual_plays_w if s.actual_plays_w is not None else "",
                f"{s.signed_error_pct:.1f}" if s.signed_error_pct is not None else "",
            ]
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--predictions", type=Path, default=Path("predictions"), help="prediction files directory")
    ap.add_argument("--out", type=Path, default=Path("score-curve.png"), help="output chart path")
    ap.add_argument("--window", type=int, default=5, help="rolling-mean window in samples")
    args = ap.parse_args()

    if not args.predictions.is_dir():
        print(f"error: {args.predictions} is not a directory", file=sys.stderr)
        return 2

    samples = collect_samples(args.predictions)
    if not samples:
        print(f"error: no prediction files found under {args.predictions}", file=sys.stderr)
        return 1

    n_with_retro = sum(1 for s in samples if s.has_retro)
    print(f"found {len(samples)} predictions, {n_with_retro} with retrospective data", file=sys.stderr)

    plotted = render_chart(samples, args.out, args.window)
    if plotted:
        print(f"chart written → {args.out}", file=sys.stderr)
    else:
        print("matplotlib not installed — emitting CSV to stdout instead", file=sys.stderr)
        render_csv(samples)

    return 0


if __name__ == "__main__":
    sys.exit(main())
