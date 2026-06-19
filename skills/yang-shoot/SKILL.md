---
name: yang-shoot
version: "2.0"
author: 阿洋
description: 登记一条视频已拍摄。**建 video folder + 询问实际拍摄稿是否与 scripts/<id>.md 一致 + buffer +1**。与 yang-publish 配对：拍了进队列，发了出队列。触发词："拍了"/"拍了 X"/"shot"/"shot it"/"已拍 X"/"录完了"。
trigger-words: [拍了, shot, shot it, 已拍, 录完了, 拍摄完成, 拍好了]
tags: [shoot, buffer管理, 改稿检测, v2预测, 拍摄登记]
argument-hint: "<scripts-path-or-id>"
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /yang-shoot — 登记拍摄完成 + 建 video folder + (改稿则) 触发 v2 预测

把视频从"已写预测、未拍摄"状态推进到"已拍摄、未发布"状态。这一步：
1. **建 `videos/<同 id>/`** 目录（之前没有的话）
2. **询问用户**："实际拍摄时用的稿子和 `scripts/<id>.md` 一致吗？"
3. 算 diff——超过 V2_TRIGGER_THRESHOLD (默认 30%) → **delegate 到 `/yang-predict — mode: v2`** 在原 prediction 文件 append `## 预测 v2` 段
4. 把 video folder 加进 state.shoots 队列，buffer +1

yang-shoot 自己**不**写预测内容——所有预测落盘逻辑在 yang-predict。yang-shoot 只负责检测改稿 + 派发。

为什么单独一个 skill：
- buffer 警戒系统需要明确区分"拍了" vs "发了"。视频可以批量拍（一天拍 5 条），分散发（每天发 1 条）
- "实际拍摄稿" ≠ "pre-shoot 草稿"是常态。这一步是把 diff 显式化、触发 v2 重判、采集"用户改稿 pattern"信号的入口
- v2 预测 vs v1 预测的差异本身就是 rubric 升级证据——比如 v1 给 ER=4，v2 给 ER=5（用户改稿改高了 hook 强度），就告诉 rubric "这个用户的 ER 阈值跟我现在公式不一致"

## Overview

```
[用户：拍了 scripts/2026-05-04_abc123_停止期待.md]
  ↓
[Phase 0: 解析路径 + 验证 prediction 已存在]
  ↓
[Phase 1: 检查是否已登记（避免重复）]
  ↓
[Phase 2: 建 videos/<id>/ + 询问"实际拍摄稿一致吗？"]
  ↓
[Phase 3: 写 videos/<id>/script.md]
  ↓
[Phase 4: append state.shoots]
  ↓
[Phase 5: 输出 buffer 状态]
```

## Constants

- **REQUIRE_PREDICTION = true** — 拍前必须先有 v1 prediction 文件
- **V2_TRIGGER_THRESHOLD = 0.30** — 稿子 diff 超过 30%（行级 unified diff 行数 / 原稿子行数）→ 默认建议 v2 重判；低于 30% 询问用户是否仍要 v2
- **DIFF_METRIC = lines** — 用 `diff -u | grep '^[+][^+]'` / `grep '^[-][^-]'` 算改动行数 / 原文件行数（排除 diff header 行）

## Inputs

| 必填 | 来源 |
|---|---|
| `<scripts-path-or-id>` | 用户参数；缺失则询问 |
| `.yang-state.json` | 状态文件 |
| `scripts/*.md` | pre-shoot 草稿 |
| `predictions/*.md` | 验证对应预测存在 |

---

## 前置条件检查

> [前置条件] 运行本 skill 前，必须满足: `last_prediction_file` 不为 null

读取 `.yang-state.json`:
- 若 `last_prediction_file` 为 null → 拒绝执行：
  ```
  [前置条件不满足] 请先运行 yang-predict
  当前状态: last_prediction_file = null
  ```
- 若 `in_progress_session` 不为 null：
  - 若 `started_at` 距今超过 2 小时 → 输出警告并询问用户：
    ```
    ⚠️ 检测到残留会话锁
    类型: {in_progress_session.type} | 文件: {in_progress_session.file}
    开始时间: {started_at}（距今 {N} 小时）
    是否清除并继续？(y/n)
    ```
  - 否则 → 并发冲突警告，拒绝执行："检测到另一流程正在运行中"
- 检查通过后，设置 `in_progress_session`，执行原子写入

---

## 执行模式

> [执行模式] 本 skill 使用单 Agent 顺序模式：解析路径 → 询问一致性 → 写 video folder → 更新 state。原因：涉及文件路径解析和状态写入，需保证顺序一致性。

---

## Workflow

### Phase 0：解析 + 验证

> 🔍 **CHECKPOINT 0**：脚本路径已解析，prediction 文件存在性已验证

1. 解析用户给的路径——支持几种形态：
   - 完整路径 `scripts/2026-05-04_abc123_停止期待.md`
   - 简写 `2026-05-04_abc123_停止期待`
   - id 简写 `abc123` → glob `scripts/*_abc123_*.md` 找匹配
2. 验证 `scripts/<id>.md` 存在：不存在 → 报错"找不到 pre-shoot 草稿"
3. 验证有对应 prediction `predictions/<同名>.md`：
   - 不存在 → **拒绝登记**，提示"先跑 /yang-predict 写预测，否则违反盲预测原则——你不能拍完才写预测，那等于事后看了画面写"
   - 存在 → 通过

### Phase 1：检查重复

读 `.yang-state.json`，检查 `shoots[]` 是否已含此 id：
- 已存在 → 警告"已登记过（X 天前）。是要重新登记，还是要用 /yang-publish 发布？"
- 不存在 → 进入 Phase 2

### Phase 2：建 video folder + 询问稿子一致性

> 🔍 **CHECKPOINT 1**：video folder 已创建，稿子一致性路径（a/b/c）已选择

1. 建目录 `videos/<id>_<short>/`（同 scripts/ + predictions/ 的命名）
2. **询问用户**：

```
拍 「<title>」 的时候，你实际用的稿子和 scripts/<id>.md 一致吗？

a) 一致——按草稿拍的
b) 改了一些——你能给我看下实际拍摄稿吗？我重新打分一次（v2 预测）
c) 大改了，基本是另一条 → 走 _redo 流程：
   scripts/<id>_redo.md → 重新 yang-predict → 再 yang-shoot（原 prediction 留档脱钩）
```

### Phase 3：写 videos/<id>/script.md + (b 路径) 触发 v2 预测

> 🔍 **CHECKPOINT 2**：实际拍摄稿已写入，diff 已计算，v2 触发判定已完成

**a 路径（一致）**：
- `cp scripts/<id>.md → videos/<id>/script.md`
- `script_consistency = consistent`
- 不重判，进 Phase 4

**b 路径（改了）**：
1. 询问用户实际拍摄稿——粘贴文本 / 文件路径 / 转录文件
2. 若用户提供 → 写入 `videos/<id>/script.md`
3. 若用户没保留（即兴）→ 标 `script_lost`，写占位文件 + 警告"v2 重判跳过——下次建议留稿（哪怕 voice memo 转录）"，进 Phase 4
4. 提供了的话：算 diff
   ```bash
   added=$(diff -u scripts/<id>.md videos/<id>/script.md | grep -c '^[+][^+]')
   removed=$(diff -u scripts/<id>.md videos/<id>/script.md | grep -c '^[-][^-]')
   total_orig=$(wc -l < scripts/<id>.md)
   diff_pct=$(( (added + removed) * 100 / total_orig ))
   ```
5. **判定 v2 触发**：
   - `diff_pct >= 30` → 默认建议 v2 重判，**主动调用** `/yang-predict — mode: v2 — prediction-file: predictions/<id>.md` 传 `videos/<id>/script.md` 作 input。yang-predict 走 v2 模式 append `## 预测 v2`
   - `diff_pct < 30` → 询问用户："只改了 N% 的内容，要重判吗？默认不（v1 预测仍有效）"。用户说要 → 同上调用；用户说不 → 跳过 v2，继续 Phase 4
6. yang-predict 完成 v2 落盘后，控制权回到 yang-shoot 进 Phase 4

**c 路径（大改）**：
- 不写 `videos/<id>/script.md`，提示走 `_redo` 流程
- 退出 yang-shoot（不进 Phase 4）

### Phase 4：state 更新

> 🔍 **CHECKPOINT 3**：state.shoots 队列已追加，buffer +1 已生效

```json
{
  "shoots": [
    ...,
    {
      "video_folder": "videos/2026-05-04_abc123_停止期待/",
      "prediction_file": "predictions/2026-05-04_abc123_停止期待.md",
      "scripts_path": "scripts/2026-05-04_abc123_停止期待.md",
      "shot_at": "<ISO timestamp>",
      "script_consistency": "consistent" | "modified" | "lost",
      "script_diff_pct": <0-100 int 或 null>,
      "v2_prediction_written": <true/false>,
      "script_hash_at_shoot": "<sha256:12 of videos/<id>/script.md>"
    }
  ]
}
```

`v2_prediction_written: true` 表示 prediction 文件里现在有 `## 预测 v2` 段，yang-retro 应读 v2 算偏差；`false` 表示沿用 v1。

### Phase 5：输出 buffer 状态

> 🔍 **CHECKPOINT 4**：buffer 颜色已计算，节奏建议已输出

读完 state 后立即算 buffer + 颜色（按 [cadence-protocol.md](../../shared-protocols/cadence-protocol.md) 的派生规则）：

```
? 已登记拍摄：videos/2026-05-04_abc123_停止期待/
   预测文件：predictions/2026-05-04_abc123_停止期待.md

⚠ 当前 buffer：3 篇（🟢 绿色，正常）
   按你的 cadence（隔日更）= 6 天 buffer，节奏稳定。

下一步：拍其他候选 / 等下个发布日 / 不动
```

如果 buffer 颜色变了（如从绿到蓝）→ 高亮提醒：
```
⚠ 当前 buffer：6 篇（🔵 蓝色，**积压**）
⚠ 建议暂停拍摄，全力发布存货 + 复盘。
   按你的 cadence（日更）= 6 天预备，已超过健康上限。
```

## Key Rules

1. **不写 prediction**——拍了 ≠ 发了。预测在 /yang-predict 锁，拍只是事件
2. **不动 video folder 内容**——script.md / draft-v0.md 都不改
3. **必须先有 prediction**——否则违反盲预测（拍完看了画面再写预测 = 数据泄漏到判断）
4. **buffer 计算实时**——每次 shoot / publish 后立刻重算，state.shoots 是真值
5. **支持批量**：用户可以一天连说 "拍了 X / 拍了 Y / 拍了 Z" 三次连续登记

**Humanness Score拍摄指引**：拍摄前检查脚本的Humanness Score——若<50，建议先润色再拍，避免录制后需要大量重拍。Score>70的脚本拍摄通过率更高。

## Refusals

- 「拍了 X，但我从来没跑过 yang-predict」 → 拒绝。v1 预测**必须拍前写**——拍完才写预测会被画面诱导事后修改。请先 /yang-predict 写 v1 再来 /yang-shoot。（v2 重判是另一回事——v1 已存在 + 拍后改稿才允许）
- 「我没有 video folder，我直接拍的」 → 询问用户 → 帮他建 video folder + 提示下次走完整流程；登记时标 `ad_hoc: true`
- 「我改稿了但你直接覆盖 v1 吧，别留 v2 段」 → 拒绝。v1 是档案，v2 才是当前判断——append 不覆盖。两段一起留是 rubric 学习的关键证据

## 知识库依赖

本 skill 在拍摄登记与改稿检测过程中引用以下知识库内容：

- 知识库B：四大脚本类型与执行一致性—— 用于拍摄稿与预写稿的差异比对逻辑 `[来源：B-脚本]`
- 知识库A：数据追踪闭环—— 用于 v2 重判触发阈值的校准依据 `[来源：A-数据]`

在输出拍摄登记结果时，应追加：

```
📚 知识依据：B-脚本 | A-数据
```

---

## Integration

- 上游：`/yang-predict` 写完 prediction → 用户拍摄 → `/yang-shoot` 登记
- 下游：`/yang-publish` 发布时把对应项从 state.shoots 移除
- `/yang-status` 看板的 buffer 数字直接来自 `state.shoots.length`
- `/yang-recommend` 看 buffer 颜色调推荐策略
- SessionStart hook 看 buffer 颜色决定报告第一行

## state.shoots 数据结构

```json
{
  "shoots": [
    {
      "video_folder": "videos/2026-05-04_abc123_停止期待/",
      "prediction_file": "predictions/2026-05-04_abc123_停止期待.md",
      "scripts_path": "scripts/2026-05-04_abc123_停止期待.md",
      "shot_at": "2026-05-04T18:30:00+08:00",
      "script_consistency": "consistent",
      "script_diff_pct": 0,
      "v2_prediction_written": false,
      "script_hash_at_shoot": "abc123def456"
    }
  ]
}
```

`script_consistency`: `"consistent"` | `"modified"` | `"lost"` — yang-retro 用此字段和 `v2_prediction_written` 决定读取 v1 还是 v2 预测段。
`script_diff_pct`: 0-100 整数或 `null`（script_lost 时）。
`v2_prediction_written`: `true` 表示 prediction 文件里有 `## 预测 v2` 段。

按 `shot_at` 升序——最早拍的在前面。`/yang-status` 显示最早一项的 days-since-shoot 警告（避免有视频拍了 30 天没发）。

## 失败模式编码

| 编码 | 名称 | 描述 |
|------|------|------|
| `YS-E01` | 预测前置缺失 | 无 v1 prediction 文件，违反盲预测原则 |
| `YS-E02` | 重复登记 | shoots[] 已含此 id，避免 buffer 重复 +1 |
| `YS-E03` | 脚本路径无法解析 | 用户给的路径/ID 匹配不到任何 scripts/ 文件 |
| `YS-E04` | 实际稿丢失 | 用户即兴拍摄未留稿，标 script_lost 但 v2 重判无法执行 |
| `YS-E05` | v2 触发误判 | diff 计算错误导致 v2 重判未触发或误触发 |
| `YS-E06` | 并发冲突 | in_progress_session 被其他流程占用 |

## 反例黑名单

1. **禁止在无 v1 prediction 时登记拍摄**——拍完才写预测等于事后修改，违反盲预测原则
2. **禁止覆盖 v1 预测段**——v1 是档案，v2 只能 append，两段共存是 rubric 学习的关键证据
3. **禁止跳过稿子一致性询问**——实际拍摄稿与草稿的差异是改稿 pattern 信号的唯一入口
4. **禁止在 script_lost 时假装 v2 重判完成**——无稿则无 diff，v2 重判必须跳过并明确标注
5. **禁止在 buffer 🔵 积压时继续推荐拍摄**——按 cadence-protocol，积压时暂停拍摄，先发存货
6. **禁止静默忽略重复登记**——shoots[] 已含此 id 必须警告，避免 buffer 虚增
7. **禁止在 diff 计算时包含 diff header 行**——只算 `^[+][^+]` 和 `^[-][^-]`，排除 `+++`/`---` header
8. **禁止在 c 路径（大改）时继续 Phase 4**——大改走 _redo 流程，yang-shoot 必须退出

## 特有量化标准：改稿偏离度分级

每次拍摄登记须计算**改稿偏离度**（script_diff_pct），并按以下标准分级记录：

| 偏离度区间 | 等级 | 标记 | 处理 |
|------------|------|------|------|
| 0% | 一致 | `consistent` | 直接进 Phase 4，不触发 v2 |
| 1-29% | 微调 | `minor_edit` | 询问用户是否 v2 重判，默认不触发 |
| 30-59% | 中改 | `significant_edit` | 默认触发 v2 重判，用户可覆盖 |
| ≥60% | 大改 | `major_rewrite` | 建议走 _redo 流程；若用户坚持，强制触发 v2 |

偏离度等级写入 `state.shoots` 对应条目的 `edit_severity` 字段。yang-retro 复盘时按等级加权：`major_rewrite` 的 v1→v2 偏差是 rubric 升级的高价值证据（权重 ×2），`minor_edit` 的偏差视为噪声（权重 ×0.5）。

---

## 拍摄登记与脚本对齐

> 确保拍摄内容与评分脚本一致是盲预测闭环的关键。本段定义从脚本到拍摄的全程对齐规则。

### 对齐检查机制

拍摄登记时（Phase 2），须执行以下对齐检查：

| 检查项 | 检查方式 | 不一致处理 |
|--------|---------|-----------|
| 脚本 ID 匹配 | `scripts/<id>.md` 与 `predictions/<id>.md` 的 ID 一致 | 拒绝登记，提示"脚本与预测文件 ID 不匹配" |
| 脚本哈希校验 | 比对 `scripts/<id>.md` 的 SHA256 与预测文件记录的 `script_hash` | 哈希不匹配 → 警告"脚本在预测后已被修改，预测基线可能失效" |
| 维度评分锚定 | 预测文件中各维度评分引用的脚本段落是否仍存在 | 引用段落缺失 → 警告"评分依据的脚本段落已变更" |
| 关键结构节点 | 脚本中的 Hook/转折/结尾结构是否完整 | 结构节点缺失 → 标记 `structure_drift: true` |

### 对齐等级

| 等级 | 条件 | 后续处理 |
|------|------|---------|
| 完全对齐 | 哈希一致 + 结构完整 + 无段落变更 | 正常登记，沿用 v1 预测 |
| 轻微偏移 | 哈希不一致但 diff < 10%，结构完整 | 标记 `minor_drift`，询问用户是否需要 v2 |
| 结构偏移 | Hook/转折/结尾任一节点变更 | 标记 `structure_drift`，建议 v2 重判 |
| 严重偏移 | diff ≥ 30% 或多个结构节点变更 | 按改稿偏离度分级处理 |

### 对齐记录

每次拍摄登记须在 `videos/<id>/alignment.json` 中写入对齐检查结果：

```json
{
  "script_hash_at_predict": "<sha256 from prediction file>",
  "script_hash_at_shoot": "<sha256 of current script>",
  "hash_match": true,
  "structure_drift": false,
  "alignment_level": "fully_aligned",
  "checked_at": "<ISO 8601 timestamp>"
}
```

---

## 改稿偏离度监控

> v2 脚本与 v1 的偏离度不仅是触发 v2 重判的条件，更是 rubric 升级和用户创作 pattern 分析的核心数据。本段定义偏离度的持续监控规则。

### 偏离度分级与处理规则

| 偏离度区间 | 等级 | 标记 | 处理规则 |
|------------|------|------|---------|
| 0% | 一致 | `consistent` | 不触发 v2，直接进 Phase 4 |
| 1-9% | 微调 | `minor_edit` | 不触发 v2，记录偏离度供 rubric 分析 |
| 10-29% | 轻改 | `light_edit` | 询问用户是否 v2，默认不触发；记录 `light_edit` 标记 |
| 30-59% | 中改 | `significant_edit` | 默认触发 v2 重判，用户可覆盖；yang-retro 权重 ×1.5 |
| ≥60% | 大改 | `major_rewrite` | 建议走 _redo 流程；若用户坚持，强制触发 v2；yang-retro 权重 ×2 |

### 偏离度趋势监控

yang-status 看板须展示**改稿偏离度趋势**：

- 计算最近 N 次拍摄的平均偏离度（`avg_script_diff_pct`）
- 趋势判定：
  - `avg_script_diff_pct < 10%` → "创作稳定，脚本执行力强"
  - `avg_script_diff_pct 10-30%` → "适度改稿，注意监控"
  - `avg_script_diff_pct > 30%` → "⚠️ 改稿频繁，建议分析原因：脚本质量不足？还是即兴偏好？"

### 偏离度与 rubric 校准关联

- `major_rewrite` 的 v1→v2 预测偏差是 rubric 升级的高价值证据（权重 ×2）
- `minor_edit` 的偏差视为噪声（权重 ×0.5）
- 连续 3 次 `significant_edit` 或 `major_rewrite` → 触发 yang-bump 评估，提示"改稿偏离度持续偏高，rubric 可能需要校准"
- 改稿方向分析：统计 v2 相对 v1 各维度的变化方向（ER↑/HP↓/...），作为 rubric 维度权重的调整信号

---

## 拍摄后二次预测触发条件

> 拍摄完成后，以下条件满足时须重新运行 yang-predict（v2 模式），确保预测与实际拍摄内容对齐。

### 自动触发条件

| # | 触发条件 | 检测方式 | 触发动作 |
|---|---------|---------|---------|
| 1 | 脚本 diff ≥ 30% | Phase 3 的 diff 计算结果 | 自动调用 `/yang-predict — mode: v2` |
| 2 | 结构节点变更 | Hook/转折/结尾任一段落被删除或大幅修改 | 自动调用 `/yang-predict — mode: v2` |
| 3 | 时长显著偏移 | 实际拍摄时长与脚本预估时长偏差 > ±30% | 建议用户确认是否 v2 |
| 4 | 情绪曲线偏移 | 实际拍摄的情绪节奏与脚本预期不一致（用户自报） | 建议用户确认是否 v2 |
| 5 | 用户主动要求 | 用户在 Phase 2 选择 b 路径 | 按用户意愿触发 v2 |

### 不触发 v2 的条件

| 条件 | 原因 |
|------|------|
| diff < 10% 且无结构变更 | 改动在噪声范围内，v1 预测仍有效 |
| 用户选择 a 路径（一致） | 用户确认按草稿拍摄，无需重判 |
| `script_lost`（即兴拍摄无稿） | 无实际稿可对比，v2 无法执行 |

### 二次预测执行规范

触发 v2 时须遵守以下规范：

1. **v2 预测必须 append**：在原 prediction 文件追加 `## 预测 v2` 段，不得覆盖 v1
2. **v2 输入为实际拍摄稿**：`videos/<id>/script.md` 作为 v2 的输入，而非 `scripts/<id>.md`
3. **v2 须标注触发原因**：在 `## 预测 v2` 段写入 `v2_trigger_reason` 字段（如 `"script_diff_42pct"` / `"structure_drift"` / `"user_request"`）
4. **v2 须记录 diff 摘要**：写入 `v2_diff_summary` 字段，包含 `diff_pct`、`added_lines`、`removed_lines`、`edit_severity`
5. **yang-retro 读 v2**：`v2_prediction_written: true` 时，复盘以 v2 为准；`false` 时以 v1 为准
