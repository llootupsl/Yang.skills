---
name: research-multi-agent
description: 多Agent协作框架调研 —— Role-based / Event-driven / Graph-based 三大架构范式对比，为多Agent协作引擎架构优化提供设计参考
parent: research
author: 阿洋
---

# 多Agent协作框架调研

> **调研问题**：多Agent协作引擎当前使用自定义多Agent架构，主流多Agent架构范式（Role-based / Event-driven / Graph-based）有哪些设计理念和工程实践值得参考？
> **结论**：三种范式各有侧重 —— Role-based 设计与多Agent协作引擎理念最一致（重点参考）；Event-driven 消息路由值得学习；Graph-based State Checkpoint 机制可解决闭环校准系统 immutable prediction 的技术难点。

---

## 一、三大范式总览对比

| 维度 | Role-based | Event-driven | Graph-based |
|------|--------|:---:|:---:|
| **核心理念** | 角色驱动 | 事件驱动 | 图编排 |
| **Agent模型** | Agent / Task / Team 三层 | ConversableAgent / Group | StateGraph / Node / Edge |
| **编排模型** | 任务分配 + 团队协作 | 对话路由 + 拓扑组合 | DAG图 + State Checkpoint |
| **状态管理** | 简单（Task结果） | 中等（对话历史） | 强（Checkpoint + State持久化） |
| **学习曲线** | 低（语义直观） | 中（需理解路由机制） | 高（需理解图编程范式） |
| **适用场景** | 团队协作、任务分工 | 复杂对话、多专家讨论 | 有状态的多步骤工作流 |
| **多Agent协作引擎参考价值** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 二、方案详细分析

### 2.1 Role-based 范式 —— 最值得参考（Phase 2）

**架构模型**：

```
Role-based 三层模型
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Team (团队)
  ├── Agent 1 (角色1: Role + Goal + Backstory)
  │    ├── Task 1 (任务1)
  │    └── Task 2 (任务2)
  ├── Agent 2 (角色2: Role + Goal + Backstory)
  │    └── Task 3 (任务3)
  └── Process: sequential / hierarchical
```

**与 多Agent协作引擎 的映射关系**：

| Role-based 概念 | 多Agent协作引擎 对应概念 | 吻合度 |
|-------------|-------------|:---:|
| Agent (Role + Goal + Backstory) | L1/L2 Agent (角色 + 知识来源 + 权重) | 95% |
| Task | 研判/创作任务 | 90% |
| Team | 部门级Agent组 | 85% |
| Process (sequential) | 四阶段顺序流程 | 80% |
| Process (hierarchical) | Director统筹模式 | 75% |

**值得参考的设计模式**：

| 模式 | Role-based 实现 | 对 多Agent协作引擎 的启发 |
|------|-----------|-------------|
| **Role Prompting** | 每个Agent有独立的 Role + Goal + Backstory | 可统一Agent定义格式为 frontmatter |
| **Task Delegation** | Agent可自主委派子任务给其他Agent | 可设计 L2→L3 的子任务委派机制 |
| **Output Validation** | Task内置expected_output验证 | 可用Pydantic自动验证 |
| **Error Recovery** | 失败自动重试 + 降级策略 | 可引入Agent级错误处理（非全局崩溃） |
| **Tools Integration** | Agent可挂载自定义工具 | 可直接参考实现 MCP Tool 挂载到Agent |

---

### 2.2 Event-driven 范式 —— 对话路由参考（Phase 3）

**架构模型**：

```
Event-driven 对话驱动模型
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ConversableAgent
  ├── UserProxyAgent (人机交互代理)
  └── AssistantAgent (AI代理)
        │
        ▼
GroupChat (多Agent群聊)
  ├── Speaker Selection (发言者选择策略)
  └── Message Routing (消息路由)
```

**核心设计模式值得参考**：

| 模式 | 说明 | 对 多Agent协作引擎 的启发 |
|------|------|-------------|
| **Conversation Patterns** | Two-Agent Chat / Sequential Chat / Group Chat | 可参考设计Agent间的标准化消息协议 |
| **Speaker Selection** | 自动选择下一个发言的Agent | 阶段三"蓝帽辩论"环节可参考 |
| **Nested Chat** | Agent内部可嵌套子对话 | 高层Agent（如Director）调低层Agent时可参考 |
| **Code Execution** | Agent可执行代码并反馈结果 | 数据分析类Agent可集成 |

---

### 2.3 Graph-based 范式 —— State Checkpoint 关键技术（Phase 3）

**架构模型**：

```
Graph-based 图编排模型
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
StateGraph (状态图)
  ├── Node (节点: 计算函数/Agent)
  ├── Edge (边: 控制流)
  │    ├── Normal Edge (固定流转)
  │    └── Conditional Edge (条件分支)
  └── Checkpoint (状态快照)
        ├── save (保存当前状态)
        └── replay (回放/追溯)
```

**对 多Agent协作引擎 最有价值的设计**：

| 设计 | 说明 | 解决问题 |
|------|------|-------------------|
| **State Checkpoint** | 每一步执行后自动保存状态快照 | 实现 immutable prediction（预测不可变）+ retro 追加模式（追加不覆写） |
| **Conditional Edges** | 根据状态动态选择下一步 | 自动化阶段间的条件跳转（如数据充足→直接进入阶段三） |
| **Human-in-the-Loop** | 在关键节点暂停等待人工审批 | 争议内容/Dou+投放等高风险决策节点 |
| **Time Travel** | 回溯到任意历史Checkpoint | 策略复盘：退回到某历史节点，模拟"如果当时选了另一条路" |

**State Checkpoint 在 多Agent协作引擎 中的应用**：

```python
# 伪代码：用 Checkpoint 实现 immutable prediction
checkpointer = MemorySaver()
config = {"configurable": {"thread_id": "account-001"}}

# 阶段二：Agent独立研判（状态保存）
graph.invoke({"phase": 2, "agents": ["STR-002", "STR-003"]}, config)

# 阶段三：蓝帽辩论（追加，不覆写阶段二的结果）
graph.invoke({"phase": 3, "mode": "debate"}, config)

# 任何时候可以回溯到阶段二的Checkpoint
state = graph.get_state(config)
print(state.created_at)  # 阶段二完成时的时间戳
```

---

## 三、推荐方案与参考优先级

### 参考优先级

| 优先级 | 范式 | 参考内容 | 应用阶段 | 理由 |
|--------|------|---------|---------|------|
| **P0** | Role-based | Agent角色设计、Task编排、错误处理 | Phase 2 | 与多Agent协作引擎设计哲学一致，可立即参考优化 |
| **P1** | Graph-based | State Checkpoint、条件分支、人工审批节点 | Phase 3 | 解决 immutable prediction + retro 追加模式技术难点 |
| **P2** | Event-driven | 消息路由协议、多Agent对话模式 | Phase 3 | 阶段三蓝帽辩论环节的消息协议设计参考 |

### 不直接集成的策略

```
为什么不直接使用第三方Agent框架替代多Agent协作引擎自定义架构？

1. 多Agent协作引擎的工作流是"创作驱动"（内容质量 > 流程效率），通用Agent框架是"任务驱动"
2. 多Agent协作引擎的知识来源锚点机制是核心差异化，通用框架不支持
3. 多Agent协作引擎的"默会知识边界"和"阶段退出条件"是党性原则级别的设计约束

策略：参考各范式的最佳实践 → 优化多Agent协作引擎自定义架构 → 保持差异化
```

---

## 四、具体参考行动清单

| 序号 | 参考来源 | 行动 | 优先级 |
|------|---------|------|--------|
| 1 | Role-based Prompting | 统一Agent定义格式，引入 Role/Goal/Backstory frontmatter | 高 |
| 2 | Role-based Output Validation | 用Pydantic自动验证Agent输出，替代逐份检查 | 高 |
| 3 | Role-based Error Recovery | 每个Agent加入独立错误处理和降级路径 | 中 |
| 4 | Graph-based State Checkpoint | 实现immutable prediction的持久化状态回溯 | 中 |
| 5 | Graph-based Human-in-the-Loop | 高风险节点（Dou+投放、争议内容）加入人工审批 | 中 |
| 6 | Event-driven Message Protocol | 设计Agent间的标准化消息格式 | 低 |

---

## 五、预期收益

| 优化方向 | 当前挑战 | 参考范式 | 预期提升 |
|---------|---------|---------|---------|
| Agent定义一致性 | 各Agent格式不统一 | Role-based Prompting | 统一为 frontmatter 格式 |
| 输出质量验证 | Director逐份人工检查 | Role-based Output Validation | 自动验证，效率提升 |
| 错误鲁棒性 | Agent崩溃=全局中断 | Role-based Error Recovery | 单Agent失败不影响全局 |
| 状态持久化 | 不可回溯 | Graph-based Checkpoint | 支持回溯 + immutable |
| 风险管控 | 无人工审批节点 | Graph-based HITL | 高风险决策加入审批 |

---

> **更新日期**：2026-05
> **调研状态**：已完成三范式对比分析，具体参考行动列入 Phase 2/3