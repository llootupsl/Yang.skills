<!-- 作者: 阿洋 -->
# Pipeline State Management（流水线状态管理协议）

被所有 v4 子 skill 引用。`.yang-state.json` 中的流水线字段定义 seed → score → predict → shoot → publish → retro → bump 的阶段间前置依赖与原子写入协议。

---

## §1 协议目的

定义流水线各阶段的前置依赖关系、状态转换规则与并发安全写入协议，防止跳步、死锁与半写损坏。

---

## §2 .yang-state.json 字段契约

```json
{
  "project_name": "string, 项目名称",
  "created_at": "ISO8601 datetime string",
  "in_progress_session": null,
  "buffer_available": "integer >= 0, 可用 buffer 数",
  "buffer_max": "integer > 0, buffer 上限",
  "last_seed_file": "string | null, 最后选题文件路径",
  "last_score_file": "string | null, 最后评分文件路径",
  "last_prediction_file": "string | null, 最后预测文件路径",
  "last_shoot_file": "string | null, 最后拍摄文件路径",
  "last_publish_file": "string | null, 最后发布文件路径",
  "last_retro_file": "string | null, 最后复盘文件路径",
  "calibration_samples": "integer >= 0, 累计校准样本数",
  "bucket_params": {
    "A": { "alpha": "float >= 1", "beta": "float >= 1" },
    "B": { "alpha": "float >= 1", "beta": "float >= 1" },
    "C": { "alpha": "float >= 1", "beta": "float >= 1" },
    "D": { "alpha": "float >= 1", "beta": "float >= 1" }
  },
  "rubric_version": "string, 当前 rubric 版本号",
  "schema_version": "string, 状态文件 schema 版本（v4 为 2.0）",
  "knowledge_index_version": "string | null, GraphRAG 索引版本",
  "knowledge_index_exists": "boolean, GraphRAG 索引是否存在"
}
```

---

## §3 状态转换图

```
     +------------------+
     |      seed        |
     +--------+---------+
              |
              | 前提: last_seed_file not null
              v
     +--------+---------+
     |      score       |
     +--------+---------+
              |
              | 前提: last_score_file not null
              v
     +--------+---------+
     |     predict      |
     +--------+---------+
              |
              | 前提: last_prediction_file not null
              v
     +--------+---------+
     |      shoot       |
     +--------+---------+
              |
              | 前提: last_shoot_file not null
              v
     +--------+---------+
     |     publish      |
     +--------+---------+
              |
              | 前提: last_publish_file not null
              v
     +--------+---------+
     |      retro       |
     +--------+---------+
              |
              | 前提: calibration_samples >= 10
              v
     +--------+---------+
     |       bump       |
     +------------------+
```

---

## §4 拒绝条件表

| Skill | 要求字段 | 拒绝条件 | 错误提示 |
|-------|---------|---------|---------|
| yang-score | last_seed_file or user provides script | both missing | "请先运行 yang-seed 或直接提供脚本内容" |
| yang-predict | last_score_file | null | "请先运行 yang-score" |
| yang-shoot | last_prediction_file | null | "请先运行 yang-predict" |
| yang-publish | last_shoot_file | null | "请先运行 yang-shoot" |
| yang-retro | last_publish_file | null | "请先运行 yang-publish" |
| yang-bump | calibration_samples >= 10 | not met | "校准样本不足（当前: X, 需要: 10），请先积累更多 retro" |
| yang-benchmark | depends (adapter 已安装) | adapter not installed | "未安装 benchmark adapter，请先配置 benchmark-auto 或 learn-from" |

---

## §5 原子写入协议

```
1. Read current .yang-state.json
2. If in_progress_session != null → reject（并发守卫）
3. Set in_progress_session = {skill, started_at, session_id}
4. Write to .yang-state.json.tmp
5. Rename .yang-state.json.tmp → .yang-state.json
```

**正常完成时**：
- 更新对应 `last_*_file` 字段
- 清除 `in_progress_session`（设为 null）
- 原子写入（.tmp → rename）

**出错时**：
- 清除 `in_progress_session`（设为 null），**不得**保持非 null 导致死锁
- **不**更新 `last_*_file`（不产生半成品引用）
- 向用户输出错误日志

---

## §6 异常退出降级

若 skill 在 `in_progress_session` 持有期间崩溃（未执行正常的清理路径），下一次任意 skill 读取 `.yang-state.json` 时检测到 `in_progress_session != null`：

1. 清除 `in_progress_session` 为 null
2. **不**更新任何 `last_*_file` 字段
3. 向用户输出警告："检测到上次 {skill} 会话异常退出，已自动清理。流水线状态未推进，请重新运行 {skill}。"

此降级策略确保：
- 不会产生指向不存在文件的 `last_*_file` 引用
- 不会因残留的 `in_progress_session` 导致后续所有 skill 永久拒绝执行
- 用户可重新运行异常退出的 skill，状态从头推进

---

## §7 Pipeline 模式状态机完整定义

### 状态机模型

Pipeline 模式下，整个产线是一个有限状态机（FSM），每个状态对应流水线的一个阶段：

```
状态机定义：PipelineFSM = (S, Σ, δ, s0, F)

S = 状态集合：
    {IDLE, SEEDING, SCORING, PREDICTING, SHOOTING, PUBLISHING, RETROING, BUMPING}

Σ = 事件集合（触发状态转换的输入）：
    {seed_start, seed_done, score_start, score_done, predict_start, predict_done,
     shoot_start, shoot_done, publish_start, publish_done, retro_start, retro_done,
     bump_start, bump_done, abort, reset}

s0 = 初始状态：IDLE

F = 终止状态集合：{IDLE}（每次完整周期后回到 IDLE）
```

### 状态转换表

| 当前状态 | 事件 | 目标状态 | 前置条件 | state 字段变更 |
|---------|------|---------|---------|--------------|
| IDLE | seed_start | SEEDING | 无 | `in_progress_session = {skill: "yang-seed", ...}` |
| SEEDING | seed_done | IDLE | last_seed_file ≠ null | `last_seed_file = <path>`; `in_progress_session = null` |
| SEEDING | abort | IDLE | — | `in_progress_session = null` |
| IDLE | score_start | SCORING | last_seed_file ≠ null | `in_progress_session = {skill: "yang-score", ...}` |
| SCORING | score_done | IDLE | last_score_file ≠ null | `last_score_file = <path>`; `in_progress_session = null` |
| SCORING | abort | IDLE | — | `in_progress_session = null` |
| IDLE | predict_start | PREDICTING | last_score_file ≠ null | `in_progress_session = {skill: "yang-predict", ...}` |
| PREDICTING | predict_done | IDLE | last_prediction_file ≠ null | `last_prediction_file = <path>`; `in_progress_session = null` |
| PREDICTING | abort | IDLE | — | `in_progress_session = null` |
| IDLE | shoot_start | SHOOTING | last_prediction_file ≠ null | `in_progress_session = {skill: "yang-shoot", ...}` |
| SHOOTING | shoot_done | IDLE | last_shoot_file ≠ null | `last_shoot_file = <path>`; `in_progress_session = null` |
| SHOOTING | abort | IDLE | — | `in_progress_session = null` |
| IDLE | publish_start | PUBLISHING | last_shoot_file ≠ null | `in_progress_session = {skill: "yang-publish", ...}` |
| PUBLISHING | publish_done | IDLE | last_publish_file ≠ null | `last_publish_file = <path>`; `in_progress_session = null` |
| PUBLISHING | abort | IDLE | — | `in_progress_session = null` |
| IDLE | retro_start | RETROING | last_publish_file ≠ null | `in_progress_session = {skill: "yang-retro", ...}` |
| RETROING | retro_done | IDLE | calibration_samples 已 +1 | `last_retro_file = <path>`; `calibration_samples += 1`; `in_progress_session = null` |
| RETROING | abort | IDLE | — | `in_progress_session = null` |
| IDLE | bump_start | BUMPING | calibration_samples ≥ 10 | `in_progress_session = {skill: "yang-bump", ...}` |
| BUMPING | bump_done | IDLE | rubric_version 已升级 | `rubric_version = <new>`; `in_progress_session = null` |
| BUMPING | abort | IDLE | — | `in_progress_session = null` |
| 任意 | reset | IDLE | — | `in_progress_session = null`（不修改 last_*_file） |

### 状态机不变量

| 不变量编号 | 不变量描述 | 验证时机 |
|----------|----------|---------|
| INV-1 | `in_progress_session ≠ null` 当且仅当状态 ≠ IDLE | 每次状态转换后 |
| INV-2 | `last_seed_file` 为 null 时，`last_score_file` 必为 null | 每次写入 state 后 |
| INV-3 | `last_score_file` 为 null 时，`last_prediction_file` 必为 null | 每次写入 state 后 |
| INV-4 | `calibration_samples` 单调递增（除非 bump 重置） | 每次 retro_done 后 |
| INV-5 | 任意时刻最多一个 skill 持有排他锁 | 每次锁获取前 |

### 状态机可视化

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                       IDLE                              │
                    │  (等待用户触发下一个 skill)                               │
                    └──┬────┬────┬────┬────┬────┬────┬────┬──────────────────┘
                       │    │    │    │    │    │    │    │
            seed_start │    │    │    │    │    │    │    │ bump_start
                       ▼    │    │    │    │    │    │    ▼
                  ┌────────┐│    │    │    │    │    │  ┌────────┐
                  │SEEDING ││    │    │    │    │    │  │BUMPING │
                  └───┬────┘│    │    │    │    │    │  └───┬────┘
           seed_done│     ││    │    │    │    │    │bump_done│
                      ▼    ││    │    │    │    │    │     ▼
                    IDLE   ││    │    │    │    │    │   IDLE
              score_start  ││    │    │    │    │    │
                      ▼    ▼▼    │    │    │    │    │
                  ┌─────────────┐│    │    │    │    │
                  │  SCORING    ││    │    │    │    │
                  └──────┬──────┘│    │    │    │    │
           score_done│          │    │    │    │    │
                      ▼          │    │    │    │    │
                    IDLE         │    │    │    │    │
            predict_start       │    │    │    │    │
                      ▼          ▼    │    │    │    │
                  ┌──────────────────┐│    │    │    │
                  │  PREDICTING      ││    │    │    │
                  └──────┬───────────┘│    │    │    │
          predict_done│               │    │    │    │
                      ▼               │    │    │    │
                    IDLE              │    │    │    │
             shoot_start              │    │    │    │
                      ▼               ▼    │    │    │
                  ┌────────────────────────┐│    │    │
                  │  SHOOTING              ││    │    │
                  └──────┬─────────────────┘│    │    │
           shoot_done│                      │    │    │
                      ▼                      │    │    │
                    IDLE                     │    │    │
           publish_start                    │    │    │
                      ▼                      ▼    │    │
                  ┌──────────────────────────────┐│    │
                  │  PUBLISHING                   ││    │
                  └──────┬───────────────────────┘│    │
        publish_done│                                │    │
                      ▼                                │    │
                    IDLE                               │    │
            retro_start                                │    │
                      ▼                                ▼    │
                  ┌────────────────────────────────────────┐│
                  │  RETROING                               ││
                  └──────┬─────────────────────────────────┘│
           retro_done│                                       │
                      ▼                                       ▼
                    IDLE ←────────────────────────────────── IDLE
```

---

## §8 Solo ↔ Pipeline 模式切换的数据迁移清单

### 模式定义

| 模式 | 描述 | 适用场景 |
|------|------|---------|
| **Solo** | 单 Agent 独立完成所有步骤，无跨 Agent 审计 | 个人用户 / 单会话 / 快速迭代 |
| **Pipeline** | 多 Agent 协作，按流水线阶段分工，含跨 Agent 审计 | 团队协作 / 多模型环境 / 高质量要求 |

### Solo → Pipeline 迁移清单

```
Solo → Pipeline 切换
  │
  ├─ Step 1: 状态文件迁移
  │    ├─ 确认 .yang-state.json 中所有 last_*_file 字段有效
  │    ├─ 确认 calibration_samples 准确
  │    ├─ 新增 pipeline_mode = "pipeline" 字段
  │    └─ 新增 pipeline_stage = "idle" 字段
  │
  ├─ Step 2: 审计配置初始化
  │    ├─ 创建 .yang-cache/audit-reports/ 目录
  │    ├─ 初始化审计对配置（见 cross-agent-audit.md）
  │    └─ 设置审计频率 = 每周期
  │
  ├─ Step 3: Agent 角色分配
  │    ├─ Topic Agent: yang-seed, yang-trends, yang-recommend
  │    ├─ Content Agent: yang-score, yang-hook-factory, yang-emotion-curve
  │    ├─ Data Agent: yang-predict, yang-retro, yang-status
  │    └─ Strategy Agent: yang-bump, yang-publish, yang-evolution-bus
  │
  ├─ Step 4: 文件权限调整
  │    ├─ 确认各 Agent 只写入其负责的文件
  │    └─ 确认审计报告目录可被所有 Agent 读取
  │
  ├─ Step 5: 兼容性检查
  │    ├─ 确认 schema_version ≥ 1.4
  │    ├─ 确认所有依赖的共享协议文件存在
  │    └─ 确认 rubric_notes.md 和 rubric-memo.md 已拆分（v1.4 要求）
  │
  └─ Step 6: 切换确认
       ├─ 向用户展示迁移结果摘要
       └─ 用户确认后正式切换
```

### Pipeline → Solo 迁移清单

```
Pipeline → Solo 切换
  │
  ├─ Step 1: 状态文件迁移
  │    ├─ 修改 pipeline_mode = "solo"
  │    ├─ 修改 pipeline_stage = "idle"
  │    └─ 保留所有 last_*_file 字段（Solo 模式仍需引用）
  │
  ├─ Step 2: 审计数据归档
  │    ├─ 将 .yang-cache/audit-reports/ 中的历史报告归档
  │    └─ 保留最近 5 份审计报告供参考
  │
  ├─ Step 3: Agent 角色合并
  │    ├─ 所有 Agent 角色合并为单一 Claude 会话
  │    └─ 清除 Agent 间的文件权限隔离
  │
  ├─ Step 4: 审计暂停
  │    ├─ 设置 audit_enabled = false
  │    └─ 标注"审计已暂停，运行于 Solo 模式"
  │
  └─ Step 5: 切换确认
       ├─ 向用户展示迁移结果摘要
       └─ 提示"Solo 模式下无跨 Agent 审计，输出质量由单一 Agent 保证"
```

### 迁移过程中的数据完整性保障

| 保障项 | 规则 |
|-------|------|
| 迁移原子性 | 迁移过程中如出错，回滚到迁移前的 state |
| 文件不丢失 | 迁移不删除任何已有文件，只新增/修改字段 |
| 版本记录 | 迁移完成后在 `migrations/` 中记录迁移事件 |
| 双向可逆 | Solo ↔ Pipeline 可随时切换，无数据损失 |

### 迁移检查清单

| 检查项 | Solo → Pipeline | Pipeline → Solo |
|-------|----------------|----------------|
| .yang-state.json 完整 | ✅ | ✅ |
| pipeline_mode 字段存在 | 新增 | 修改 |
| 审计目录存在 | 新建 | 归档 |
| Agent 角色已分配 | 新增 | 清除 |
| schema_version ≥ 1.4 | ✅ | ✅ |
| rubric 文件已拆分 | ✅ | — |
| 用户已确认 | ✅ | ✅ |

---

## §9 Pipeline 异常中断的恢复点定义

### 恢复点概念

恢复点（Recovery Point）是 Pipeline 运行过程中的安全快照点。当 Pipeline 异常中断时，可以从最近的恢复点恢复，避免从头开始。

### 恢复点定义

| 恢复点编号 | 恢复点名称 | 触发时机 | 保存的状态 | 恢复动作 |
|----------|----------|---------|----------|---------|
| RP-0 | **IDLE 基线** | 每次回到 IDLE 状态 | 完整 .yang-state.json 快照 | 从 IDLE 重新开始 |
| RP-1 | **Seed 完成** | seed_done 事件 | last_seed_file + seed 输出文件 | 从 score 阶段开始 |
| RP-2 | **Score 完成** | score_done 事件 | last_score_file + score 输出文件 | 从 predict 阶段开始 |
| RP-3 | **Predict 完成** | predict_done 事件 | last_prediction_file + prediction 文件 | 从 shoot 阶段开始 |
| RP-4 | **Shoot 完成** | shoot_done 事件 | last_shoot_file + shoot 记录 | 从 publish 阶段开始 |
| RP-5 | **Publish 完成** | publish_done 事件 | last_publish_file + publish 记录 | 从 retro 阶段开始 |
| RP-6 | **Retro 完成** | retro_done 事件 | calibration_samples + retro 文件 | 从 IDLE 或 bump 开始 |

### 恢复点存储

```json
// 存储位置：.yang-cache/recovery-points/<rp_id>.json
{
  "rp_id": "RP-3",
  "created_at": "2026-06-14T15:30:00+08:00",
  "pipeline_stage": "PREDICTING",
  "state_snapshot": {
    "last_seed_file": "seeds/2026-06-14_选题.md",
    "last_score_file": "scores/2026-06-14_评分.md",
    "last_prediction_file": "predictions/2026-06-14_预测.md",
    "calibration_samples": 8,
    "rubric_version": "v2"
  },
  "files_created": [
    "seeds/2026-06-14_选题.md",
    "scores/2026-06-14_评分.md",
    "predictions/2026-06-14_预测.md"
  ]
}
```

### 恢复流程

```
检测到 Pipeline 异常中断
  │
  ├─ Step 1: 判定中断位置
  │    ├─ 读取 .yang-state.json
  │    ├─ 检查 in_progress_session（非 null = 中断发生在该 skill 执行中）
  │    └─ 检查 last_*_file 字段（确定最近完成的阶段）
  │
  ├─ Step 2: 定位恢复点
  │    ├─ 查找 .yang-cache/recovery-points/ 中最新的恢复点
  │    └─ 选择中断位置前一个恢复点（保守策略：从上一个完成点恢复）
  │
  ├─ Step 3: 验证恢复点完整性
  │    ├─ 检查恢复点中引用的所有文件是否存在
  │    ├─ 检查 state_snapshot 与当前 state 的一致性
  │    └─ 如文件缺失 → 降级到更早的恢复点
  │
  ├─ Step 4: 执行恢复
  │    ├─ 清除 in_progress_session
  │    ├─ 从恢复点恢复 state 字段
  │    ├─ 原子写入 .yang-state.json
  │    └─ 向用户报告恢复结果
  │
  └─ Step 5: 恢复后验证
       ├─ 确认 state 可正常读取
       ├─ 确认所有 last_*_file 指向的文件存在
       └─ 提示用户"已从恢复点 RP-N 恢复，请从 [阶段] 重新开始"
```

### 恢复点清理策略

| 清理规则 | 说明 |
|---------|------|
| 保留数量 | 最多保留最近 10 个恢复点 |
| 清理时机 | 每次 bump 完成后清理旧恢复点 |
| 清理规则 | 删除 bump 前的所有恢复点（bump 已改变 rubric，旧恢复点不可用） |
| 手动清理 | 用户可手动删除 `.yang-cache/recovery-points/` 中的旧文件 |

### 异常中断场景与恢复策略

| 中断场景 | 中断位置 | 恢复策略 |
|---------|---------|---------|
| Skill 执行中崩溃 | in_progress_session 非 null | 清除 session → 从上一个恢复点恢复 |
| 网络中断（Pipeline 模式） | Agent 间通信失败 | 等待恢复 → 重试当前阶段（最多 3 次） |
| State 文件损坏 | JSON 解析失败 | 从最近恢复点的 state_snapshot 恢复 |
| 输出文件丢失 | last_*_file 指向不存在的文件 | 降级到上一个恢复点 → 重新执行 |
| 用户强制中断 | Ctrl+C / 手动停止 | 清除 session → 从 IDLE 恢复 → 用户选择从哪个阶段继续 |
| Bump 中断 | rubric_version 未更新 | 回滚到 bump 前的恢复点 → 重新执行 bump |