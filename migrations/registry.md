---
name: migrations-registry
description: Yang.skills schema 迁移注册表。记录各版本间的数据/状态/协议迁移方案。
author: 阿洋
---

# Migrations Registry

## LATEST_SCHEMA: v2.2

当前最新 schema 版本。所有 yang-init 新建项目均以此为基准。

## Migration History

| 版本 | state_schema_version | 日期 | 迁移文件 | 类型 | 说明 |
|------|----------------------|------|----------|------|------|
| v2.2 | `"v2.2"` | 2026-06 | [v2.1-to-v2.2.md](v5.1-to-v6.0.md) | MAJOR (CURRENT) | 新增搜索意图适配器(adapters/search-intent/)、活人感量化评分协议(shared-protocols/humanness-score.md)、统一适配器接口(adapters/adapter_base.py + registry.py)、渐进式加载机制(loading-strategy: progressive)、yang-seed从四通道升级为五通道、Humanness Score与yang-score的映射关系。SKILL主版本5.1.0→6.0.0 |
| v2.1 | `"v2.1"` | 2026-05 | — | MINOR | v2.0 补齐字段：content_form / typical_duration_seconds / target_publish_cadence_days / rubric_form_mismatch / benchmark_status / data_collection / pool_status / data_layer / hooks_installed / enabled_trend_sources / consecutive_directional_errors / pending_retros / shoots / calibration_records。所有字段 .get() 兜底，MINOR 兼容 |
| v2.0 | `"v2.0"` | 2026-05 | [1.4-to-v2.0.md](1.4-to-v2.0.md) | MAJOR | 新增 persona_exists / persona_version / persona_name / persona_history / competitor_count / calibration_records |
| v1.4 | `"v1.4"` | 2026-04 | [1.3-to-1.4.md](1.3-to-1.4.md) | MINOR (BREAKING for blind) | rubric 文件拆分：rubric_notes.md → rubric_notes.md + rubric-memo.md；blind channel 隔离增强 |
| v1.3 | `"v1.3"` | 2026-04 | [1.2-to-1.3.md](1.2-to-1.3.md) | MINOR | 新增 last_prediction_self_scored / last_self_scored_at；contamination 跟踪升级 |
| v1.2 | `"v1.2"` | 2026-04 | [1.1-to-1.2.md](1.1-to-1.2.md) | MINOR | shoots[] 项 schema 扩展 5 字段；v2 预测重判触发跟踪 |
| v1.1 | `"v1.1"` | 2026-04 | [1.0-to-1.1.md](1.0-to-1.1.md) | MAJOR | 删除 mode / prediction_complexity / bucket_scheme 硬模式；统一从 calibration_samples 派生 |
| v1.0 | `"v1.0"` | 2026-04 | — | INITIAL | 初始 schema：projects / sessions / predictions / calibrations |

## Migration Chain

```
v1.0 → [1.0-to-1.1] → v1.1 → [1.1-to-1.2] → v1.2 → [1.2-to-1.3] → v1.3 → [1.3-to-1.4] → v1.4 → [1.4-to-v2.0] → v2.0 → (v2.1 MINOR, no migration file needed) → [v2.1-to-v2.2] → v2.2
```

## Upgrade Path

按序迁移，不可跳版：
1. 确认当前 `schema_version`
2. 从匹配的迁移文件开始，依次跑至最新
3. 每次迁移后验证 state file JSON 合法性

v2.0 → v2.1 为 MINOR 升级，所有新增字段使用 `.get(field, default)` 兼容，**无需跑迁移脚本**。yang-status 检测到 `schema_version < "v2.1"` 时提示但非阻塞。

v2.1 → v2.2 为 MAJOR 升级（SKILL主版本5.1.0→6.0.0），需执行迁移脚本 [v5.1-to-v6.0.md](v5.1-to-v6.0.md)。

---

## 版本兼容性矩阵

| 从 ↓ \ 到 → | v1.0 | v1.1 | v1.2 | v1.3 | v1.4 | v2.0 | v2.1 | v2.2 |
|-------------|------|------|------|------|------|------|------|------|
| **v1.0** | — | ⚠️ MAJOR | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **v1.1** | ❌ | — | ✅ MINOR | ❌ | ❌ | ❌ | ❌ | ❌ |
| **v1.2** | ❌ | ❌ | — | ✅ MINOR | ❌ | ❌ | ❌ | ❌ |
| **v1.3** | ❌ | ❌ | ❌ | — | ⚠️ MINOR(BREAKING-blind) | ❌ | ❌ | ❌ |
| **v1.4** | ❌ | ❌ | ❌ | ❌ | — | ⚠️ MAJOR | ❌ | ❌ |
| **v2.0** | ❌ | ❌ | ❌ | ❌ | ❌ | — | ✅ MINOR | ❌ |
| **v2.1** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — | ⚠️ MAJOR |
| **v2.2** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — |

**图例**：
- ✅ = 可直接迁移，无破坏性变更
- ⚠️ = 可迁移但有注意事项（见迁移文件说明）
- ❌ = 不可直接迁移，必须按序逐版升级

**关键规则**：
1. **不可跳版**：v1.0 → v2.0 必须经过 v1.1 → v1.2 → v1.3 → v1.4 → v2.0
2. **不可降级**：矩阵中所有 ❌ 也包含降级场景，降级不在支持范围内
3. **MINOR 无需脚本**：v2.0 → v2.1 这类 MINOR 升级只需更新 `schema_version` 字段
4. **BREAKING 标注**：v1.3 → v1.4 对 blind channel 有破坏性变更，需特别注意

---

## 迁移风险评估模板

每次执行 MAJOR 或 BREAKING MINOR 迁移前，需填写以下风险评估：

```markdown
## 迁移风险评估

**迁移路径**: `<当前版本>` → `<目标版本>`
**迁移文件**: `<迁移文件名>`
**评估日期**: `<YYYY-MM-DD>`
**评估人**: `<姓名/AI>`

### 1. 数据丢失风险

| 风险项 | 等级 | 说明 | 缓解措施 |
|--------|------|------|---------|
| 字段删除 | 高/中/低 | [哪些字段被删除] | [备份策略] |
| 字段语义变更 | 高/中/低 | [哪些字段含义变化] | [兼容处理] |
| 数据结构重组 | 高/中/低 | [结构如何变化] | [迁移脚本处理] |

### 2. 功能兼容性风险

| 风险项 | 等级 | 说明 | 缓解措施 |
|--------|------|------|---------|
| Hook 不兼容 | 高/中/低 | [哪些 hook 受影响] | [hook 更新方案] |
| 命令行参数变更 | 高/中/低 | [哪些命令受影响] | [参数适配] |
| 模板文件格式变更 | 高/中/低 | [哪些模板需更新] | [模板迁移] |

### 3. 回滚方案

- **回滚方式**: [git revert / 手动恢复 state file / 其他]
- **回滚窗口**: 迁移后 `<N>` 小时内可安全回滚
- **回滚数据损失**: [回滚是否会丢失新格式数据]

### 4. 验证清单

- [ ] state file JSON 合法性验证通过
- [ ] yang-status 输出正常
- [ ] 现有 prediction 文件可正常读取
- [ ] 现有 retro 文件可正常追加
- [ ] hook 脚本执行无报错
- [ ] calibration_samples 计数正确

### 5. 总体风险评级

**综合评级**: 🟢 低风险 / 🟡 中风险 / 🔴 高风险

**建议**: [直接执行 / 先在测试项目验证 / 需人工审核后执行]
```

### 风险评级标准

| 评级 | 条件 | 审批要求 |
|------|------|---------|
| 🟢 低风险 | 无字段删除、无语义变更、有自动回滚 | 可自动执行 |
| 🟡 中风险 | 有字段语义变更或结构重组 | 需在测试项目验证后执行 |
| 🔴 高风险 | 有字段删除或 hook 不兼容 | 需人工审核 + 测试项目验证 |

---

## 自动迁移脚本执行规范

### 脚本命名与位置

```
migrations/
├── <from>-to-<to>.md          # 迁移说明文档（已有）
├── <from>-to-<to>.sh          # 迁移脚本（新增）
└── _common.sh                  # 公共函数库（新增）
```

### 公共函数库 `_common.sh` 接口

```bash
# 加载公共函数
source "$(dirname "$0")/_common.sh"

# 可用函数：
# backup_state <project_dir>           → 备份当前 state.json
# validate_json <file>                 → 验证 JSON 合法性
# get_schema_version <project_dir>     → 读取当前 schema_version
# set_schema_version <project_dir> <v> → 写入新 schema_version
# log_migration <from> <to> <status>   → 记录迁移日志
```

### 迁移脚本标准结构

```bash
#!/usr/bin/env bash
set -euo pipefail

SOURCE "$(dirname "$0")/_common.sh"

FROM="v1.4"
TO="v2.0"

# ====== 前置检查 ======
project_dir="${1:?用法: $0 <project_dir>}"
state_file="${project_dir}/state.json"

# 1. 验证当前版本
current=$(get_schema_version "$project_dir")
if [[ "$current" != "$FROM" ]]; then
  echo "❌ 当前版本 $current，期望 $FROM"
  exit 1
fi

# 2. 备份
backup_state "$project_dir"

# ====== 迁移逻辑 ======

# 3. 执行字段变更
# ... 具体迁移操作 ...

# 4. 更新 schema_version
set_schema_version "$project_dir" "$TO"

# ====== 后置验证 ======

# 5. 验证 JSON 合法性
validate_json "$state_file"

# 6. 记录日志
log_migration "$FROM" "$TO" "success"

echo "✅ 迁移完成: $FROM → $TO"
```

### 执行规范

1. **执行前**：
   - 确认当前 `schema_version` 与迁移脚本 `FROM` 一致
   - 确认项目目录下无未提交的 git 变更（避免备份冲突）
   - 确认 `_common.sh` 存在且可执行

2. **执行中**：
   - 脚本必须 `set -euo pipefail`，任何错误立即终止
   - 每个字段变更操作前打印 `echo "→ [操作描述]"`
   - 备份文件命名为 `state.json.bak.<from>-<to>.<timestamp>`

3. **执行后**：
   - 运行 `yang-status` 验证状态正常
   - 检查 `schema_version` 已更新为目标版本
   - 保留备份文件至少 7 天，确认无误后手动删除

4. **失败处理**：
   - 脚本自动从备份恢复：`cp state.json.bak.* state.json`
   - 打印失败原因和恢复状态
   - 记录 `log_migration "$FROM" "$TO" "failed: <reason>"`

5. **批量迁移**：
   - 多个项目需逐个执行，不可并行
   - 每个项目迁移后独立验证
   - 批量迁移脚本示例：`for dir in projects/*/; do bash migrations/1.4-to-v2.0.sh "$dir"; done`

### 迁移日志格式

迁移日志追加到项目目录的 `migration.log`：

```
[YYYY-MM-DD HH:MM:SS] v1.4 → v2.0 | status=success | backup=state.json.bak.v1.4-v2.0.20260515T143022
[YYYY-MM-DD HH:MM:SS] v2.0 → v2.1 | status=success | backup=none(MINOR)
```