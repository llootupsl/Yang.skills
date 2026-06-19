---
name: yang-evolution-bus
version: "2.0"
description: 进化总线协议。多Agent协作引擎与闭环校准系统之间的轻量通信层，通过三阶段钩子注入机制同步双向信号。
trigger-words: [产线模式, pipeline mode, 完整流程, 激活总线, 进化总线, 总线协议, 多Agent协作]
author: 阿洋
argument-hint: "[--stage <1|2|3>] [--bridge-mode tight|loose]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
tags: [进化总线, 多Agent协作, 闭环校准, 信号同步, 钩子注入]
---

# yang-evolution-bus · 进化总线协议

> ⚗️ **实验性功能** —— Agent 引擎需用户自行实现，本 skill 仅提供协议标准。总线协议的信号格式和注入点定义可用于指导自建 Agent 引擎与 Yang.skills 的集成开发。
>
> **前置条件**：项目已 init
>
> **功能**：多Agent协作引擎 ↔ 闭环校准系统 双向信号翻译与同步
>
> **依赖**：evolution-bus/bus-protocol.md、evolution-bus/bridge-rules.md

---

## 前置条件检查

> [前置条件] 本 skill 为辅助 skill，无严格流水线前置依赖

读取 `.yang-state.json`:
- 若 `in_progress_session` 不为 null → 警告并发冲突（soft check，不强制拒绝）
- 若 `.yang-state.json` 不存在 → 提示用户运行 yang-init
- 检查通过后，正常执行

### 生命周期钩子安装

本 skill 的三个生命周期钩子（`stage1-seed-hook.md`、`stage2-predict-hook.md`、`stage3-retro-hook.md`）位于 `skills/yang-evolution-bus/hooks/` 目录下，**不会**被 yang-init 自动安装。

激活 evolution-bus 后，需手动完成以下步骤：

1. 将钩子文件复制到项目的 `.claude/hooks/` 目录：
   ```bash
   cp skills/yang-evolution-bus/hooks/stage1-seed-hook.md .claude/hooks/
   cp skills/yang-evolution-bus/hooks/stage2-predict-hook.md .claude/hooks/
   cp skills/yang-evolution-bus/hooks/stage3-retro-hook.md .claude/hooks/
   ```
2. 在 `.claude/hooks/hooks.json` 中注册三个钩子（参考现有钩子的注册格式）
3. 重启 Claude Code 会话以加载新钩子

---

## 工作流

### 核心设计

```
多Agent协作引擎 Agent 集群          闭环校准系统
     │                              │
     ├──────── 进化反馈总线 ─────────┤
      │         │         │          │
      │    Stage 1   Stage 2   Stage 3│
      │    (Seed)    (Predict) (Retro)│
      │         │         │          │
      ▼         ▼         ▼          ▼
   选题注入   盲预测同步  复盘反馈
```

### Stage 1: 选题注入

> 🔍 **检查点 CP-1**：`.yang-state.json` 存在且无并发冲突，钩子文件已安装

**触发时机**：选题 Agent 生成选题时

**数据流**：

```
Agent群 → Bus → 闭环校准系统
  ├─ Agent群选题 Agent 产出的选题列表
  ├─ 每个选题的 Agent群内部评分
  └─ 触发闭环校准系统自动打分验证

闭环校准系统 → Bus → Agent群
  ├─ 闭环校准系统对每个选题的 rubric 评分
  ├─ 选题排序修正建议
  └─ Hook 变体推荐
```

**Bus 规则**（来自 `bridge-rules.md`）：
- Agent群内部"质量分" → 映射到闭环校准系统 rubric 对应维度
- 闭环校准系统评分差异 > 20% → 标记「跨系统争议」，需人工决策

### Stage 2: 盲预测同步

> 🔍 **检查点 CP-2**：Stage 1 选题注入已完成，闭环校准系统评分差异 < 20% 或已标记争议

**触发时机**：内容产线完成脚本、准备发布前

**数据流**：

```
Agent群 → Bus → 闭环校准系统
  ├─ Agent群 Content Agent 产出的成稿
  ├─ 发布计划（时间/平台）
  └─ 触发闭环校准系统盲预测

闭环校准系统 → Bus → Agent群
  ├─ 预测播放量/互动率
  ├─ 预测置信度 → 影响发布决策
  └─ 建议修改项（如 rubric 某维低分）
```

**Bus 规则**：
- 闭环校准系统预测置信度 < 0.3 → 不干预 Agent群发布决策
- 单维得分 < 2/5 → 建议 Agent群回炉修改该维

### Stage 3: 复盘反馈

> 🔍 **检查点 CP-3**：Stage 2 盲预测已完成，发布后数据已到账（T+3d）

**触发时机**：数据 Agent 收集到发布后数据

**数据流**：

```
Agent群 → Bus → 闭环校准系统
  ├─ Agent群数据 Agent 收集的实际表现数据
  └─ 触发闭环校准系统自动复盘

闭环校准系统 → Bus → Agent群
  ├─ 预测准确度分析
  ├─ rubric 维度贡献率回顾
  └─ 校准池状态更新 → 可能触发 bump
```

**Bus 规则**：
- 连续 3 条预测偏差 > 30% → 建议降低 Agent群对该维的依赖权重
- Bump 通过后自动同步新版 rubric 到 Agent群选题/内容 Agent

---

## 总线模式

| 模式 | 含义 | 闭环校准系统行为 |
|------|------|---------|
| **tight** | Agent群发布前必须通过闭环校准系统盲预测门禁 | blind-predict 不通过 → 拦截发布 |
| **loose** | 闭环校准系统提供建议但 Agent群可自行决定 | 盲预测输出后不拦截，仅标记 |
| **solo** | 闭环校准系统完全独立运行 | Agent群全部休眠（默认） |

**搜索意图信号传递**：Channel E产出的搜索意图信号通过bus传递：seed→hook-factory（搜索意图钩子）→publish（搜索意图标签）→retro（搜索意图验证）→bump（搜索意图校准）。

---

## 输出

管道模式运行时不输出冗长中间过程，仅输出阶段性摘要：

```
🏭 产线模式 · 激活

[Stage 1] 选题注入... ✅ 闭环校准系统验证 3/5 选题，修正 1 个排序
[Stage 2] 盲预测同步... ✅ 预测: 8k-12k，置信度: 0.65
[Stage 3] 复盘反馈...   ⏳ 等待发布后数据（T+3d 自动触发）
```

> 🔍 **检查点 CP-4**：三阶段摘要均已输出，无阶段被跳过
>
> 🔍 **检查点 CP-5**：总线模式已确认（tight/loose/solo），tight 模式下盲预测门禁已生效

---

## 失败模式编码

| 编码 | 含义 | 触发条件 | 处置 |
|------|------|----------|------|
| `EB-E01` | 项目未初始化 | `.yang-state.json` 不存在 | 拒绝激活，提示 `yang-init` |
| `EB-E02` | 绕过总线直接通信 | Agent 群绕过 Bus 直接与闭环校准系统通信 | 检测并报错"禁止绕过总线通信" |
| `EB-E03` | 阶段超时 | 某阶段 >60s 无响应 | 降级到 loose 模式，标注异常 |
| `EB-E04` | 跨系统争议累积 | 评分差异 >20% 累计 ≥3 条 | 建议调整映射公式，人工决策 |
| `EB-E05` | 钩子未安装 | 生命周期钩子文件不在 `.claude/hooks/` | 警告并提示手动安装钩子 |
| `EB-E06` | 并发冲突 | `in_progress_session` 已存在 | 警告但不强制拒绝（soft check） |

---

## 反例黑名单

1. **禁止绕过总线直接通信**：Agent 群与闭环校准系统之间必须通过 Bus 传递信号，不得直连
2. **禁止跳过阶段**：三阶段必须按序执行，不得从 Stage 1 直接跳到 Stage 3
3. **禁止 tight 模式跳过门禁**：tight 模式下盲预测不通过必须拦截发布，不得放行
4. **禁止忽略跨系统争议**：评分差异 >20% 必须标记，不得静默通过
5. **禁止置信度 <0.3 的信号过桥**：低置信度信号不得影响 Agent 群决策
6. **禁止连续预测偏差不处理**：连续 3 次偏差 >30% 必须建议降权，不得继续依赖
7. **禁止未初始化激活总线**：项目未 init 时不得激活总线
8. **禁止 solo 模式下发 Agent 群信号**：solo 模式下 Agent 群休眠，不得发送信号

---

## 量化标准：总线信号一致性

进化总线的有效性由**信号一致性**衡量：

- **信号一致性** = Agent 群评分与闭环校准系统评分差异 <20% 的维度数 / 总维度数
- **合格线**：一致性 ≥ 60%（5 维中至少 3 维差异 <20%）
- **优秀线**：一致性 ≥ 80%
- 跨系统争议率：≤ 1 次/周期（超过则建议调整映射公式）
- 预测偏差收敛速度：连续 3 次复盘后偏差应下降 ≥10 个百分点
- 一致性 < 60% 时，必须暂停总线并建议人工校准映射公式

---

## 错误处理

| 场景 | 行为 |
|------|------|
| 绕过总线直接通信 | 检测并报错"禁止绕过总线通信" |
| 某阶段超时（>60s 无响应） | 降级到 loose 模式，标注异常 |
| 未 init 就激活总线 | 拒绝，提示先 init |

---

## 知识库依赖

本 skill 在进化总线协议运行中引用以下知识库内容：

- 知识库A：数据追踪闭环（预测→实际→偏差分析→模型修正）—— 作为总线双向信号翻译的数据框架 `[来源：A-数据]`
- 知识库B：运营漏斗与内容协作流程—— 用于产线模式下的内容流转节奏校准 `[来源：B-运营]`

在输出总线摘要时，应追加：

```
📚 知识依据：A-数据 | B-运营
```

---

## 总线与子skill的接口规范

每个子skill接入进化总线时，必须遵循以下标准接口协议，确保信号格式统一、语义无损。

### 接入标准接口

| 接口项 | 规范 | 示例 |
|--------|------|------|
| **信号格式** | JSON，包含 `source`、`stage`、`payload`、`confidence`、`timestamp` 五个必须字段 | `{"source":"yang-seed","stage":1,"payload":{"topics":[...]},"confidence":0.8,"timestamp":"2025-01-15T10:00:00Z"}` |
| **source 字段** | 子skill名称，必须与 `skills/yang-<name>/SKILL.md` 中的 `name` 字段一致 | `"yang-seed"` / `"yang-predict"` / `"yang-retro"` |
| **stage 字段** | 1/2/3，对应三阶段钩子 | Stage 1=选题注入，Stage 2=盲预测同步，Stage 3=复盘反馈 |
| **payload 字段** | 阶段特定的业务数据，结构由各阶段数据流定义 | Stage 1: `{topics, scores}`；Stage 2: `{script, publish_plan}`；Stage 3: `{actual_data}` |
| **confidence 字段** | 0.0-1.0 浮点数，<0.3 的信号不过桥 | `0.65` |
| **timestamp 字段** | ISO 8601 格式，UTC 时区 | `"2025-01-15T10:00:00Z"` |
| **响应格式** | JSON，包含 `status`（ok/rejected）、`actions`（建议动作列表）、`bus_mode`（tight/loose/solo） | `{"status":"ok","actions":["排序修正：将选题B提升至第1位"],"bus_mode":"tight"}` |

### 各阶段接入映射

| 子skill | 接入阶段 | payload 结构 | 响应消费方式 |
|---------|----------|-------------|-------------|
| yang-seed | Stage 1 | `{topics: [{title, score, dimensions}], agent_scores: {吸引力, 信息含量, 情绪感染, 人设匹配, 传播预估}}` | 读取 `actions` 中的排序修正建议，更新 candidates.md |
| yang-score | Stage 1 | `{score_report: {dimensions, composite}, rubric_version: string}` | 读取跨系统争议标记，决定是否需要人工决策 |
| yang-predict | Stage 2 | `{script_path, publish_plan: {time, platform}, prediction: {range, confidence}}` | 读取盲预测结果和修改建议；tight 模式下不通过则拦截发布 |
| yang-publish | Stage 2 | `{publish_link, published_at}` | 记录发布时间，启动 T+3d 计时器 |
| yang-retro | Stage 3 | `{actual_data: {views, likes, comments, shares}, prediction_path}` | 读取预测准确度分析和 rubric 维度贡献率回顾 |
| yang-bump | Stage 3 | `{bump_result: {version, changes, validation_status}}` | bump 通过后自动同步新版 rubric 到相关 Agent |

### 接入校验规则

1. **格式校验**：信号必须包含全部5个必须字段，缺少任一字段拒绝翻译（对应 `BR-E02`）
2. **阶段校验**：子skill发送的 `stage` 必须与总线当前阶段匹配，跨阶段信号被拒绝
3. **置信度校验**：`confidence < 0.3` 的信号不过桥，`0.3-0.5` 标注 [低频]
4. **幂等性**：同一 `source + stage + timestamp` 的信号只处理一次，重复信号忽略

---

## 总线性能监控

总线运行时持续监控以下指标，确保信号传输的及时性和可靠性。

### 监控指标

| 指标名称 | 定义 | 采集方式 | 合格线 | 告警阈值 |
|----------|------|----------|--------|----------|
| **消息吞吐量** | 单位时间内成功通过总线的信号数（条/分钟） | 统计每分钟 `status=ok` 的信号数 | ≥ 10 条/分钟 | < 5 条/分钟（总线拥堵） |
| **端到端延迟** | 信号从 `source` 发出到 `response` 返回的时间差（秒） | `response.timestamp - signal.timestamp` | ≤ 30s | > 60s（触发 EB-E03 降级） |
| **信号丢失率** | 发出但未收到响应的信号占比 | `(sent - received) / sent` | ≤ 1% | > 5%（总线不稳定） |
| **跨系统争议率** | 评分差异 >20% 的维度占比 | 统计争议标记数 / 总维度数 | ≤ 1 次/周期 | ≥ 3 次/周期（触发 EB-E04） |
| **预测偏差趋势** | 连续复盘后预测偏差的变化方向 | 对比最近3次复盘的偏差值 | 偏差下降 ≥10pp/3次 | 连续3次偏差 >30%（触发降权建议） |
| **clamp 截断率** | 映射结果被截断的信号占比 | 统计 clamp 触发次数 / 总映射次数 | ≤ 10% | > 20%（映射公式需校准） |
| **阶段完成率** | 三阶段全部完成的比例 | 完整3阶段周期数 / 总周期数 | ≥ 90% | < 70%（阶段跳过严重） |

### 告警分级

| 告警级别 | 触发条件 | 处置动作 |
|----------|----------|----------|
| **P0-紧急** | 信号丢失率 >10% 或 阶段完成率 <50% | 立即暂停总线，降级到 Solo 模式，人工介入 |
| **P1-严重** | 端到端延迟 >60s 或 跨系统争议率 ≥3次/周期 | 降级到 loose 模式，标注异常，建议检查映射公式 |
| **P2-警告** | 消息吞吐量 <5条/分钟 或 clamp 截断率 >20% | 继续运行，输出警告日志，建议下次周期校准 |
| **P3-提示** | 预测偏差趋势未收敛 或 阶段完成率 70%-90% | 记录到诊断日志，yang-doctor 下次运行时报告 |

### 监控数据存储

- 运行时指标写入 `.yang-cache/bus-metrics.jsonl`，每条记录包含 `timestamp`、`metric`、`value`、`threshold`、`level`
- yang-status 看板展示最近 10 个周期的指标趋势
- yang-doctor 诊断时读取指标文件，输出异常汇总

---

## 总线故障恢复手册

总线异常时按以下步骤诊断和恢复，确保系统尽快回到正常状态。

### 故障诊断流程

```
总线异常
  │
  ├─ 1. 确认异常类型（查看 bus-metrics.jsonl 最新记录）
  │     ├─ 信号丢失 → 进入流程 A
  │     ├─ 阶段超时 → 进入流程 B
  │     ├─ 跨系统争议累积 → 进入流程 C
  │     └─ 映射越界/截断 → 进入流程 D
  │
  ├─ 2. 执行对应恢复流程
  │
  └─ 3. 恢复后验证
        ├─ 运行 yang-doctor 确认无异常
        ├─ 检查 bus-metrics 指标回到合格线内
        └─ 执行一个完整三阶段周期验证
```

### 流程 A：信号丢失恢复

| 步骤 | 动作 | 预期结果 |
|------|------|----------|
| A1 | 检查 `.yang-state.json` 中 `in_progress_session` 是否冲突 | 确认无并发冲突 |
| A2 | 检查 `.claude/hooks/` 下三个阶段钩子文件是否存在 | 钩子文件完整 |
| A3 | 检查 `hooks.json` 中钩子注册是否正确 | 注册格式正确 |
| A4 | 重新发送丢失的信号（手动触发对应阶段） | 信号成功过桥 |
| A5 | 验证响应中 `status=ok` | 信号恢复 |

### 流程 B：阶段超时恢复

| 步骤 | 动作 | 预期结果 |
|------|------|----------|
| B1 | 确认超时阶段（Stage 1/2/3） | 定位超时点 |
| B2 | 检查闭环校准系统是否正常响应 | 确认校准系统状态 |
| B3 | 如校准系统正常 → 降级到 loose 模式继续 | loose 模式运行 |
| B4 | 如校准系统异常 → 降级到 Solo 模式 | Solo 模式运行 |
| B5 | 记录超时事件到 `bus-metrics.jsonl` | 事件已记录 |
| B6 | 超时恢复后，手动重新触发超时阶段 | 阶段正常完成 |

### 流程 C：跨系统争议累积恢复

| 步骤 | 动作 | 预期结果 |
|------|------|----------|
| C1 | 列出所有争议维度和差异值 | 明确争议范围 |
| C2 | 分析争议原因：映射公式偏差 / Agent群评分标准漂移 / 数据异常 | 定位根因 |
| C3 | 映射公式偏差 → 调整 `bridge-rules.md` 中的映射系数 | 公式更新 |
| C4 | 评分标准漂移 → 重新校准 Agent群评分锚点 | 锚点对齐 |
| C5 | 数据异常 → 清洗异常数据，重新打分 | 数据恢复 |
| C6 | 重跑争议期间的信号，验证一致性 ≥ 60% | 争议消除 |

### 流程 D：映射越界/截断恢复

| 步骤 | 动作 | 预期结果 |
|------|------|----------|
| D1 | 统计 clamp 截断率和越界维度 | 量化越界程度 |
| D2 | 分析越界原因：输入值范围变化 / 映射系数偏移 | 定位根因 |
| D3 | 调整映射公式中的偏移量和缩放系数 | 新公式减少截断 |
| D4 | 用历史数据回测新公式，确认截断率 ≤ 10% | 公式验证通过 |
| D5 | 更新 `bridge-rules.md`，记录变更到 `rubric-memo.md` | 规则已更新 |

### 紧急降级操作

当总线无法在 5 分钟内恢复时，执行紧急降级：

1. 在 `.yang-state.json` 中设置 `bus_mode: "solo"`
2. 输出：`🔴 总线紧急降级至 Solo 模式 | 原因：<具体原因> | 恢复需手动重新激活`
3. 所有 Agent 群信号立即停止，闭环校准系统独立运行
4. 降级后通过 `/yang-evolution-bus` 重新激活总线

---

## 错误处理

| 场景 | 行为 |
|------|------|
| 绕过总线直接通信 | 检测并报错"禁止绕过总线通信" |
| 某阶段超时（>60s 无响应） | 降级到 loose 模式，标注异常 |
| 未 init 就激活总线 | 拒绝，提示先 init |