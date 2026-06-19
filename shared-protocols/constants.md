<!-- 作者: 阿洋 -->
# Yang.skills 共享常量 (Single Source of Truth)

所有跨 skill 的数值常量集中定义在此文件中。任何 skill 或 hook 需要使用以下数值时，应引用此文件而非硬编码。

---

## 打分量程

| 常量 | 值 | 说明 | 使用场景 |
|------|-----|------|---------|
| `SCORING_SCALE_MIN` | `0` | 最低分 | yang-score, yang-score-blind, starter-rubrics, dspy_scoring.py |
| `SCORING_SCALE_MAX` | `10` | 最高分 | yang-score, yang-score-blind, starter-rubrics, dspy_scoring.py |

## 校准样本阈值

| 常量 | 值 | 说明 | 使用场景 |
|------|-----|------|---------|
| `BUMP_MIN_CALIBRATION_SAMPLES` | `10` | yang-bump 最小校准样本数，少于此值不执行 bump | yang-bump, bump-trigger-monitor.sh |
| `PUBLISH_OPTIMIZER_MIN_SAMPLES` | `8` | yang-publish-optimizer 最小样本数，少于此值仅展示频率统计 | yang-publish-optimizer, yang-status |
| `EVOLUTION_BUS_MIN_SAMPLES` | `30` | yang-evolution-bus 最小样本数，少于此值不触发 | yang-evolution-bus, yang-status |

## 争议与分歧阈值

| 常量 | 值 | 说明 | 使用场景 |
|------|-----|------|---------|
| `BUMP_DISAGREEMENT_THRESHOLD` | `2` | yang-bump 争议阈值，在 0-10 量程下各 Judge 极差 > 2 触发争议标记 | yang-bump |
| `PREDICTION_DISAGREEMENT_THRESHOLD` | `0.4` | yang-predict Step 2.5 分歧阈值，主 Claude 分与 Channel B 分的归一化差异 ≥ 0.4 触发裁定 | yang-predict |

## 去重与改稿阈值

| 常量 | 值 | 说明 | 使用场景 |
|------|-----|------|---------|
| `DUPLICATE_CATEGORY_LOOKBACK_BASE` | `3` | yang-recommend 去重回顾基数：最近 N 条内同主题脚本视为重复 | yang-recommend |
| `DIFF_PCT_V2_THRESHOLD` | `30` | yang-shoot 改稿超过 30% 触发 v2 重判（在 0-10 量程下） | yang-shoot |

## 人设系统参数

| 常量 | 值 | 说明 | 使用场景 |
|------|-----|------|---------|
| `PERSONA_MAX_QUESTION_ROUNDS` | `2` | yang-persona 追问最多 2 轮 | yang-persona |

## 防膨胀参数 (neat-freak)

| 常量 | 值 | 说明 | 使用场景 |
|------|-----|------|---------|
| `RUBRIC_NOTES_MAX_LINES` | `250` | rubric_notes.md 单次 bump 后净增幅行数上限 | yang-doctor 诊断项 11 |
| `BENCHMARK_STALE_MONTHS` | `6` | benchmark.md 中对标账号 N 个月未更新，提示删除 | yang-doctor 诊断项 13 |

## 时效锁参数 (Freshness / Time-Lock)

一切外部抓取数据（对标视频、竞品快照、热点选题、高赞评论）都以"运行那一刻的真实日期"为锚做新鲜度判定，防止把旧时间内容误当作当下有效信号。详见 `shared-protocols/freshness-protocol.md`。

| 常量 | 值 | 说明 | 使用场景 |
|------|-----|------|---------|
| `FRESHNESS_WINDOW_DAYS` | `90` | 新鲜窗口：发布距今 ≤ 90 天判为 `fresh`，可直接作当下信号 | adapters/_common/freshness.py, yang-benchmark, yang-seed, yang-trends, yang-learn-from |
| `FRESHNESS_AGING_HARD_LIMIT_DAYS` | `365` | 偏旧硬上限：90–365 天判为 `aging`（可用但须显式标注"偏旧"），> 365 天判为 `stale`（默认剔除/降权） | 同上 |

> 说明：`FRESHNESS_WINDOW_DAYS` / `FRESHNESS_AGING_HARD_LIMIT_DAYS` 与代码层 `adapters/_common/freshness.py` 中的 `DEFAULT_FRESHNESS_WINDOW_DAYS` / `DEFAULT_STALE_HARD_LIMIT_DAYS` 一一对应；调用方可在运行时显式传参覆盖。`BENCHMARK_STALE_MONTHS`（6 个月）是 yang-doctor 对"对标库账号长期不更新"的清理阈值，与本组按"单条内容发布时间"判定的时效锁互补、各司其职。

## Tier 功能阈值

| Tier | 功能范围 |
|------|---------|
| `core` | 基础功能：yang-score(-blind), yang-seed(-blind), yang-predict, yang-bump, yang-polish, yang-hook-factory, yang-emotion-curve, yang-retro, yang-shoot, yang-publish, yang-status, yang-doctor, yang-recommend, yang-persona, yang-init |
| `media` | core + Playwright 浏览器自动化：yang-benchmark, yang-learn, yang-learn-from |
| `full` | media + 实验性功能：yang-evolution-bus, yang-trends MCP, yang-publish-optimizer 进阶分析 |