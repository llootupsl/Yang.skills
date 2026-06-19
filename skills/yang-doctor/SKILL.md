---
name: yang-doctor
version: "2.0"
description: 系统健康诊断。对 Yang.skills 项目进行全量诊断检查，覆盖状态文件完整性、知识库健康度、迁移记录、schema 对齐度和文档膨胀检测。支持 --fix 自动修复。触发词："体检"/"doctor"/"诊断"/"系统检查"/"健康检查"/"跑一下诊断"/"检查一下系统"。
tags: [诊断, 修复, 健康检查, 系统维护]
author: 阿洋
argument-hint: "[--fix]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob
---

# yang-doctor · 系统健康诊断

## ⚡ 紧凑核心规则

**搜索意图健康**：检查adapters/search-intent/是否可用+最近一次Channel E拉取是否在7天内+种子词是否过于宽泛。

**Humanness Score健康**：检查最近5次润色的Humanness Score平均值——若<50→提示"活人感评分偏低，建议重点润色H-OPEN和H-SPEC维度"。

> **前置条件**：项目已 init（`.yang-state.json` 存在）
>
> **产生**：诊断报告（控制台输出）+ 可选 `--fix` 自动修复
>
> **只读（默认）**：不加 `--fix` 时不产生任何文件写入

## 前置条件检查

> [前置条件] 运行本 skill 前检查 `.yang-state.json` 是否存在

---

## 失败模式编码

| 编码 | 名称 | 描述 |
|------|------|------|
| DOC-E01 | STATE_MISSING | `.yang-state.json` 不存在，无法执行诊断 |
| DOC-E02 | STATE_CORRUPT | state 文件 JSON 解析失败 |
| DOC-E03 | SCHEMA_MISMATCH | schema_version 与 registry 不对齐（MAJOR 不兼容） |
| DOC-E04 | KNOWLEDGE_A_MISSING | 知识库A 文件缺失或占位，依赖 skill 全局降级 |
| DOC-E05 | PROTOCOLS_INCOMPLETE | shared-protocols/ 核心协议文件缺失 |
| DOC-E06 | FIX_PERMISSION_DENIED | --fix 模式下写文件权限不足 |

---

## 反例黑名单

1. **禁止在无 --fix 参数时写入任何文件**：只读诊断模式不得修改任何项目文件
2. **禁止跳过任何诊断项**：14 项诊断必须逐项执行并输出结果，不得因某项失败而跳过后续
3. **禁止自动修复知识库A缺失**：知识库A内容缺失只能提示人工处理，不得生成占位内容
4. **禁止在 state 损坏时执行 --fix**：必须先人工修复 JSON 损坏，--fix 不得在损坏文件上操作
5. **禁止覆盖已有备份**：创建备份时若 .bak 文件已存在，必须追加时间戳而非覆盖
6. **禁止静默降级诊断精度**：知识库A降级时必须在诊断报告中明确标注降级范围
7. **禁止忽略 MAJOR 版本不兼容**：SCHEMA_MISMATCH (MAJOR) 必须标记为🔴严重，不得降级为⚠️

---

## 工作流

读取 `.yang-state.json`:
- 若不存在 → 拒绝执行："请先运行 yang-init 初始化项目"
- 若存在 → 解析 JSON，记录 `schema_version`
- 若 `in_progress_session` 不为 null → 警告并发冲突（soft check，不强制拒绝）
- 检查通过后，正常执行

解析 `--fix` 参数：
- 若命令行包含 `--fix` → 启用自动修复模式
- 否则 → 只读诊断模式

---

## 工作流

### Step 1: 全量扫描

> 🔍 **检查点 CP-1**：确认 `.yang-state.json` 存在且 JSON 合法，否则输出 DOC-E01/DOC-E02 并终止

按以下 14 项诊断逐项执行，每项输出状态（✅ 通过 / ⚠️ 警告 / 🔴 严重）和详情。

---

## 诊断项 1: `.yang-state.json` 文件存在性

检查 `.yang-state.json` 是否存在于项目根目录。

- 存在 + JSON 合法 → ✅
- 存在但 JSON 解析失败 → 🔴 "state file 损坏，建议备份后重新 init"
- 不存在 → 🔴 "未初始化，请先运行 yang-init"

## 诊断项 2: `schema_version` 与 registry 对齐

读取 `.yang-state.json` 的 `schema_version`，与 `migrations/registry.md` 的 `LATEST_SCHEMA` 对比。

- 版本匹配 → ✅
- 版本落后（MINOR）→ ⚠️ "schema 版本落后（当前: {current}, 最新: {latest}），建议运行 yang-migrate（非阻塞）"
- 版本落后（MAJOR）→ 🔴 "MAJOR 版本不兼容（当前: {current}, 最新: {latest}），必须运行 yang-migrate"
- `migrations/registry.md` 不存在 → ⚠️ "迁移注册表缺失，无法验证版本兼容性"

## 诊断项 3: 必填字段完整性

逐字段检查 `.yang-state.json` 是否包含 v2.1 schema 定义的所有字段（按 [state-management.md](../../shared-protocols/state-management.md) 的完整 schema 核对）。

必填字段清单：
- 元数据：`schema_version`, `skill_version`, `initialized_at`
- 模式配置：`rubric_version`, `content_form`, `typical_duration_seconds`, `target_publish_cadence_days`, `rubric_form_mismatch`, `benchmark_status`, `benchmark_name`, `benchmark_sample_count`, `baseline_plays`
- 累计计数：`calibration_samples`, `calibration_samples_at_last_bump`
- 数据配置：`data_collection`, `pool_status`, `data_layer`, `hooks_installed`, `enabled_trend_sources`, `enabled_perf_adapters`
- 时间戳：`last_bump_at`, `last_bump_self_audited`, `last_published_at`, `last_published_file`, `last_retro_at`, `last_trends_run_at`, `last_trends_added_count`, `last_prediction_self_scored`, `last_self_scored_at`
- v2.0 新增：`persona_exists`, `persona_version`, `persona_name`, `persona_history`, `competitor_count`, `calibration_records`
- 列表队列：`consecutive_directional_errors`, `pending_retros`, `shoots`
- 会话：`in_progress_session`

- 所有字段齐全 → ✅
- 缺失 ≤ 3 个非关键字段 → ⚠️ 列出缺失字段名
- 缺失 > 3 个或缺失关键字段 → 🔴 列出缺失字段名

## 诊断项 4: `shoots[]` 条目字段完整性

遍历 `.yang-state.json` 的 `shoots[]` 数组中每条记录，检查是否包含完整字段：

- 必需字段：`video_folder`, `prediction_file`, `shot_at`, `ad_hoc`
- v1.2 扩展字段：`scripts_path`, `script_consistency`, `script_diff_pct`, `v2_prediction_written`, `script_hash_at_shoot`

- 所有条目字段齐全 → ✅
- 部分条目缺少 v1.2 扩展字段（但含所有必需字段）→ ⚠️ "N 条 shoot 记录缺少 v1.2 扩展字段（script_consistency/v2_prediction_written 等），yang-retro 可能无法正确判断 v2 预测重判"
- 条目缺少必需字段 → 🔴 列出问题条目

## 诊断项 5: `calibration_records` 结构一致性

遍历 `.yang-state.json` 的 `calibration_records[]` 数组中每条记录，检查结构：

- 每项必须包含：`graded_scores`（含 hook/emotion/structure/copywriting/persona/virality/rhythm 7 维）、`actual_plays`、`bucket`、`scored_by`、`scored_at`
- `graded_scores` 中每维必须包含 `value` 和 `justification`

- 所有记录结构一致 → ✅
- 部分记录缺少可选字段（如 `justification`）→ ⚠️
- 记录缺少必需字段 → 🔴

## 诊断项 6: `shared-protocols/` 目录完整性

检查 `shared-protocols/` 目录下预期文件是否存在：

- 核心协议文件：`state-management.md`, `blind-prediction-protocol.md`, `migration-protocol.md`, `cross-agent-audit.md`
- 辅助协议文件：`constants.md`, `pipeline-state.md`, `parallel-subagent.md`, `candidate-schema.md`, `prediction-anatomy.md`, `observation-lifecycle.md`, `data-source-routing.md`, `hypothesis-prediction-bridge.md`, `cadence-protocol.md`, `bump-validation-protocol.md`

- 核心协议全部存在 → ✅
- 核心协议缺失 → 🔴 列出缺失文件
- 辅助协议缺失 → ⚠️ 列出缺失文件

## 诊断项 7: 知识库A 内容完整性

读取 `knowledge/ansir/SKILL.md`，检查文件大小和内容：

- 文件大小 ≥ 10KB且含 "安先生" 关键词 → ✅
- 文件大小 ≥ 1KB 但 < 10KB → ⚠️ "知识库A 内容偏少（{N} KB），可能为部分蒸馏状态"
- 文件大小 < 1KB → 🔴 列出受影响 skill 清单：

  ```
  🔴 知识库A 占位状态（{N} 字节）
  受影响 skill（均降级运行）：
    · yang-polish —— L4 活人感终审降级
    · yang-score —— 评分锚定维度从A降级为B/C混合
    · yang-emotion-curve —— 情绪理论降级为通用ER-Curve
    · yang-hook-factory —— 钩子分类降级为C的开篇36计
    · yang-status —— 数据解读降级为简化数值对比
    · yang-bump —— bump 评估缺少A的结构化数据参考
  ```

- 文件不存在 → 🔴 "知识库A 文件缺失，所有依赖 skill 均降级运行。请运行 '蒸馏 ansir' 创建知识库"

## 诊断项 8: `migrations/` 文件完整性

检查 `migrations/` 目录下的预期文件：

- 预期迁移文件（5个）：`1.0-to-1.1.md`, `1.1-to-1.2.md`, `1.2-to-1.3.md`, `1.3-to-1.4.md`, `1.4-to-v2.0.md`
- 注册表文件（1个）：`registry.md`

- 5 迁移 + 1 registry 全部存在 → ✅
- 注册表缺失 → 🔴 "migrations/registry.md 缺失，版本追踪不可用"
- 部分迁移文件缺失 → ⚠️ 列出缺失文件

## 诊断项 9: state 字段与 schema 对齐度

逐字段比对 `.yang-state.json` 的实际字段值与 [state-management.md](../../shared-protocols/state-management.md) 定义的语义约束：

检查项：
| 字段 | 约束 | 比对方式 |
|------|------|---------|
| `schema_version` | 格式 `v{major}.{minor}` | 正则 `^v\d+\.\d+$` |
| `rubric_version` | 格式 `v{major}` 或 `v{major}.{minor}` | 正则 |
| `calibration_samples` | ≥ 0 整数 | 类型检查 |
| `calibration_samples_at_last_bump` | ≥ 0 整数，≤ `calibration_samples` | 比较 |
| `content_form` | 枚举值之一 | `["opinion-video","long-essay","short-text","podcast","other","mixed"]` |
| `benchmark_status` | 枚举值之一 | `["none","imported","pending"]` |
| `data_collection` | 枚举值之一 | `["manual","adapter"]` |
| `pool_status` | 枚举值之一 | `["none","markdown","notion","sqlite"]` |
| `data_layer` | 枚举值之一 | `["markdown","sqlite"]` |

- 所有字段对齐 → ✅
- 字段值超出枚举范围 → ⚠️ 列出异常字段和当前值
- 字段类型错误 → 🔴 列出错误字段

## 诊断项 10: `state.shoots` 条目字段完整性

此诊断项与诊断项 4 互补，额外检查 shoots 的语义约束：

- `shot_at` 是否为合法 ISO 8601 时间戳
- `ad_hoc` 是否为 bool
- 若 `scripts_path` 非 null → 对应文件是否存在
- 若 `prediction_file` 非 null → 对应文件是否存在
- `script_consistency` 是否为合法枚举值（`"consistent"` / `"modified"` / `"rewritten"`）

- 所有条目语义正确 → ✅
- 语义违规 → ⚠️ 列出问题条目和违规项

## 诊断项 11: `rubric_notes.md` 膨胀检测

检查 `rubric_notes.md` 文件在一段时间内的膨胀情况：

- 读取当前文件行数和字节数
- 检查是否存在 `rubric_notes.md.bak` 备份文件（由 `--fix` 或 yang-bump 自动创建）
- 若有备份 → 计算净增幅（当前行数 - 备份行数）
  - 净增幅 ≤ 250 行 → ✅
  - 净增幅 > 250 行 → 🔴 "rubric_notes.md 单次 bump 净增幅 {N} 行（超过 250 行阈值）。可能原因：重复规则堆积 / 未清理废弃维度。建议运行 yang-bump 进行规则合并和废弃清理"
- 若无备份 → ⚠️ "缺少对比基线，无法判断膨胀程度。下次 bump 时将自动创建备份"

## 诊断项 12: `script_patterns.md` 重复检测

若项目存在 `script_patterns.md` 文件，检查其中是否存在重复的模式定义：

- 读取 `script_patterns.md`，按段落/标题拆分
- 检测是否有高度相似（编辑距离 < 20% 或 文本相似度 > 80%）的模式块
  - 无重复 → ✅
  - 发现重复 → ⚠️ "发现 {N} 对疑似重复的模式定义，建议合并或删除冗余项"，列出重复对
- 文件不存在 → ⚪ 跳过（标注"N/A - script_patterns.md 不存在"）

## 诊断项 13: `benchmark.md` 活跃度检测

若项目存在 `benchmark.md` 文件，检查其活跃度：

- 读取 `benchmark.md` 的最后修改时间
- 若最后修改距今天数 > 180（6个月）→ ⚠️ "benchmark.md 已 {N} 天未更新（超过 6 个月）。对标数据可能严重过时。建议：更新对标数据或运行 `yang-learn-from --refresh`；若已不再使用对标功能，可安全删除此文件"
- 若最后修改 ≤ 180 天 → ✅
- 文件不存在 → ⚪ 跳过（标注"N/A - benchmark.md 不存在"）

## 诊断项 14: 校准收敛曲线可用性

检查 `tools/score-curve.py` 是否存在，并判断是否有足够的校准数据支持收敛分析。

- `tools/score-curve.py` 不存在 → ⚪ 跳过（标注"N/A - score-curve.py 缺失，可能 Yang.skills 版本不完整"）
- `tools/score-curve.py` 存在 + `calibration_records` 条数 ≥ 5 → ✅ 提示："校准池有 {N} 条记录，建议运行 `python tools/score-curve.py` 查看预测精度收敛曲线"
- `tools/score-curve.py` 存在 + `calibration_records` 条数 < 5 → ⚠️ "校准样本不足（{N}/5），收敛曲线需 ≥5 条记录才有参考价值"
- `calibration_records` 为空或不存在 → ⚪ 跳过（标注"N/A - 尚无校准记录"）

---

### Step 2: 汇总诊断报告

> 🔍 **检查点 CP-2**：14 项诊断全部执行完毕，确认无遗漏项

按严重程度排序输出：

```
┌────────────────────────────────────────────┐
│        Yang.skills · 系统健康诊断报告          │
├────────────────────────────────────────────┤
│                                            │
│  🔴 严重: {N} 项                            │
│  ⚠️ 警告: {N} 项                            │
│  ✅ 通过: {N} 项                            │
│  ⚪ 跳过: {N} 项                            │
│                                            │
│  诊断汇总:                                  │
│  [按编号列出各诊断项状态 + 概要]               │
│                                            │
│  修复建议:                                  │
│  1. [最高优先级修复项]                       │
│  2. ...                                    │
│                                            │
│  输入 '--fix' 自动修复可自动处理的问题。        │
│                                            │
└────────────────────────────────────────────┘
```

---

## --fix 模式

当用户传入 `--fix` 参数时，在诊断报告后追加自动修复流程。

> 🔍 **检查点 CP-3**：确认 --fix 模式已启用，验证写入权限，否则输出 DOC-E06

### 可自动修复的问题

**FIX-1: shared-references → shared-protocols 路径修正**

扫描所有 `skills/*/SKILL.md` 文件中的 `shared-references/` 引用：
- 用 Grep 查找所有包含 `shared-references/` 的文件
- 对每个匹配项，替换为 `shared-protocols/`
- 记录修复日志：文件名 + 替换行号

**FIX-2: state 字段自动补齐**

对诊断项 3 发现的缺失字段，自动写入默认值：
- 读取 `.yang-state.json`
- 创建备份：`.yang-state.json.bak.{timestamp}`
- 按 [state-management.md](../../shared-protocols/state-management.md) 的默认值规则补齐所有缺失字段
- 原子写入（.tmp → rename）
- 记录修复日志：备份路径 + 补齐字段列表

**FIX-3: rubric_notes.md 备份创建**

若诊断项 11 提示"缺少对比基线"：
- 自动创建 `rubric_notes.md.bak` 备份（当前内容的完整副本）

**FIX-4: Migration 注册表引用修正**

若 `migrations/registry.md` 中的文件引用指向不存在的文件：
- 从实际目录中移除无效引用
- 添加缺失的迁移文件记录

### 不可自动修复（需人工介入）

- 🔴 知识库A 内容缺失 → 提示"请运行 '蒸馏 ansir' 手动创建知识库"
- 🔴 state file JSON 损坏 → 提示"请手动修复或备份后重新 init"
- 🔴 核心 shared-protocols 文件缺失 → 提示"请从 Yang.skills 原始仓库恢复缺失文件"
- ⚠️ benchmark.md 过期 → 提示"请手动更新对标数据"

### 修复报告输出

> 🔍 **检查点 CP-4**：验证所有修复操作原子完成，备份文件已创建，无残留 .tmp 文件
> 🔍 **检查点 CP-5**：修复后重新运行关键诊断项，确认修复有效

```
┌────────────────────────────────────────────┐
│        Yang.skills · 自动修复报告              │
├────────────────────────────────────────────┤
│                                            │
│  备份创建:                                  │
│  · .yang-state.json.bak.20260517_120000    │
│  · rubric_notes.md.bak                     │
│                                            │
│  FIX-1 路径修正:                            │
│  · skills/yang-polish/SKILL.md L18:         │
│    shared-references/ → shared-protocols/   │
│  · skills/yang-score/SKILL.md L12:          │
│    shared-references/ → shared-protocols/   │
│  （共 {N} 处修正）                          │
│                                            │
│  FIX-2 字段补齐:                            │
│  · calibration_samples_at_last_bump → 0    │
│  · persona_history → []                    │
│  （共 {N} 个字段补齐）                       │
│                                            │
│  ⚠️ 以下问题需人工处理：                      │
│  · [不可自动修复的问题列表]                    │
│                                            │
└────────────────────────────────────────────┘
```

---

### 知识库A 状态检测

读取 `knowledge/ansir/SKILL.md`:
- 若文件大小 < 1KB → 判定为占位状态
  → 诊断报告顶部标注 "A-占位（全局降级）"
  → 诊断项 7 直接标记为 🔴
- 若 ≥ 1KB → 正常加载

**降级行为（yang-doctor）**：诊断项 7 的精细化程度降低
- 当A降级时：诊断项 7 仅做存在性检查（文件是否存在 + 大小），不做内容深度评估
- 诊断项 7 的详细内容分析（关键词匹配、章节完整性检查）仅在 A 正常加载时执行

---

## 知识库依赖

本 skill 在诊断过程中引用以下知识库内容：

- 知识库A：结构精细化三要素——用于诊断项 7 的知识库A 内容深度评估参考 `[来源：A-结构]`

---

## 错误处理

| 场景 | 行为 |
|------|------|
| `.yang-state.json` 不存在 | 拒绝执行："请先运行 yang-init 初始化项目" |
| `knowledge/ansir/` 目录不存在 | 诊断项 7 标记为 "A-目录缺失"，其他诊断正常执行 |
| `migrations/` 目录不存在 | 诊断项 8 标记为 🔴，其他诊断正常执行 |
| `shared-protocols/` 目录不存在 | 诊断项 6 标记为 🔴，其他诊断正常执行 |
| `--fix` 模式下写文件权限不足 | 报告"无法写入文件，请检查权限"，跳过该修复项继续执行其余修复 |

---

## 量化标准：系统健康度评分

诊断报告输出后，附加**系统健康度评分**，满分 100 分，按诊断项结果加权计算。

| 诊断项 | 权重 | 评分规则 |
|--------|------|---------|
| 1. state 文件存在性 | 15% | ✅=15, ⚠️=5, 🔴=0 |
| 2. schema 对齐 | 10% | ✅=10, ⚠️=5, 🔴=0 |
| 3. 必填字段完整性 | 10% | ✅=10, ⚠️=5, 🔴=0 |
| 6. shared-protocols 完整性 | 10% | ✅=10, ⚠️=5, 🔴=0 |
| 7. 知识库A 完整性 | 15% | ✅=15, ⚠️=5, 🔴=0 |
| 8. migrations 完整性 | 5% | ✅=5, ⚠️=2, 🔴=0 |
| 9. state 字段语义约束 | 10% | ✅=10, ⚠️=5, 🔴=0 |
| 11. rubric_notes 膨胀 | 5% | ✅=5, ⚠️=2, 🔴=0 |
| 其余诊断项（各 5%） | 20% | ✅=5, ⚠️=2, 🔴=0 / 项 |

**评分等级**：
- ≥ 85：🟢 健康
- 60-84：🟡 亚健康（建议修复⚠️项）
- < 60：🔴 不健康（必须修复🔴项）

---

## 自动巡检规则

> 定期自动检查系统健康指标，在问题恶化前预警。本段定义巡检的频率、指标和阈值。

### 巡检频率

| 巡检类型 | 频率 | 触发方式 |
|---------|------|---------|
| 轻量巡检 | 每次会话启动时 | SessionStart hook 自动触发 |
| 标准巡检 | 每周一次 | Schedule 定时任务 |
| 深度巡检 | 每次 yang-bump 前 | bump 流程内置 |
| 紧急巡检 | 用户主动触发 | "体检"/"doctor" 触发词 |

### 轻量巡检指标（SessionStart）

| # | 指标 | 检查方式 | 告警阈值 | 告警级别 |
|---|------|---------|---------|---------|
| 1 | `.yang-state.json` 存在性 | 文件存在检查 | 不存在 | 🔴 |
| 2 | `schema_version` 与 registry 对齐 | 版本号比对 | MAJOR 不匹配 | 🔴 |
| 3 | buffer 颜色 | 计算 shoots.length / cadence | 🔴 或 🔵 | ⚠️ |
| 4 | 待复盘超期项 | `pending_retros` 中超过 T+7 的条目数 | > 0 | ⚠️ |
| 5 | 知识库A 状态 | 文件大小检查 | < 1KB | 🔴 |

### 标准巡检指标（每周）

| # | 指标 | 检查方式 | 告警阈值 | 告警级别 |
|---|------|---------|---------|---------|
| 1 | 全部 14 项诊断 | 完整 yang-doctor 流程 | 见各诊断项 | 按诊断项 |
| 2 | 校准样本增长 | `calibration_samples` 增量 | 连续 2 周无增长 | ⚠️ |
| 3 | rubric_notes 膨胀 | 行数增量 vs 上周 | 单周增 > 100 行 | ⚠️ |
| 4 | 候选池健康度 | candidates.md 条目数 + 打分率 | 打分率 < 50% | ⚠️ |
| 5 | 改稿偏离度趋势 | 最近 5 次平均 diff_pct | > 30% | ⚠️ |
| 6 | 预测精度趋势 | 最近 5 次复盘的桶命中率 | < 40% | 🔴 |

### 巡检结果输出格式

```
🔄 自动巡检报告（{轻量/标准}）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ 巡检时间：{ISO timestamp}
📊 健康度：{score}/100 ({等级})

🔴 严重：{N} 项
  · {指标名}: {具体值}（阈值: {阈值}）

⚠️ 警告：{N} 项
  · {指标名}: {具体值}（阈值: {阈值}）

✅ 正常：{N} 项

建议操作：
  1. {最高优先级建议}
  2. {次优先级建议}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 诊断报告模板

> 标准化的诊断报告输出格式，确保诊断结果可追溯、可对比、可操作。

### 报告结构

```markdown
# Yang.skills 系统健康诊断报告

## 基本信息
- 诊断时间：{ISO 8601 timestamp}
- 诊断类型：{手动/轻量巡检/标准巡检/深度巡检}
- 触发方式：{用户触发/自动触发/bump前置}
- 项目路径：{project_root}
- schema 版本：{current} / 最新：{latest}
- rubric 版本：{rubric_version}

## 健康度总览
- 综合评分：{score}/100
- 健康等级：{🟢 健康 / 🟡 亚健康 / 🔴 不健康}
- 🔴 严重：{N} 项
- ⚠️ 警告：{N} 项
- ✅ 通过：{N} 项
- ⚪ 跳过：{N} 项

## 诊断明细

### 🔴 严重项
| # | 诊断项 | 编码 | 现状 | 阈值 | 修复建议 |
|---|--------|------|------|------|---------|
| 1 | {名称} | {编码} | {当前值} | {期望值} | {建议} |

### ⚠️ 警告项
| # | 诊断项 | 编码 | 现状 | 阈值 | 修复建议 |
|---|--------|------|------|------|---------|
| 1 | {名称} | {编码} | {当前值} | {期望值} | {建议} |

### ✅ 通过项
| # | 诊断项 | 当前值 |
|---|--------|--------|
| 1 | {名称} | {值} |

## 关键指标趋势（与上次诊断对比）
| 指标 | 上次 | 本次 | 变化 |
|------|------|------|------|
| 健康度评分 | {N} | {N} | {↑/↓/→} |
| 校准样本数 | {N} | {N} | {↑/↓/→} |
| buffer 状态 | {颜色} | {颜色} | {变化} |

## 修复优先级排序
1. 🔴 {最高优先级修复项} — {影响范围}
2. 🔴 {次高优先级修复项} — {影响范围}
3. ⚠️ {警告项} — {影响范围}

## 自动修复建议
可自动修复：{N} 项（运行 `yang-doctor --fix`）
需人工介入：{N} 项

---
报告生成：yang-doctor v2.0
```

### 报告存档

- 每次诊断报告写入 `logs/doctor-{YYYY-MM-DD-HHMMSS}.md`
- 保留最近 10 份报告，超出自动清理最旧的
- yang-status 可引用最新报告的健康度评分

---

## 常见问题修复手册

> 8-10 个系统运行中最常见的问题及其修复步骤，供 yang-doctor --fix 和人工参考。

### 问题 1：state 文件 JSON 损坏

**症状**：诊断项 1 报 🔴，`JSON.parse()` 失败
**原因**：手动编辑 state 文件时引入语法错误，或并发写入导致截断
**修复步骤**：
1. 检查 `.yang-state.json.bak.*` 备份是否存在
2. 若备份存在 → 验证备份 JSON 合法性 → 替换损坏文件
3. 若备份不存在 → 尝试手动定位语法错误（常见：末尾逗号、未转义引号）
4. 无法修复 → 运行 `yang-init` 重建，从 `predictions/*.md` 和 `videos/` 目录恢复关键数据
5. 修复后运行 `yang-doctor` 验证

### 问题 2：知识库A 占位/缺失

**症状**：诊断项 7 报 🔴，文件 < 1KB 或不存在
**原因**：未执行知识库蒸馏，或蒸馏中断
**修复步骤**：
1. 确认 `knowledge/ansir/` 目录存在
2. 若目录不存在 → 创建目录结构
3. 运行知识库蒸馏流程（"蒸馏 ansir"）
4. 蒸馏完成后验证文件大小 ≥ 10KB
5. 重新运行 `yang-doctor` 确认降级状态解除

### 问题 3：schema 版本不兼容（MAJOR）

**症状**：诊断项 2 报 🔴，MAJOR 版本不匹配
**原因**：Yang.skills 升级后未运行迁移
**修复步骤**：
1. 确认当前版本和目标版本
2. 运行 `yang-migrate --from {current} --to {latest}`
3. 迁移完成后运行 `yang-doctor` 验证
4. 若迁移失败 → 检查备份文件 → 按回滚操作手册处理

### 问题 4：shared-protocols 核心文件缺失

**症状**：诊断项 6 报 🔴，核心协议文件不存在
**原因**：项目文件被误删或 git 操作导致文件丢失
**修复步骤**：
1. 确认缺失的文件列表
2. 从 Yang.skills 原始仓库恢复缺失文件
3. 若无法访问原始仓库 → 从 `shared-references/` 旧路径查找（yang-doctor --fix FIX-1 可自动修正路径引用）
4. 恢复后验证所有 skill 的路径引用正确

### 问题 5：buffer 计数不一致

**症状**：`buffer_available` 与 `state.shoots.length` 不匹配
**原因**：并发操作或异常中断导致 shoots 队列与 buffer 计数不同步
**修复步骤**：
1. 读取 `state.shoots` 数组，计算实际长度
2. 与 `buffer_available` 对比
3. 若不一致 → 以 `shoots.length` 为准，重算 `buffer_available`
4. 检查是否有已发布但未从 shoots 移除的条目（与 `predictions/*.md` 的发布信息交叉验证）
5. 修正后运行 `yang-doctor` 验证

### 问题 6：rubric_notes.md 膨胀

**症状**：诊断项 11 报 🔴，单次 bump 净增幅 > 250 行
**原因**：bump 时规则堆积、未清理废弃维度、重复规则未合并
**修复步骤**：
1. 对比 `rubric_notes.md` 与 `rubric_notes.md.bak`，识别新增内容
2. 检查是否存在重复规则（编辑距离 < 20% 的段落）
3. 检查是否有废弃维度（引用的维度在当前 rubric 中不存在）
4. 合并重复规则、删除废弃维度
5. 运行 `yang-bump` 时确保启用规则合并和废弃清理

### 问题 7：候选池打分率过低

**症状**：candidates.md 中 composite=null 的条目占比 > 50%
**原因**：新增候选未及时打分，或 /yang-trends 批量导入未触发打分
**修复步骤**：
1. 统计未打分条目数量
2. 运行 `/yang-score` 逐条打分（或批量模式）
3. 若条目过多 → 优先对 tier1 条目打分
4. 打分完成后验证打分率 ≥ 80%

### 问题 8：预测精度持续偏低

**症状**：最近 5 次复盘桶命中率 < 40%
**原因**：rubric 维度权重与实际表现不匹配，或校准样本不足
**修复步骤**：
1. 检查 `calibration_samples` 是否达到 bump 阈值
2. 若达到 → 运行 `yang-bump` 校准 rubric
3. 若未达到 → 积累更多校准样本（至少 5 条复盘记录）
4. 检查是否有维度权重严重偏移（某维度预测偏差 > 2 级）
5. 手动调整维度权重或运行 `yang-bump` 重新校准

### 问题 9：人设档案与润色效果脱节

**症状**：yang-polish 润色后人设特征不明显，或饱和度 < 50%
**原因**：人设档案内容泛化、选填项缺失、长期未更新
**修复步骤**：
1. 运行 `yang-persona --show` 查看当前饱和度
2. 若饱和度 < 50% → 引导补充选填项和故事细节
3. 若饱和度 ≥ 50% 但润色效果差 → 检查人设与内容类型的匹配度
4. 更新人设档案后运行 `yang-polish` 重新润色验证

### 问题 10：迁移后功能异常

**症状**：yang-migrate 完成后部分 skill 报错或行为异常
**原因**：迁移步骤遗漏、新增字段默认值不正确、字段类型错误
**修复步骤**：
1. 运行 `yang-doctor` 检查所有诊断项
2. 重点检查诊断项 3（必填字段完整性）和诊断项 9（字段语义约束）
3. 对比迁移前备份，确认无字段丢失
4. 若发现字段缺失 → 运行 `yang-doctor --fix` 自动补齐
5. 若功能仍异常 → 从备份回滚，重新执行迁移