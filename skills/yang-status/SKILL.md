---
name: yang-status
version: "2.1"
description: 状态看板。查看系统当前状态：校准池大小、待复盘数、rubric 版本、最近预测、准确率趋势。
trigger-words: [状态, status, 看板, 系统概况, 当前状态, 看一眼]
tags: [只读, 诊断, 状态监控, 数据可视化]
author: 阿洋
argument-hint: none
allowed-tools: Bash(*), Read, Grep, Glob
---

# yang-status · 状态看板

> **前置条件**：任意时刻可调用
>
> **产生**：状态摘要（控制台输出）
>
> **只读**：本 skill 不产生任何文件写入

---

## ⚡ 紧凑核心规则

**搜索意图状态**：展示最近一次Channel E拉取的信号分布（搜索建议N条/相关搜索N条/问题型N条/长尾词N条/内容空白N条）+种子词列表+数据时效。

**Humanness Score状态**：展示最近5次润色的Humanness Score变化趋势（Before→After）+当前平均分+等级分布。

## 前置条件检查

> [前置条件] 本 skill 为辅助 skill，无严格流水线前置依赖

读取 `.yang-state.json`:
- 若 `in_progress_session` 不为 null → 警告并发冲突（soft check，不强制拒绝）
- 若 `.yang-state.json` 不存在 → 提示用户运行 yang-init
- 检查通过后，正常执行

---

## 失败模式编码

| 编码 | 名称 | 描述 |
|------|------|------|
| STS-E01 | STATE_MISSING | `.yang-state.json` 不存在，无法读取任何状态 |
| STS-E02 | STATE_CORRUPT | state 文件存在但 JSON 解析失败 |
| STS-E03 | STALE_DATA | 校准样本 > 30% 超 90 天，数据新鲜度不足 |
| STS-E04 | COVERAGE_GAP | 校准池流量覆盖缺失某档次（≤1w/1w-10w/>10w 有空缺） |
| STS-E05 | LOCK_ORPHAN | 残留会话锁超过 2 小时未释放 |
| STS-E06 | KNOWLEDGE_A_DEGRADED | 知识库A 占位状态，数据解读降级为简化数值对比 |

---

## 反例黑名单

1. **禁止写入任何文件**：yang-status 是只读 skill，不得调用 Write/Edit 工具
2. **禁止修改 .yang-state.json**：即使发现字段缺失，也不得自行补齐（应由 yang-doctor --fix 处理）
3. **禁止在样本不足时计算 Spearman ρ**：calibration_records < 5 时不得输出相关系数
4. **禁止省略知识库降级警告**：当知识库A 占位时，必须输出完整降级警告框，不得静默降级
5. **禁止伪造准确率趋势**：数据不足时标注"数据不足"，不得用零值或均值填充
6. **禁止忽略残留锁**：检测到 in_progress_session != null 时必须输出警告，不得静默跳过
7. **禁止硬编码看板数据**：所有数值必须从文件实时读取，不得缓存上次结果

---

## 工作流

### Step 1: 读取 .yang-state.json

> 🔍 **检查点 CP-1**：确认 state 文件存在且 JSON 合法，否则输出 STS-E01/STS-E02 并终止

```json
{
  "schema_version": "v2.1",
  "skill_version": "1.0.0",
  "rubric_version": "v2",
  "content_form": "opinion-video",
  "typical_duration_seconds": 240,
  "target_publish_cadence_days": 2,
  "rubric_form_mismatch": false,
  "benchmark_status": "none",
  "benchmark_name": null,
  "benchmark_sample_count": 0,
  "baseline_plays": null,
  "calibration_samples": 8,
  "calibration_samples_at_last_bump": 5,
  "data_collection": "manual",
  "pool_status": "none",
  "data_layer": "markdown",
  "hooks_installed": false,
  "enabled_trend_sources": ["manual-paste"],
  "enabled_perf_adapters": [],
  "persona_exists": true,
  "persona_version": "v1",
  "persona_name": "阿洋",
  "persona_history": [],
  "competitor_count": 0,
  "calibration_records": [
    {
      "script": "完整脚本文本示例",
      "graded_scores": {
        "hook": {"value": 7, "justification": "开篇钩子明确"},
        "emotion": {"value": 6, "justification": "中段情绪有起伏"},
        "structure": {"value": 8, "justification": "递进式结构清晰"},
        "copywriting": {"value": 7, "justification": "语言有传播力"},
        "persona": {"value": 8, "justification": "人设鲜明统一"},
        "virality": {"value": 6, "justification": "共鸣点明确"},
        "rhythm": {"value": 7, "justification": "节奏张弛有度"}
      },
      "actual_plays": 85000,
      "bucket": "A",
      "scored_by": "3judge-v1",
      "scored_at": "2026-05-15T10:00:00"
    }
  ],
  "last_bump_at": "2026-05-01T10:00:00+08:00",
  "last_bump_self_audited": true,
  "last_published_at": "2026-05-04T15:00:00+08:00",
  "last_published_file": "predictions/2026-05-04_a3f2c1d4e5b6_停止期待.md",
  "last_retro_at": "2026-05-06T10:00:00+08:00",
  "last_trends_run_at": "2026-05-05T08:00:00+08:00",
  "last_trends_added_count": 3,
  "last_prediction_self_scored": false,
  "last_self_scored_at": null,
  "consecutive_directional_errors": [],
  "pending_retros": ["predictions/2026-05-04_video-04.md", "predictions/2026-05-05_video-05.md"],
  "shoots": [
    {
      "video_folder": "shoots/2026-05-06_停止期待",
      "prediction_file": "predictions/2026-05-04_a3f2c1d4e5b6_停止期待.md",
      "shot_at": "2026-05-06T14:00:00+08:00",
      "ad_hoc": false,
      "scripts_path": null,
      "script_consistency": "consistent",
      "script_diff_pct": null,
      "v2_prediction_written": false,
      "script_hash_at_shoot": null
    }
  ],
  "in_progress_session": null,
  "initialized_at": "2026-03-01T10:00:00+08:00"
}
```

### Step 2: 读取 rubric_notes.md

> 🔍 **检查点 CP-2**：确认 rubric_notes.md 存在且非空，否则在看板中标注"rubric 未就绪"

读取版本号 + 活跃维度数 + 待验证观察数。

### Step 3: 扫描 predictions/

> 🔍 **检查点 CP-3**：确认 predictions/ 目录存在，统计预测文件数量，若为空在看板中标注

统计近期预测 + 预测准确率趋势（最近 N 条复盘数据）。

### Step 3.5: 计算校准池健康指标

从校准池中读取每个样本的流量数据和时间信息：

1. **流量覆盖度**: 统计校准样本中 ≤1w / 1w-10w / >10w 三个流量档次的分布
   - 遍历每个已校准样本的实际播放量
   - 若某档次样本数为 0 → 标记为缺失警告
2. **时间新鲜度**: 计算最老样本距今天数 + 超过 90 天样本的比例
   - 遍历每个校准样本的发布时间
   - 计算距今 > 90 天的样本占比
   - 若 > 30% 超 90 天 → 标记为过期警告
3. **平台分布**: 若 `.yang-state.json` 含平台数据（如 `platforms` 字段），统计各平台样本数
   - 若某平台样本数为 0 → 标记为缺失警告

### Step 3.7: 知识库A 完整性检查

读取 `knowledge/ansir/SKILL.md`，检查文件大小：
- 若 < 1KB（占位状态）→ 在 dashboard 顶部输出醒目警告：

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ 知识库A 占位警告                                       │
│                                                         │
│ knowledge/ansir/SKILL.md 当前仅 {N} 字节（占位状态）       │
│                                                         │
│ 以下 skill 功能受影响（降级运行）：                        │
│   · yang-polish —— L4 活人感终审降级为通用规则             │
│   · yang-score —— 评分锚定维度从A降级为B/C混合            │
│   · yang-emotion-curve —— 情绪理论降级为通用ER-Curve      │
│   · yang-hook-factory —— 钩子分类降级为C的开篇36计         │
│   · yang-status —— 数据解读降级为简化数值对比              │
│   · yang-bump —— bump 评估缺少A的结构化数据参考            │
│                                                         │
│ 建议：尽快蒸馏 ansir 课程内容以恢复完整功能。               │
│ 输入「蒸馏 ansir」启动知识蒸馏流程。                       │
└─────────────────────────────────────────────────────────┘
```

- 若 ≥ 1KB → 跳过，正常加载

此检查每个 skill 启动时独立执行，yang-status 集中展示全局状态。

### Step 4: 输出看板

> 🔍 **检查点 CP-4**：所有数据源读取完毕，校验看板各区块数据完整性（无空值/无硬编码）
> 🔍 **检查点 CP-5**：若启用 --detailed 模式，确认 Spearman ρ 计算前提满足（calibration_records ≥ 5）

```
┌────────────────────────────────────────┐
│        Yang.skills · 系统状态               │
├────────────────────────────────────────┤
│                                         │
│  📏 Rubric                              │
│  版本: v2.1.0                           │
│  活跃维度: 5 / 总维度: 7                │
│  待验证观察: 3                          │
│                                         │
│  🎯 校准池                              │
│  已校准样本: 8 / 下次 Bump 需要: ≥10    │
│  达标进度: ████████░ 80%              │
│                                         │
│  📊 校准池健康度                        │
│  流量覆盖: ≤1w(3) 1w-10w(5) >10w(2) ✅ 全覆盖 │
│  时间新鲜度: 最老 67d 超90d: 10% ✅    │
│  平台分布: 抖音(8) B站(2) 小红书(0)     │
│  ⚠️ 小红书无样本                        │
│                                         │
│  📊 预测 vs 实际                         │
│  近 5 条准确率:                          │
│  ▏video-01  ? ████░░ 偏差 5%         │
│  ▏video-02  ███░░░░ 偏差 18%        │
│  ▏video-03  ? █████░? 偏差 3%          │
│  ▏video-04  ? ████░░ 偏差 7%          │
│  ▏video-05  ? 待复盘                     │
│                                         │
│  📋 任务队列                             │
│  待复盘: 2 ▏ video-04, video-05         │
│  待发布: 0                              │
│                                         │
│  🔍 对标                                │
│  已分析账号: 3                          │
│  上次更新: YYYY-MM-DD                    │
│                                         │
│  📁 项目                                │
│  根目录: <path>                         │
│  总预测: 12 ▏ 已发布: 10 ▏ 待复盘: 2    │
│                                         │
│  🔓 功能解锁进度                          │
│  yang-init         ✅ 已完成             │
│  yang-persona      ✅ 已建人设 v1         │
│  yang-seed         ✅ 已启用             │
│  yang-score        ✅ 已启用 (3-Judge)    │
│  yang-polish       ✅ 已启用             │
│  yang-predict      ✅ 已启用 (Channel B)  │
│  yang-publish      ✅ 已启用             │
│  yang-retro        ⚠️ 2 条待复盘          │
│  yang-bump         ⚪ 未触发（需≥10校准）   │
│  yang-benchmark    ⚪ 未设置对标           │
│  yang-hook-factory ✅ 已启用             │
│  yang-emotion-curve✅ 已启用             │
│  yang-doctor       ✅ 已启用             │
│  yang-learn        ⚪ 未使用             │
│  yang-learn-from   ⚪ 未使用             │
│  yang-trends       ⚪ 未启用             │
│  yang-recommend    ⚪ 未启用             │
│  yang-bridge       ⚪ 未配置跨平台         │
│                                         │
└────────────────────────────────────────┘
```

### --detailed 模式：预测精度进化可视化

当用户输入 `/yang-status --detailed` 时，额外输出以下三项：

#### 📈 误差趋势（最近 5 条）

读取最近 5 条内容的预测分 vs 实际表现对比：
- 若 `predictions/` 目录下不足 5 条 → 显示已有数据
- 每条内容显示：预测分 → 实际表现 / 误差 / 趋势箭头

```
📈 预测精度进化趋势
  预测趋势（最近 5 条）：⬊⬈⬊⬈⬊  → 误差在收敛（p=0.06）
```

#### 📊 维度相关性（Spearman ρ）

从 `.yang-state.json` 的 `calibration_records` 数组中读取每条记录，对每个维度计算预测分与实际表现的 Spearman 秩相关系数：

- 若 `calibration_records` 长度 < 5 → 显示 "样本不足（需≥5条校准记录），无法计算相关系数"
- 若可用 → 计算步骤：
  1. 对每条记录：取 `graded_scores.{维度}.value` 为预测分（0-10）
  2. 对每条记录：取 `predicted_bucket`（预测桶）和计算 `actual_bucket`（根据 `actual_plays` 按桶阈值映射：<5w→D, 5-30w→C, 30-100w→B, >100w→A）
  3. 将 bucket 映射为数值：A=4, B=3, C=2, D=1
  4. 对每个维度：计算该维度预测分与 actual_bucket 数值的 Spearman 秩相关系数
  5. 同时计算 predicted_bucket 与 actual_bucket 的命中率（一致比例）

```
📊 维度相关性（Spearman ρ）
  钩子力 0.72 | 情绪力 0.65 | 结构力 0.58 | 文案力 0.71
  人设力 0.55 | 传播力 0.48 | 节奏力 0.61
  Bucket 命中率：6/8 (75%)
```

数据来源：`.yang-state.json` → `calibration_records[{graded_scores, predicted_bucket, actual_plays}]`

#### 📉 Bump 进化趋势

读取 `migrations/registry.md` 中的 bump 历史记录，展示每次 bump 后的 Spearman ρ 提升：

```
📉 Bump 进化
  v1.0: ρ=0.42 → v1.1: ρ=0.51 → v1.2: ρ=0.58 → v2.0: ρ=0.67
  ↑ +25%（累计提升）
```

若无 bump 历史 → 显示 "尚未执行过 bump，无进化趋势数据"

### 残留锁检测

若 `in_progress_session != null`:
  检查 `started_at` 距今是否超过 2 小时
  若超过：
    → 输出警告：
      ```
      ⚠️ 检测到残留会话锁
      类型: {in_progress_session.type} | 文件: {in_progress_session.file}
      开始时间: {started_at}（距今 {N} 小时）
      输入「清除锁」强制清除，或继续等待该会话完成。
      ```

---

### 知识库A 状态检测

读取 `knowledge/ansir/SKILL.md`:
- 若文件大小 < 1KB → 判定为占位状态
  → 在知识来源标注中显示 "A-占位（内容降级）"
  → 降低知识库A 的权重依赖
- 若 ≥ 1KB → 正常加载

**降级行为（yang-status）**：数据解读框架从A降级读取
- 当A降级时：三大数据维度和流量结构模型的数据解读框架不可用
- 准确率趋势的数据解读 → 降级为纯数值对比（不使用A的2秒跳出率/停留时长/互动反馈三维分析）
- 校准池健康度的底层逻辑判断 → 降级为简单阈值判断（样本数是否达标）
- 看板输出中去除A相关的深度解读标签
- 知识依据标注自动调整：`A-数据 | A-流量` → `A-占位（简化解读）`

---

## 知识库依赖

本 skill 在状态看板展示过程中引用以下知识库内容：

- 知识库A：三大数据维度（2秒跳出率/停留时长/互动反馈）—— 用于准确率趋势的数据解读框架 `[来源：A-数据]`
- 知识库A：流量结构模型（流量 = 需求量大 x 数据好）—— 用于校准池健康度的底层逻辑判断 `[来源：A-流量]`

在看板输出后，系统内部引用上述知识库作为数据解读依据。

```
📚 知识依据：A-数据 | A-流量
```

---

## 错误处理

| 场景 | 行为 |
|------|------|
| .yang-state.json 不存在 | 提示"项目尚未初始化，先运行 '初始化'" |
| predictions/ 目录为空 | 显示"还没有做过预测" |

---

## 量化标准：看板数据新鲜度评分

看板输出的整体可信度由**数据新鲜度评分**量化，满分 100 分，低于 60 分在看板顶部标注⚠️警告。

| 维度 | 权重 | 计算方式 | 满分条件 |
|------|------|---------|---------|
| 校准池规模 | 30% | `min(calibration_samples / 10, 1) × 30` | ≥10 条得满分 |
| 时间新鲜度 | 25% | `(1 - 超90天样本占比) × 25` | 无超90天样本得满分 |
| 流量覆盖度 | 20% | `已覆盖档次数 / 3 × 20` | 3 档全覆盖得满分 |
| 预测复盘率 | 15% | `已复盘数 / 总预测数 × 15` | 100% 复盘得满分 |
| 知识库A状态 | 10% | A正常=10, A降级=3, A缺失=0 | 知识库A正常加载得满分 |

**评分输出格式**：
```
📊 数据新鲜度评分：82/100
  校准池规模: 24/30 | 时间新鲜度: 23/25 | 流量覆盖: 20/20 | 复盘率: 12/15 | 知识库A: 3/10 ⚠️
```

---

## 状态看板自定义

用户可以自定义看板显示的指标和排序方式，通过 `--config` 参数或交互式配置：

### 自定义指标选择

| 指标分组 | 可选指标 | 默认显示 |
|---------|---------|---------|
| Rubric | 版本号、活跃维度数、待验证观察数 | 全部显示 |
| 校准池 | 样本数、达标进度、流量覆盖、时间新鲜度、平台分布 | 全部显示 |
| 预测 | 近期准确率、误差趋势、Bucket 命中率 | 近期准确率 + 误差趋势 |
| 任务 | 待复盘数、待发布数、会话锁状态 | 待复盘数 + 待发布数 |
| 对标 | 已分析账号数、上次更新时间、数据有效期状态 | 已分析账号数 + 上次更新 |
| 项目 | 总预测数、已发布数、根目录 | 全部显示 |
| 功能解锁 | 各 skill 启用状态 | 全部显示 |

### 排序自定义

| 排序维度 | 可选排序方式 | 默认排序 |
|---------|------------|---------|
| 校准池 | 按样本数 / 按达标进度 / 按新鲜度 | 按达标进度 |
| 预测 | 按时间 / 按准确率 / 按误差 | 按时间 |
| 任务 | 按紧急度 / 按时间 / 按类型 | 按紧急度 |

### 配置方式

**方式一：命令行参数**

```bash
yang-status --config show=rubric,calibration,prediction --sort calibration=progress,prediction=accuracy
```

**方式二：交互式配置**

输入 `yang-status --customize` 进入交互模式：

```
🎨 看板自定义配置

当前显示指标: [rubric, calibration, prediction, task, benchmark, project, unlock]
请选择要显示的指标分组（输入编号，空格分隔）:
  1. Rubric  2. 校准池  3. 预测  4. 任务  5. 对标  6. 项目  7. 功能解锁

排序设置:
  校准池排序 (1.样本数 2.达标进度 3.新鲜度): 2
  预测排序 (1.时间 2.准确率 3.误差): 2

是否保存为默认配置？(y/n)
```

**方式三：配置文件**

在项目根目录创建 `.yang-dashboard.json`：

```json
{
  "show_groups": ["rubric", "calibration", "prediction", "task"],
  "sort": {
    "calibration": "progress",
    "prediction": "accuracy"
  },
  "compact_mode": false,
  "hide_healthy_items": false
}
```

### 紧凑模式

输入 `yang-status --compact` 仅显示异常项和关键指标：

```
┌────────────────────────────────────────┐
│  Yang.skills · 紧凑看板                   │
├────────────────────────────────────────┤
│  ⚠️ 校准池: 8/10 (80%) 待补充           │
│  ⚠️ 待复盘: 2 条                        │
│  ⚠️ 知识库A: 占位状态                    │
│  ✅ 预测准确率: 75%                      │
│  ✅ Rubric: v2.1.0                      │
└────────────────────────────────────────┘
```

---

## 异常状态告警规则

以下状态组合应触发告警，帮助用户及时发现系统异常：

### 告警级别定义

| 级别 | 图标 | 含义 | 是否需要立即行动 |
|------|------|------|---------------|
| 🔴 严重 | 🔴 | 系统功能受损或数据丢失风险 | 是，立即处理 |
| 🟡 警告 | ⚠️ | 数据质量下降或功能受限 | 尽快处理 |
| 🔵 提示 | ℹ️ | 建议优化但不影响核心功能 | 可选处理 |

### 告警规则表

| 规则编号 | 状态组合 | 告警级别 | 告警信息 | 建议行动 |
|---------|---------|---------|---------|---------|
| ALT-01 | calibration_samples < 5 | 🔴 严重 | 校准池严重不足（< 5 条），评分系统不可靠 | 立即执行 yang-score + yang-retro 补充校准数据 |
| ALT-02 | pending_retros ≥ 3 | 🔴 严重 | 积压 {N} 条待复盘，预测-实际校准断裂 | 立即执行 yang-retro 清理积压 |
| ALT-03 | calibration_samples 中 > 50% 超 90 天 | 🟡 警告 | 校准数据过旧（> 50% 超 90 天），评分可能偏移 | 执行 yang-retro 更新近期数据 |
| ALT-04 | 流量覆盖缺失 ≥ 2 档 | 🟡 警告 | 流量覆盖不完整，缺少 {缺失档次} 样本 | 针对性补充缺失流量档次的内容 |
| ALT-05 | 知识库A 占位 | 🟡 警告 | 知识库A 占位状态，多个 skill 功能降级 | 输入「蒸馏 ansir」启动知识蒸馏 |
| ALT-06 | 残留会话锁 > 2 小时 | 🟡 警告 | 残留会话锁超 2 小时未释放 | 输入「清除锁」强制清除 |
| ALT-07 | 连续 3 次预测方向性错误 | 🟡 警告 | 连续 3 次预测方向偏差，rubric 可能需要校准 | 执行 yang-bump 校准 rubric |
| ALT-08 | calibration_samples ≥ 10 且未执行 bump | 🔵 提示 | 校准池已达标（≥ 10 条），可执行 bump 升级 rubric | 执行 yang-bump |
| ALT-09 | 对标数据全部 stale | 🔵 提示 | 所有对标数据已过期，参考价值下降 | 执行 yang-benchmark 更新对标数据 |
| ALT-10 | 最近 7 天无任何操作记录 | 🔵 提示 | 系统近 7 天无活动，数据可能过时 | 执行 yang-status --detailed 检查整体状态 |

### 组合告警

当多个告警同时触发时，输出组合告警摘要：

```
🚨 系统告警摘要（{N} 项）

🔴 严重 (2):
  · 校准池严重不足（3 条，需 ≥ 5）→ 立即补充
  · 积压 4 条待复盘 → 立即清理

🟡 警告 (1):
  · 知识库A 占位 → 输入「蒸馏 ansir」

建议优先处理 🔴 严重告警
```

### 告警抑制

- 同一告警在 24 小时内仅触发一次（避免重复提醒）
- 用户可通过 `.yang-dashboard.json` 的 `suppress_alerts` 字段抑制特定告警：

```json
{
  "suppress_alerts": ["ALT-05", "ALT-09"]
}
```

---

## 状态趋势分析

从状态历史数据中发现趋势，帮助用户预判系统走向：

### 趋势数据采集

每次执行 `yang-status` 时，将关键指标快照追加到 `.yang-cache/status_history.jsonl`：

```json
{"ts": "2026-06-14T10:00:00+08:00", "calibration_samples": 8, "accuracy_rate": 0.75, "pending_retros": 2, "data_freshness_score": 82, "rubric_version": "v2"}
{"ts": "2026-06-15T10:00:00+08:00", "calibration_samples": 9, "accuracy_rate": 0.78, "pending_retros": 1, "data_freshness_score": 85, "rubric_version": "v2"}
```

### 可分析的趋势维度

| 趋势维度 | 数据来源 | 分析方法 | 趋势信号 |
|---------|---------|---------|---------|
| 校准池增长趋势 | `calibration_samples` 时序 | 线性回归斜率 | 斜率 > 0 → 增长中；斜率 ≈ 0 → 停滞 |
| 准确率趋势 | `accuracy_rate` 时序 | 移动平均（窗口 5） | 上升/下降/震荡 |
| 复盘积压趋势 | `pending_retros` 时序 | 当前值 vs 7 天前值 | 增加 → 积压恶化；减少 → 改善 |
| 数据新鲜度趋势 | `data_freshness_score` 时序 | 线性回归斜率 | 下降 → 数据老化加速 |
| Rubric 稳定性 | `rubric_version` 变更频率 | 版本变更间隔 | 频繁变更 → 不稳定；长期不变 → 可能过时 |

### 趋势分析输出

输入 `yang-status --trend` 时输出趋势分析：

```
📈 状态趋势分析（近 30 天）

校准池: 5 → 8 → 9 📈 增长中（+80%，斜率 +0.13/天）
  预计达标（≥ 10 条）: 约 8 天后

准确率: 65% → 72% → 78% 📈 上升中（+13pp）
  趋势: 稳步提升，rubric 校准有效

复盘积压: 3 → 4 → 2 📉 改善中
  当前: 2 条待复盘，可控

数据新鲜度: 78 → 82 → 85 📈 改善中
  主要贡献: 近期补充了 3 条新校准样本

Rubric: v2（已稳定 45 天）
  ⚠️ 超过 30 天未 bump，建议评估是否需要校准

综合判断: 🟢 系统健康度上升趋势
  建议关注: Rubric 稳定性（已 45 天未更新）
```

### 趋势预警

当趋势分析发现以下信号时，主动输出预警：

| 预警信号 | 触发条件 | 预警信息 |
|---------|---------|---------|
| 校准池停滞 | 连续 14 天 calibration_samples 无增长 | "校准池增长停滞，评分系统可能逐渐失准" |
| 准确率下降 | 移动平均连续 3 次下降 | "预测准确率持续下降，建议执行 yang-bump" |
| 复盘积压恶化 | pending_retros 连续 3 次增加 | "复盘积压持续增加，校准数据链可能断裂" |
| 数据老化加速 | data_freshness_score 连续 3 次下降 > 5 分 | "数据新鲜度加速下降，建议补充近期内容数据" |