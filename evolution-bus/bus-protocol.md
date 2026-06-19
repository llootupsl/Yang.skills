# 进化反馈总线协议 · Evolution Feedback Bus Protocol

> **版本**：v2.0  
> **状态**：正式发布  
> **架构哲学**：Agent引擎 做内容，闭环校准系统 做校准，总线做翻译——三元各司其职，互不侵入，信号精准。

---

## 目录

- [§1 三元协同架构定义](#1-三元协同架构定义)
- [§2 总线唯一通信层原则](#3-总线唯一通信层原则)
- [§3 三阶段注入点定义](#4-三阶段注入点定义)
  - [§3.1 Stage1 Hook —— 选题注入点](#41-stage1-hook--选题注入点)
  - [§3.2 Stage2 Hook —— 盲预测注入点](#42-stage2-hook--盲预测注入点)
  - [§3.3 Stage3 Hook —— 复盘注入点](#43-stage3-hook--复盘注入点)
- [§4 Solo 模式定义](#5-solo-模式定义)
- [§5 信号方向性约束](#6-信号方向性约束)
- [§6 置信度标注传播规则](#7-置信度标注传播规则)
- [§7 总线运行时状态机](#8-总线运行时状态机)
- [§8 异常处理与降级策略](#9-异常处理与降级策略)
- [附录 A：注入点信号格式完整规范](#附录-a注入点信号格式完整规范)

---

## §0 架构声明

### 0.1 本文档的权威性

本文档是 Agent引擎-闭环校准系统 v2 系统的**唯一架构权威文档**。

### 0.2 现行架构

当前 v2 采用三元协同架构（Agent引擎 + 闭环校准系统 + 总线），各方独立运行、互不侵入，信号经进化反馈总线桥接。

---

## §1 三元协同架构定义

### 1.1 架构全景

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Agent引擎-闭环校准系统 v2 · 三元协同架构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌──────────────────────────────┐        ┌──────────────────────────────┐    │
│   │         Agent引擎 v5               │        │      Yang.skills        │    │
│   │                              │        │                              │    │
│   │  C-001  首席策略官            │        │  yang-seed      选题引擎     │    │
│   │  C-002  赛道商业策略师         │        │  yang-trends    热点追踪     │    │
│   │  C-003  内容总监              │        │  yang-predict   盲预测引擎   │    │
│   │  C-004  流量运营官            │        │  yang-score     Rubric评分   │    │
│   │  C-005  商业变现官            │        │  yang-shoot     拍摄登记     │    │
│   │  C-006  魔鬼代言人            │        │  yang-publish   发布登记     │    │
│   │  C-007  元认知监控官           │        │  yang-retro     复盘校准     │    │
│   │                              │        │  yang-bump      Bump评估     │    │
│   │  15,967 行 · 自成体系         │        │  yang-learn     对标学习     │    │
│   │  7 个 Agent · 完整闭环        │        │  yang-status    状态看板     │    │
│   │  独立运行 · 不感知 闭环校准系统        │        │  yang-migrate   版本迁移     │    │
│   │                              │        │  7,607 行 · 自成体系         │    │
│   └──────────────┬───────────────┘        └──────────────┬───────────────┘    │
│                  │                                       │                    │
│                  │        创作意图信号                     │                    │
│                  │    ──────────────────→                │                    │
│                  │                                       │                    │
│                  │         ┌─────────────────┐            │                    │
│                  └────────→│   进化反馈总线    │←──────────┘                    │
│                            │                 │                                │
│                            │  · Stage1 Hook   │                               │
│                            │  · Stage2 Hook   │                               │
│                            │  · Stage3 Hook   │                               │
│                            │  · 信号翻译规则    │                               │
│                            │  · 置信度传播      │                               │
│                            │  · 状态同步协议    │                               │
│                            └─────────────────┘                                │
│                                     │                                         │
│                              ~3,000 行 · 轻量桥接                               │
│                                                                               │
│   设计原则：                                                                   │
│   · Agent引擎 v5 保持原版 15,967 行不变，不感知 闭环校准系统存在                             │
│   · 闭环校准系统 保持原版 7,607 行独立运行，不感知 Agent引擎内部状态                          │
│   · 进化反馈总线是 Agent引擎 和 闭环校准系统 之间的唯一通信层，约 3,000 行做轻量桥接              │
│   · 任何一方的内部重构不影响另一方                                                │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 三体职责边界

#### Agent引擎 v5（第一体）—— 内容创作与运营体系

- **职责**：选题策划 → 脚本创作 → 拍摄执行 → 发布运营 → 数据追踪 → 迭代优化
- **Agent 体系**：C-001~C-007，7 个 C 级 Agent，自成闭环
- **代码规模**：15,967 行（原版，不做修改）
- **对外接口**：仅在产线环节 1 / 3 / 6 暴露三个总线注入点
- **关键规则**：Agent引擎 **不感知** 闭环校准系统内部状态；产线**不因 闭环校准系统 响应延迟而阻塞**

#### Yang.skills（第二体）—— 闭环校准与进化体系

- **职责**：盲预测 → Rubric 评分 → 复盘校准 → Bump 评估 → Pattern 学习 → 对标分析 → 状态管理
- **核心能力**：7,607 行（原版，不做修改）
- **对外接口**：仅通过总线三个 Hook 接收创作意图信号，输出预测/评估信号
- **关键规则**：闭环校准系统 **不感知** Agent引擎内部决策过程；闭环校准系统 输出**异步注入**，不阻塞 产线

#### 进化反馈总线（第三体）—— 信号翻译与桥接层

- **职责**：信号格式翻译 → 注入时机控制 → 置信度传播 → 状态同步 → 异常降级
- **代码规模**：约 3,000 行
- **关键规则**：总线**不做决策**，只做翻译和路由；总线是 Agent引擎 和 闭环校准系统 之间的**唯一通信路径**

### 1.3 三体通信拓扑

```
                        Agent引擎 v5                            Yang.skills
                   ┌──────────────┐                    ┌──────────────────┐
                   │  C-001~C-007 │                    │  yang-* 子技能   │
                   │              │                    │                  │
                   │  产线环节 1   │──→ Stage1 Hook ──→│  yang-seed      │
                   │  (选题策划)   │                    │  yang-trends    │
                   │              │                    │                  │
                   │  产线环节 3   │──→ Stage2 Hook ──→│  yang-predict   │
                   │  (脚本定稿)   │                    │  yang-score     │
                   │              │                    │                  │
                   │  产线环节 6   │──→ Stage3 Hook ──→│  yang-retro     │
                   │  (数据复盘)   │                    │  yang-bump      │
                   │              │                    │                  │
                   │              │←── 信号注入 ───────│  预测/评估信号    │
                   │              │                    │                  │
                   └──────────────┘                    └──────────────────┘
                            │                                  │
                            │         进化反馈总线              │
                            └────────────┬─────────────────────┘
                                         │
                                    唯一通信层
                                 禁止绕过总线直接通信
```

---

## §2 总线唯一通信层原则

### 3.1 核心禁令

> **总线是 Agent引擎 和 闭环校准系统 之间的唯一通信层。禁止任何形式的绕过总线直接通信。**

### 3.2 禁止行为清单

| 编号 | 禁止行为 | 违规后果 |
|------|---------|---------|
| BAN-01 | Agent C-003 直接调用 闭环校准系统 yang-score 做 rubric 评分 | 信号未经翻译，Agent引擎 无法理解 闭环校准系统输出格式 |
| BAN-02 | 闭环校准系统 yang-predict 直接写入 Agent引擎 假设库 | 污染 Agent引擎 内部状态，假设生命周期管理混乱 |
| BAN-03 | Agent C-004 直接读取 闭环校准系统 `.yang-state.json` 做投流决策 | 跨越信息边界，闭环校准系统 内部状态不应被 Agent引擎 直接消费 |
| BAN-04 | 闭环校准系统 yang-retro 直接修改 Agent C-006 的攻击意见 | 违背去中心化原则，闭环校准系统 不应干预 Agent引擎 内部决策 |
| BAN-05 | 任何 Agent 在未经过总线翻译的情况下消费另一体系的原始输出 | 格式不兼容、语义错位、状态污染 |

### 3.3 合法通信路径

```
合法路径：

  Agent引擎 ──→ 总线注入点 ──→ 信号翻译 ──→ 闭环校准系统 子技能
       ↑                                      │
       │                                      ↓
       └──── 总线注入点 ←── 信号翻译 ←── 闭环校准系统 输出信号

非法路径（被禁止）：

  Agent引擎 ──→ 闭环校准系统 子技能          （绕过总线，直接通信）
  闭环校准系统 子技能 ──→ Agent引擎          （绕过总线，直接通信）
  Agent引擎 ──→ .yang-state.json   （直接消费 闭环校准系统 内部状态）
  闭环校准系统 子技能 ──→ Agent引擎 假设库          （直接污染 Agent引擎 内部状态）
```

### 3.4 总线注入点的隔离保证

每个总线注入点确保以下隔离：

1. **格式隔离**：Agent引擎 产出的格式（脚本、选题清单、发布数据）在注入 闭环校准系统 前经总线翻译为 闭环校准系统 能消费的标准格式。
2. **语义隔离**：闭环校准系统 产出的格式（Bucket、rubric 评分、Bump 信号）在注入 Agent引擎 前经总线翻译为 Agent引擎 能理解的操作语义。
3. **状态隔离**：闭环校准系统内部状态（`.yang-state.json`、`rubric_notes.md`、候选池）不被 Agent引擎 直接访问。Agent引擎 仅接收总线翻译后的结构化信号。
4. **时序隔离**：闭环校准系统异步响应不阻塞 产线。产线继续运行，闭环校准系统 信号异步注入后在下一轮产线循环中生效。

---

## §4 三阶段注入点定义

### §4.1 Stage1 Hook —— 选题注入点

#### 4.1.1 概览

| 属性 | 值 |
|------|-----|
| 注入点编号 | BUS-STAGE1 |
| Agent引擎 触发位置 | 产线环节 1（选题策划阶段） |
| 激活的 闭环校准系统 功能 | yang-seed（选题生成引擎）+ yang-trends（热点追踪引擎） |
| 注入 Agent引擎 目标位置 | C-001 路径判定 + C-003 内容策略 |
| 总线文件 | `evolution-bus/hooks/stage1-seed-hook.md` |
| 是否阻塞 产线 | 否——异步注入，本轮选题可先基于历史数据，闭环校准系统 结果在下一轮选题中生效 |

#### 4.1.2 触发条件

Stage1 Hook 在以下**任一**条件满足时触发：

| 条件编号 | 触发条件 | 说明 |
|---------|---------|------|
| TRG-1.1 | Agent C-002 完成对标账号自动发现 | 对标清单已产出，需要 闭环校准系统 根据对标反推选题方向 |
| TRG-1.2 | Agent C-003 请求新一轮选题策划 | 内容线需要补充选题，需要 闭环校准系统 候选人池 |
| TRG-1.3 | 用户直接请求"帮我找选题" | 显式触发选题生成 |
| TRG-1.4 | 定期热点扫描触发（≥24h 间隔） | 闭环校准系统 yang-trends 检测到热点变化 |

#### 4.1.3 激活的 闭环校准系统 功能

| 闭环校准系统 功能 | 激活方式 | 产出内容 |
|---------|---------|---------|
| yang-seed | 全量激活 | ① 兴趣 × 热点 × 历史的选题候选池（≥5 个候选）② 每个选题的红线过滤结果 ③ 每个选题的预测 Bucket 初评 |
| yang-trends | 全量激活 | ① 热点词云 ② 趋势方向 ③ 对标账号的热点跟进状态 |

#### 4.1.4 输入数据格式（Agent引擎 → 闭环校准系统，经总线翻译）

```yaml
# Stage1 输入信号：选题意图信号
bus_stage1_input:
  signal_id: "S1-{timestamp}-{seq}"
  signal_type: "topic_intent"
  source: "AGENT_STAGE1"
  payload:
    user_profile:
      track: "{赛道}"               # 来源：用户输入
      city: "{城市}"                # 来源：用户输入
      persona_model: "{七层人设摘要}" # 来源：C-002 输出
      content_line: "{当前内容线}"    # 来源：C-003 输出
    benchmark_context:
      accounts:                     # 来源：C-002 对标清单
        - id: "{对标账号ID}"
          level: "S|A|B|C"
          content_style: "{风格标签}"
      recent_topics:                # 来源：C-003 对标内容分析
        - "{近30天热门选题1}"
        - "{近30天热门选题2}"
    historical_context:
      published_topics:             # 来源：Agent引擎 历史发布记录
        - id: "{历史选题ID}"
          performance: "{Bucket}"
      candidate_pool_status:        # 来源：候选池当前状态
        total: {N}
        used: {M}
    user_intent:
      explicit_request: "{用户显式请求}"   # 来源：用户输入
      content_line_gap: "{内容线缺口}"     # 来源：C-003 分析
  timestamp: "{ISO8601}"
```

#### 4.1.5 输出信号格式（闭环校准系统 → Agent引擎，经总线翻译）

```yaml
# Stage1 输出信号：选题推荐信号
bus_stage1_output:
  signal_id: "S1-{timestamp}-{seq}-RESP"
  signal_type: "topic_recommendation"
  source: "YANG_STAGE1"
  target:
    primary: "C-001"               # 路径判定：根据 Bucket 分布调整选题投入力度
    secondary: "C-003"             # 内容策略：将候选选题融入内容线规划
  payload:
    candidate_pool:
      - id: "CAND-{NNN}"
        topic: "{选题标题}"
        angle: "{切入角度}"
        predicted_bucket: "S|A|B|C|D"
        confidence: "{置信度标注}"  # 见 §7 置信度标注传播规则
        redline_check: "PASS|FAIL"
        rationale: "{选题依据}"
        benchmark_alignment: "{对标反推证据}"
    trend_integration:
      hot_topics: ["{热点1}", "{热点2}"]
      trend_direction: "{趋势描述}"
      urgency: "HIGH|MEDIUM|LOW"
    recommendation_rank:
      - rank: 1
        candidate_id: "CAND-{NNN}"
        score: {0-100}
        reason: "{推荐理由}"
  calibration_context:             # 闭环校准系统 状态透明传递
    calibration_samples: {N}
    confidence_level: "{speculative|medium|medium-high+}"
    benchmark_ratio: "{对标数据占比}%"
  timestamp: "{ISO8601}"
```

#### 4.1.6 注入后的 Agent引擎 行为

1. **C-001 路径判定**：根据候选池的 Bucket 分布和置信度，判定选题投入路径：
   - Bucket S/A 占比 > 30% → 建议"高度路径"（重点投入）
   - Bucket B 为主 → 建议"中度路径"（标准投入）
   - Bucket C/D 为主 → 建议"默认路径"（低成本试错）
   - 置信度为 speculative → 所有路径降一档执行（保守策略）

2. **C-003 内容策略**：将候选选题按优先级融入内容线规划，标注：
   - 高优先级（Bucket S/A，置信度 medium+）：优先排期
   - 中优先级（Bucket B，任意置信度）：正常排期
   - 低优先级（Bucket C/D，置信度 speculative）：暂存候选池，等待更多数据

---

### §4.2 Stage2 Hook —— 盲预测注入点

#### 4.2.1 概览

| 属性 | 值 |
|------|-----|
| 注入点编号 | BUS-STAGE2 |
| Agent引擎 触发位置 | 产线环节 3（脚本定稿阶段） |
| 激活的 闭环校准系统 功能 | yang-predict（盲预测引擎，7 组件 + 情绪曲线）+ yang-score（Rubric 评分引擎） |
| 注入 Agent引擎 目标位置 | C-007 元认知对齐（H2xx 假设创建） |
| 总线文件 | `evolution-bus/hooks/stage2-predict-hook.md` |
| 是否阻塞 产线 | 否——异步注入。闭环校准系统 预测信号异步写入假设库，后续产线循环中 C-007 消费。产线不等待 闭环校准系统 响应即继续执行。 |

#### 4.2.2 触发条件

| 条件编号 | 触发条件 | 说明 |
|---------|---------|------|
| TRG-2.1 | Agent C-003 完成脚本审核并输出定稿 | 脚本终稿已产出，触发盲预测 |
| TRG-2.2 | 用户提交外部脚本请求评测 | Solo 模式下也可触发（见 §5） |
| TRG-2.3 | 对标学习流程中需要对对标视频做 retrospective 评分 | 反推 rubric 维度得分 |

#### 4.2.3 激活的 闭环校准系统 功能

| 闭环校准系统 功能 | 激活方式 | 产出内容 |
|---------|---------|---------|
| yang-predict | 全量激活（7 组件 + 情绪曲线） | ① 7 组件预测日志（HP/ER/QL/NA/AB/SR/SAT + ER-Curve 六段 × 1-10 分）② 综合 Bucket 预测 ③ 中枢值（播放量区间）④ Hook 保护段（不可变预测段） |
| yang-score | 全量激活 | ① 14 维 rubric 逐维度评分 ② 加权总分 ③ Bucket 映射 |

#### 4.2.4 输入数据格式（Agent引擎 → 闭环校准系统，经总线翻译）

```yaml
# Stage2 输入信号：脚本定稿信号
bus_stage2_input:
  signal_id: "S2-{timestamp}-{seq}"
  signal_type: "script_finalized"
  source: "AGENT_STAGE2"
  payload:
    script:
      content: "{完整脚本正文}"       # 来源：C-003 审核通过的脚本终稿
      topic: "{选题标题}"             # 来源：Stage1 选定的选题
      angle: "{切入角度}"             # 来源：C-003 内容策略
      word_count: {N}
      estimated_duration: "{预估时长}"
    creative_context:
      hook_strategy: "{钩子策略描述}"   # 来源：C-003 输出
      emotion_design: "{情绪设计意图}"  # 来源：C-003 输出
      benchmark_reference:            # 来源：对标分析
        - account: "{对标账号}"
          reference_video: "{参考视频ID}"
          reference_element: "{参考要素}"
    production_context:
      content_line: "{所属内容线}"      # 来源：C-003 内容线规划
      publish_plan: "{预计发布时间}"    # 来源：C-004 发布计划
    rubric_version: "{当前 rubric 版本}" # 来源：闭环校准系统 .yang-state.json
  timestamp: "{ISO8601}"
```

#### 4.2.5 输出信号格式（闭环校准系统 → Agent引擎，经总线翻译）

```yaml
# Stage2 输出信号：盲预测信号
bus_stage2_output:
  signal_id: "S2-{timestamp}-{seq}-RESP"
  signal_type: "blind_prediction"
  source: "YANG_STAGE2"
  target:
    primary: "C-007"               # 元认知对齐：创建 H2xx 假设记录
  payload:
    prediction:
      bucket: "S|A|B|C|D"
      central_value: "{播放量中枢值}"
      range: "{播放量区间}"
      confidence: "{置信度标注}"      # 见 §7
    seven_components:
      HP: {0-10}                    # 钩子力量
      ER: {0-10}                    # 情感共鸣
      QL: {0-10}                    # 金句密度
      NA: {0-10}                    # 叙事结构
      AB: {0-10}                    # 抽象突破
      SR: {0-10}                    # 社会相关性
      SAT: {0-10}                   # 讽刺强度
    emotion_curve:                  # ER-Curve 六段评分
      S1_hook: {1-10}
      S2_build: {1-10}
      S3_conflict: {1-10}
      S4_peak: {1-10}
      S5_resonance: {1-10}
      S6_rhythm: {1-10}
      er_curve_total: {0.0-10.0}   # 加权公式：(S1×1.5+S2×1.0+S3×2.0+S4×2.0+S5×1.0+S6×1.5)/9.0
    rubric_full:
      version: "{rubric版本}"
      tier1: {HP, ER, QL, NA, AB, SR, SAT}
      tier2: {TS, MS}
      tier3: {UN, NO, PC, MA, CL}
      weighted_total: {0-100}
    hook_protection:                 # 不可变预测段
      locked_fields: ["bucket", "central_value", "seven_components", "emotion_curve"]
      lock_timestamp: "{ISO8601}"
      unlock_condition: "T+3 复盘后方可比较"
  calibration_context:
    calibration_samples: {N}
    confidence_level: "{speculative|medium|medium-high+}"
    benchmark_ratio: "{对标数据占比}%"
  timestamp: "{ISO8601}"
```

#### 4.2.6 注入后的 Agent引擎 行为

1. **C-007 元认知对齐**：接收盲预测信号后，自动创建 H2xx 假设记录：
   ```
   H2{NN}：脚本 [{选题标题}] 预测 Bucket = [{Bucket}]，中枢值 = [{播放量中枢值}]
   ─ 基于 [7 组件] + [情绪曲线] 盲预测
   ─ 置信度：[speculative|medium|medium-high+]
   ─ Hook 保护：已锁定预测段，T+3 复盘后方可比较
   ─ 创建时间：{ISO8601}
   ```

2. **C-003 内容策略**：可选消费情绪曲线信号，对 S1（Hook 段）和 S3（冲突段）评分低（<5）的脚本触发钩子变体工厂重新生成 Hook。

3. **C-004 流量运营官**：可选消费 Bucket 信号，基于预测 Bucket 生成投流策略参考（需标注"基于盲预测，非实际数据"）。

---

### §4.3 Stage3 Hook —— 复盘注入点

#### 4.3.1 概览

| 属性 | 值 |
|------|-----|
| 注入点编号 | BUS-STAGE3 |
| Agent引擎 触发位置 | 产线环节 6（T+3 数据复盘阶段） |
| 激活的 闭环校准系统 功能 | yang-retro（复盘校准引擎）+ yang-bump（Bump 评估引擎） |
| 注入 Agent引擎 目标位置 | C-006 魔鬼代言人 + C-001 路径升级/降级裁决 |
| 总线文件 | `evolution-bus/hooks/stage3-retro-hook.md` |
| 是否阻塞 产线 | 半阻塞——闭环校准系统 yang-retro 的偏差分析是路径裁决的前置输入，但 Agent引擎 侧的数据收集和初步复盘可并行进行。 |

#### 4.3.2 触发条件

| 条件编号 | 触发条件 | 说明 |
|---------|---------|------|
| TRG-3.1 | Agent C-004 收到 T+3 真实播放数据 | 视频发布后 ≥3 天，播放数据已稳定 |
| TRG-3.2 | 用户显式请求"复盘"某个视频 | 手动触发复盘 |
| TRG-3.3 | pending_retros 队列中待复盘视频 ≥3 条 | 批量复盘触发 |
| TRG-3.4 | Bump 监控检测到连续 ≥3 次同向偏差 | 自动触发 Bump 评估 |

#### 4.3.3 激活的 闭环校准系统 功能

| 闭环校准系统 功能 | 激活方式 | 产出内容 |
|---------|---------|---------|
| yang-retro | 全量激活 | ① 偏差分析报告（预测 vs 实际）② 观察记录（Observation，含生命周期状态）③ Pattern 候选（升级/新建/废弃）④ 假设验证状态更新（confirmed/rejected/pending） |
| yang-bump | 条件激活：≥3 次同向偏差 + calibration_samples ≥5 | ① Bump 评估提案（五步验证）② 新 rubric 版本草案 ③ 乖离率审计报告 |

#### 4.3.4 输入数据格式（Agent引擎 → 闭环校准系统，经总线翻译）

```yaml
# Stage3 输入信号：发布后数据信号
bus_stage3_input:
  signal_id: "S3-{timestamp}-{seq}"
  signal_type: "post_publish_data"
  source: "AGENT_STAGE3"
  payload:
    video_identity:
      video_id: "{视频唯一标识}"
      script_id: "{关联的脚本ID}"
      prediction_id: "{关联的 Stage2 预测信号ID}"  # 用于偏差分析配对
    actual_performance:
      plays: {实际播放量}
      likes: {点赞数}
      comments: {评论数}
      shares: {分享数}
      completion_rate: "{完播率}"
      engagement_rate: "{互动率}"
      follower_growth: {涨粉数}
      revenue: {变现收入}
      publish_timestamp: "{发布时间 ISO8601}"
      data_collection_timestamp: "{数据采集时间 T+3}"
    traffic_sources:
      recommendation: "{推荐流占比}"
      search: "{搜索占比}"
      following: "{关注流占比}"
      paid: "{付费流量占比}"
    audience_profile:
      age_distribution: "{年龄段分布}"
      gender_ratio: "{性别比}"
      city_tier: "{城市等级分布}"
    douyin_analytics:               # 来源：C-004 流量运营
      retention_curve: "{观众留存曲线}"
      peak_drop_off: "{最大跳出点}"
      replay_segments: "{重播热点段}"
    user_operations:                # 来源：C-004 流量运营
      dou_plus_spent: {DOU+花费}
      dou_plus_roi: "{DOU+ ROI}"
    c003_self_review:               # 来源：C-003 内容总监自评
      script_quality_self_score: "{自评分数}"
      deviation_from_plan: "{偏离内容线的程度}"
  timestamp: "{ISO8601}"
```

#### 4.3.5 输出信号格式（闭环校准系统 → Agent引擎，经总线翻译）

```yaml
# Stage3 输出信号：复盘评估信号
bus_stage3_output:
  signal_id: "S3-{timestamp}-{seq}-RESP"
  signal_type: "retrospective_assessment"
  source: "YANG_STAGE3"
  target:
    primary: "C-006"               # 魔鬼代言人：基于偏差分析审计 Agent引擎 假设缺陷
    secondary: "C-001"             # 路径裁决：接收 Bump 信号后判定升级/降级
  payload:
    deviation_analysis:
      predicted_bucket: "{预测 Bucket}"
      actual_bucket: "{实际 Bucket}"
      deviation_direction: "OVERESTIMATED|UNDERESTIMATED|ALIGNED"
      deviation_magnitude: "{偏差幅度（Bucket 跨度）}"
      key_factors:                  # 偏差归因
        - factor: "{偏差主导因子}"
          weight: "{贡献权重}"
    observations:
      - id: "OBS-{NNN}"
        content: "{观察内容}"
        status: "proposed|active|absorbed|overturned"
        supporting_samples: {N}
        relates_to_pattern: "PAT-{NNN}"
    pattern_candidates:
      - id: "PAT-{NNN}"
        name: "{Pattern 名称}"
        status: "proposed|active"
        supporting_samples: {N}
        action: "CREATE|UPGRADE|DEPRECATE"
    hypothesis_verification:
      - hypothesis_id: "H2{NN}"
        prediction: "{原假设内容}"
        result: "CONFIRMED|REJECTED|PENDING"
        evidence: "{验证依据}"
    bump_evaluation:                # 条件输出：仅在触发 Bump 评估时存在
      triggered: true|false
      reason: "{触发原因}"
      validation_steps:
        step1_rescore: "PASS|FAIL"
        step2_cross_validation: "PASS|FAIL"
        step3_anomaly_detection: "PASS|FAIL"
        step4_wall_clock_stability: "PASS|FAIL"
        step5_cross_agent_audit: "PASS|FAIL"
      new_rubric_draft:
        version: "{新版本号}"
        changes: ["{变更1}", "{变更2}"]
      divergence_audit:              # 乖离率审计
        divergence_rate: "{乖离率}"
        audit_result: "PASS|WARN|FAIL"
        auditor_note: "{审计意见}"
    path_recommendation:             # 路径建议
      current_path: "默认|中度|高度|进化"
      recommended_path: "默认|中度|高度|进化"
      reason: "{建议理由}"
  calibration_context:
    calibration_samples: {N}
    confidence_level: "{speculative|medium|medium-high+}"
    benchmark_ratio: "{对标数据占比}%"
    samples_since_last_bump: {N}
  timestamp: "{ISO8601}"
```

#### 4.3.6 注入后的 Agent引擎 行为

1. **C-006 魔鬼代言人**：消费偏差分析报告，执行以下攻击：
   - 攻击 Agent引擎 假设缺陷："预测 Bucket [{X}]，实际 [{Y}]，偏差 [{Z}] 个等级。Agent引擎 在选题/脚本/运营环节的哪些假设被证伪？"
   - 攻击归因逻辑："闭环校准系统 归因为 [{主导因子}]，Agent引擎 是否认可？如认可，为什么这个因子在产线中没有被 C-003/C-004 识别？"
   - 审计乖离率："乖离率 [{rate}]，是否超过审计阈值？超过则建议 C-001 冻结 Bump。"

2. **C-001 路径裁决**：消费 Bump 评估信号和路径建议：
   - Bump 五步验证全部 PASS → C-001 批准 rubric 升级
   - Bump 被 C-006 审计否决 → C-001 宣布 Bump 冻结 3 个样本周期
   - 路径建议升级（如默认→中度）且 C-006 无致命反驳 → C-001 执行路径升级
   - 路径建议降级 → C-001 评估降级理由后裁决

---

## §5 Solo 模式定义

### 5.1 模式概述

Solo 模式是 闭环校准系统 **独立运行、Agent引擎 不激活**的工作模式。在此模式下，进化反馈总线仅充当 闭环校准系统输出翻译器和状态持久化层，不触发任何 Agent引擎。

### 5.2 触发场景

| 场景编号 | 场景描述 | 典型用户语句 |
|---------|---------|-------------|
| SOLO-1 | 用户只想评测已有脚本的数据潜力 | "帮我看看这个脚本能跑多少播放量"、"给这个稿子打个分" |
| SOLO-2 | 用户只做预测复盘，不涉及新内容创作 | "复盘一下上次那个视频"、"为什么预测 S 结果只有 B？" |
| SOLO-3 | 用户只想对标学习 | "分析一下这个对标账号最近的内容"、"帮我学一下这个博主的写作套路" |
| SOLO-4 | 用户只想做状态查询 | "我的校准样本多少了？"、"当前 rubric 是什么版本？" |
| SOLO-5 | 用户只想做 Bump 评估 | "检查一下是不是该升级 rubric 了" |
| SOLO-6 | 用户只想做选题生成 | "随便给我几个选题方向" |

### 5.3 Solo 模式启动判定

```
当用户请求满足以下条件之一时，系统进入 Solo 模式：

1. 用户请求中不包含内容产线完整流程的关键词
   （如"做一期"、"帮我写脚本"、"发布策略"等 产线触发词）
2. 用户请求中仅包含 闭环校准系统 子技能的关键词
   （如"评测"、"复盘"、"对标"、"打分"、"预测"、"选题"、"状态"、"校准"）
3. 用户显式声明 "solo" 或 "只用 闭环校准系统"
```

### 5.4 Solo 模式下的总线行为

```
┌─────────────────────────────────────────────────────────────┐
│                  Solo 模式 · 总线行为                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  用户请求 ──→ 总线 ──→ 判定为 Solo 模式                        │
│                │                                              │
│                ├──→ 激活 闭环校准系统 对应子技能                         │
│                │     · yang-predict（SOLO-1, SOLO-2）         │
│                │     · yang-retro（SOLO-2）                   │
│                │     · yang-learn-from（SOLO-3）              │
│                │     · yang-status（SOLO-4）                  │
│                │     · yang-bump（SOLO-5）                    │
│                │     · yang-seed + yang-trends（SOLO-6）      │
│                │                                              │
│                ├──→ Agent引擎 全部保持休眠状态                   │
│                │     · C-001~C-007 不激活                       │
│                │     · 产线不启动                            │
│                │                                              │
│                ├──→ 闭环校准系统 结果直接输出到当前对话                    │
│                │     · 经过总线格式翻译（人类可读）               │
│                │     · 标注 Solo 模式标识                       │
│                │                                              │
│                └──→ 状态持久化                                  │
│                      · 写入 .yang-state.json                 │
│                      · 更新 calibration_samples（如产生新样本）  │
│                      · 更新 pending_retros（如有未复盘预测）     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 5.5 Solo 模式输出格式

Solo 模式下的 闭环校准系统 输出经总线翻译后，以以下格式呈现给用户：

```markdown
## 🔵 Solo 模式 · 闭环校准系统 独立运行

> Agent引擎 未激活。以下结果由 Yang.skills 独立产出。

### {子技能名称} 结果

{结构化的 闭环校准系统 输出内容，使用 闭环校准系统 原生格式}

---

📊 **状态更新**：结果已写入 `.yang-state.json`
- 校准样本数：{calibration_samples}
- 置信度：{confidence_derived}
- 本次操作类型：{prediction|retro|benchmark|status|bump|seed}

💡 **如需启动完整 产线**，请触发 Agent引擎 入口（如"做一期新内容"）。
```

### 5.6 Solo 模式下的 .yang-state.json 写入规则

| Solo 场景 | 写入操作 |
|-----------|---------|
| SOLO-1（脚本评测） | 写入 `predictions` 队列（新建一条预测记录），但不触发 Agent引擎 侧假设创建 |
| SOLO-2（复盘） | 如果预测记录有对应的发布数据 → 写入 `observations` + 更新 `calibration_samples`；否则仅更新观察 |
| SOLO-3（对标学习） | 写入 `benchmarks` 队列，按三通道规则贡献 calibration_samples |
| SOLO-4（状态查询） | 只读操作，不写入 |
| SOLO-5（Bump 评估） | 如触发 Bump → 写入 `rubric.version` + `bump_history` |
| SOLO-6（选题生成） | 写入 `candidate_pool`，不触发 Agent引擎 侧内容线更新 |

---

## §6 信号方向性约束

### 6.1 约束原理

三元协同架构的核心设计原则是**信息边界**：Agent引擎 和 闭环校准系统 各自维护独立的内部状态和推理过程，仅通过总线交换经过翻译的**信号**，而非原始状态数据。

### 6.2 Agent引擎 → 闭环校准系统 方向约束

> Agent引擎 只能通过总线注入点向 闭环校准系统 传递"创作意图信号"，不得传递 Agent引擎 内部推理过程或 Agent 间通信内容。

**允许传递的信号类型**：

| 信号类别 | 具体内容 | 传递注入点 | 格式要求 |
|---------|---------|-----------|---------|
| 选题方向信号 | 赛道、城市、对标清单、用户兴趣、内容线规划 | Stage1 | 必须使用 §4.1.4 定义的 `bus_stage1_input` 格式 |
| 脚本初稿信号 | 脚本全文、选题标题、切入角度、钩子策略、对标参考 | Stage2 | 必须使用 §4.2.4 定义的 `bus_stage2_input` 格式 |
| 发布后数据信号 | 播放量、互动数据、留存曲线、投流 ROI、观众画像 | Stage3 | 必须使用 §4.3.4 定义的 `bus_stage3_input` 格式 |

**禁止传递的内容**：

- Agent引擎 之间的内部通信内容（如 C-001 对 C-003 的指令、C-006 的攻击意见）
- Agent引擎 假设库中的原始假设记录（H1xx/H2xx）
- Agent引擎 路径判定过程中的分歧度量化数据
- C-007 元认知对齐过程中的各 Agent 元认知声明
- 任何 Agent引擎 内部状态的数据结构（如 `Agent引擎_state.json`、`agent_dispatch_log`）

### 6.3 闭环校准系统 → Agent引擎 方向约束

> 闭环校准系统 只能通过总线注入点向 Agent引擎 传递"预测/评估信号"，不得传递 闭环校准系统 内部推理过程或原始状态数据。

**允许传递的信号类型**：

| 信号类别 | 具体内容 | 传递注入点 | 格式要求 |
|---------|---------|-----------|---------|
| 选题推荐信号 | 候选池、Bucket 初评、热点整合、推荐排序 | Stage1 | 必须使用 §4.1.5 定义的 `bus_stage1_output` 格式 |
| 盲预测信号 | Bucket、7 组件评分、情绪曲线、rubric 评分 | Stage2 | 必须使用 §4.2.5 定义的 `bus_stage2_output` 格式 |
| 复盘评估信号 | 偏差分析、观察记录、Pattern 候选、假设验证、Bump 提案 | Stage3 | 必须使用 §4.3.5 定义的 `bus_stage3_output` 格式 |

**禁止传递的内容**：

- 闭环校准系统 内部的 `.yang-state.json` 原始数据（Agent引擎 不应直接读取）
- 闭环校准系统 内部的 `rubric_notes.md` 原始内容（Agent引擎 不应直接读取）
- 闭环校准系统 内部的校准历史记录（calibration 日志）
- 闭环校准系统 yang-predict 的内部推理链（7 组件判定依据的细节推导）
- 闭环校准系统 yang-bump 的五步验证内部计算过程
- 任何 闭环校准系统 内部状态的数据结构

### 6.4 信息边界违规检测

总线在每个注入点执行以下校验：

```
输入校验（Agent引擎 → 闭环校准系统）：
  ✓ 信号格式是否符合 bus_stage{N}_input schema
  ✓ payload 中是否包含禁止传递的 Agent引擎 内部状态数据
  ✓ source 字段是否正确标识为 Agent引擎 侧的触发位置

输出校验（闭环校准系统 → Agent引擎）：
  ✓ 信号格式是否符合 bus_stage{N}_output schema
  ✓ payload 中是否包含禁止传递的 闭环校准系统 内部状态数据
  ✓ 置信度标注是否符合 §7 定义的传播规则
  ✓ target 字段是否正确标识注入目标 Agent引擎

违规处理：
  · 格式不符合 schema → 拒绝传递，返回 BUS_ERR_FORMAT
  · 包含禁止数据 → 拒绝传递，返回 BUS_ERR_BOUNDARY
  · 置信度标注违规 → 警告但允许传递，记录 BUS_WARN_CONFIDENCE
```

### 6.5 互不污染保证

| 保证项 | Agent引擎 侧 | 闭环校准系统 侧 |
|--------|--------|--------|
| 状态独立性 | Agent引擎 不读取 `.yang-state.json` | 闭环校准系统 不读取 Agent引擎 假设库 |
| 推理独立性 | Agent引擎 不依赖 闭环校准系统 原始推理链做决策 | 闭环校准系统 不依赖 Agent引擎 通信内容做校准 |
| 演化独立性 | Agent引擎路径判定逻辑可独立升级 | 闭环校准系统 rubric 版本可独立演进 |
| 故障独立性 | 闭环校准系统 故障不影响 产线继续运行 | Agent引擎 故障不影响 闭环校准系统 已持久化的校准数据 |

---

## §7 置信度标注传播规则

### 7.1 calibration_samples 计算

置信度标注的基础是 `calibration_samples`，按三通道混合公式计算：

```
calibration_samples = 
    SUM(自己发布的视频) × 1.0
  + SUM(对标爆款深度分析) × 0.5   // 上限 3 条计入
  + SUM(对标低播放深度分析) × 0.3  // 上限 2 条计入
  + SUM(用户确认为"代表作"的历史视频) × 1.0
```

> 注：`calibration_samples` 取上述公式计算后向下取整的整数值。

### 7.2 置信度等级与标注规则

| calibration_samples | 置信度等级 | 标注文本 | 传播行为 |
|---------------------|----------|---------|---------|
| < 5 | 低置信度 | `⚠️ speculative（低置信度）` | 所有 闭环校准系统 输出必须标注此标签。Agent引擎 接收信号后采用保守策略（路径降一档、投流设止损线、建议标注"推测性"）。 |
| 5 ~ 9 | 中等置信度 | `medium 置信度` | 闭环校准系统 输出标注 medium。Agent引擎 接收信号后正常消费，但 C-006 必须额外审计偏差风险。 |
| ≥ 10 | 中高置信度 | `medium-high+ 置信度` | 闭环校准系统 输出标注 medium-high+。Agent引擎 接收信号后进入数据驱动模式，对标数据参考权重降低。 |
| ≥ 20 | 高置信度 | `high 置信度` | 闭环校准系统 输出标注 high。Agent引擎 可进入"进化路径"，对标分析转为 sanity check 角色。 |

### 7.3 对标数据占比降档规则

> 当 `对标数据贡献的 calibration_samples 权重 / 总 calibration_samples > 50%` 时，**自动将置信度降一档**。

**降档规则表**：

| 原始置信度等级 | 对标数据占比 > 50% 后的等级 | 标注文本附加说明 |
|-------------|--------------------------|----------------|
| medium-high+ → | medium | "⚠️ 对标数据占比 {ratio}%，置信度由 medium-high+ 降为 medium" |
| medium → | speculative | "⚠️ 对标数据占比 {ratio}%，置信度由 medium 降为 speculative" |
| high → | medium-high+ | "⚠️ 对标数据占比 {ratio}%，置信度由 high 降为 medium-high+" |
| speculative → | speculative | 不再降档（已是底限），附加说明："对标数据占比 {ratio}%，置信度保持 speculative" |

**计算示例**：

```
场景 A：
  · 自发布视频：2 条 × 1.0 = 2.0
  · 对标爆款深度分析：3 条 × 0.5 = 1.5
  · calibration_samples = floor(3.5) = 3 → speculative
  · 对标占比 = 1.5 / 3.5 = 42.9% → 不触发降档
  · 最终标注：⚠️ speculative（低置信度）

场景 B：
  · 自发布视频：1 条 × 1.0 = 1.0
  · 对标爆款深度分析：3 条 × 0.5 = 1.5
  · 对标低播放分析：2 条 × 0.3 = 0.6
  · calibration_samples = floor(3.1) = 3 → speculative
  · 对标占比 = (1.5 + 0.6) / 3.1 = 67.7% → 触发降档
  · 原始等级：speculative → 不再降档（已是底限）
  · 最终标注：⚠️ speculative（低置信度，对标数据占比 67.7%）

场景 C：
  · 自发布视频：5 条 × 1.0 = 5.0
  · 对标爆款深度分析：3 条 × 0.5 = 1.5
  · calibration_samples = floor(6.5) = 6 → medium
  · 对标占比 = 1.5 / 6.5 = 23.1% → 不触发降档
  · 最终标注：medium 置信度

场景 D：
  · 自发布视频：2 条 × 1.0 = 2.0
  · 对标爆款深度分析：3 条 × 0.5 = 1.5
  · 对标低播放分析：2 条 × 0.3 = 0.6
  · 代表作历史视频：2 条 × 1.0 = 2.0
  · calibration_samples = floor(6.1) = 6 → medium
  · 对标占比 = (1.5 + 0.6) / 6.1 = 34.4% → 不触发降档
  · 最终标注：medium 置信度

场景 E：
  · 自发布视频：1 条 × 1.0 = 1.0
  · 对标爆款深度分析：3 条 × 0.5 = 1.5
  · 对标低播放分析：2 条 × 0.3 = 0.6
  · 代表作历史视频：2 条 × 1.0 = 2.0
  · calibration_samples = floor(5.1) = 5 → medium
  · 对标占比 = (1.5 + 0.6) / 5.1 = 41.2% → 不触发降档
  · 最终标注：medium 置信度

场景 F：
  · 自发布视频：2 条 × 1.0 = 2.0
  · 对标爆款深度分析：3 条 × 0.5 = 1.5
  · 对标低播放分析：2 条 × 0.3 = 0.6
  · calibration_samples = floor(4.1) = 4 → speculative
  · 对标占比 = (1.5 + 0.6) / 4.1 = 51.2% → 触发降档
  · 原始等级：speculative → 不再降档（已是底限）
  · 最终标注：⚠️ speculative（低置信度，对标数据占比 51.2%，本已为底限）
```

### 7.4 置信度在不同注入点的传播行为

| 注入点 | speculative 行为 | medium 行为 | medium-high+ 行为 |
|--------|-----------------|------------|-------------------|
| Stage1（选题） | 选题推荐标注"推测性"，建议从候选池中选择但是谨慎投入。C-001 路径判定降一档。 | 正常推荐，标注 medium 置信度。C-001 按标准路径判定。 | 高置信推荐。对标数据权重降低，自有数据主导。 |
| Stage2（盲预测） | Bucket 预测标注 speculative，C-004 投流策略以保守预算为主。Hook 保护段仍锁定。 | 正常预测，C-004 投流策略可参考 Bucket 但设止损。 | 高置信预测。C-004 投流策略可更积极但 C-006 仍执行攻击。 |
| Stage3（复盘） | 偏差分析标注 speculative，Bump 功能可用但不建议执行。观察记录仅为 proposed。 | 正常偏差分析。连续 ≥3 次同向偏差可触发 Bump 评估。 | 高置信偏差分析。Bump 进入数据驱动模式，对标参考权重降低。 |

### 7.5 置信度升级/降级事件

```
升级事件：
  · 每新增 1 条自发布复盘 → calibration_samples +1 → 重新计算置信度
  · 每新增 1 条对标深度分析 → 按权重贡献 → 重新计算置信度
  · 对标数据占比首次降至 50% 以下 → 解除降档 → 置信度回升一档

降级事件：
  · 发现 ≥2 次重大预测偏差（偏差 ≥2 个 Bucket 等级）→ 置信度降一档，冻结 3 个样本
  · 对标数据占比升至 50% 以上 → 自动降档
  · C-006 审计发现系统性偏差模式 → 降一档直到偏差消除
```

---

## §8 总线运行时状态机

### 8.1 总线运行模式

```
                        ┌─────────────┐
                        │   总线待机    │
                        └──────┬──────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
          ┌──────────┐  ┌──────────┐  ┌──────────┐
          │ Stage1   │  │ Stage2   │  │ Stage3   │
          │ Hook     │  │ Hook     │  │ Hook     │
          │ 激活     │  │ 激活     │  │ 激活     │
          └────┬─────┘  └────┬─────┘  └────┬─────┘
               │              │              │
               ▼              ▼              ▼
          ┌─────────────────────────────────────┐
          │        信号翻译 + 路由 + 校验          │
          └─────────────────┬───────────────────┘
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
           ┌────────┐ ┌────────┐ ┌────────┐
           │ 闭环校准系统    │ │ Agent引擎    │ │ Solo   │
           │ 激活   │ │ 注入   │ │ 模式   │
           └───┬────┘ └───┬────┘ └───┬────┘
               │          │          │
               └──────────┼──────────┘
                          ▼
                    ┌──────────┐
                    │ 总线待机  │
                    └──────────┘
```

### 8.2 总线状态标志

| 状态标志 | 含义 | 影响 |
|---------|------|------|
| BUS_IDLE | 总线待机，无激活的注入点 | 正常状态 |
| BUS_STAGE1_ACTIVE | Stage1 Hook 已激活，等待 闭环校准系统 响应 | 选题信号处理中 |
| BUS_STAGE2_ACTIVE | Stage2 Hook 已激活，等待 闭环校准系统 响应 | 盲预测信号处理中 |
| BUS_STAGE3_ACTIVE | Stage3 Hook 已激活，等待 闭环校准系统 响应 | 复盘信号处理中 |
| BUS_SOLO_ACTIVE | Solo 模式激活 | Agent引擎 全部休眠 |
| BUS_DEGRADED | 总线降级模式（闭环校准系统 不可用） | Agent引擎 独立运行，闭环校准系统 信号缺失 |
| BUS_ERROR | 总线错误状态 | 需人工介入 |

---

## §9 异常处理与降级策略

### 9.1 闭环校准系统 不可用时的降级

```
当 闭环校准系统 不可用时（文件缺失、状态损坏、或环境不支持）：

1. 总线自动进入 BUS_DEGRADED 降级模式
2. Agent引擎 v5 以原版模式独立运行（不依赖任何 闭环校准系统 信号）
3. 所有注入点返回空信号，标注 BUS_DEGRADED
4. Agent引擎 正常产线运行，但以下功能暂时不可用：
   · 盲预测（Bucket 预判）
   · Rubric 维度自动评分
   · T+3 偏差分析
   · Bump 自动评估
   · 情绪曲线分析
5. 当 闭环校准系统 恢复后，总线自动退出降级模式
6. 降级期间产生的 Agent引擎 数据（脚本、发布数据）在 闭环校准系统 恢复后补入复盘队列
```

### 9.2 注入点超时处理

| 注入点 | 超时时间 | 超时行为 |
|--------|---------|---------|
| Stage1 | 30 秒 | 选题推荐信号为"降级空信号"。Agent引擎 基于对标数据和用户输入自行选题。 |
| Stage2 | 60 秒 | 盲预测信号为"降级空信号"。Agent引擎 不做假设创建，脚本直接进入发布流程。 |
| Stage3 | 90 秒 | 复盘信号为"降级空信号"。Agent引擎 自行做基础复盘，不触发 Bump 流程。 |

### 9.3 信号校验失败处理

| 错误码 | 含义 | 处理方式 |
|--------|------|---------|
| BUS_ERR_FORMAT | 信号格式不符合 schema | 拒绝传递，返回错误详情。发送方需修正格式后重试。 |
| BUS_ERR_BOUNDARY | 信号包含信息边界违规数据 | 拒绝传递，记录违规详情。发送方需剥离敏感数据后重试。 |
| BUS_ERR_CONFIDENCE | 置信度标注计算错误 | 警告，自动修正置信度标注后传递。记录修正日志。 |
| BUS_ERR_TIMEOUT | 注入点超时 | 发送降级空信号。记录超时日志。 |
| BUS_WARN_CONFIDENCE | 置信度标注与传播规则不完全匹配 | 允许传递但附加警告标记。 |

---

## 附录 A：注入点信号格式完整规范

### A.1 通用信号头

所有通过总线传递的信号 MUST 包含以下通用头部字段：

```yaml
signal_header:
  protocol_version: "2.0"                    # 总线协议版本
  signal_id: "{STAGE}-{timestamp}-{seq}"     # 信号唯一标识
  direction: "AGENT_TO_闭环校准系统 | 闭环校准系统_TO_AGENT"       # 信号方向
  stage: "STAGE1 | STAGE2 | STAGE3 | SOLO"   # 注入点标识
  timestamp: "{ISO8601}"                      # 信号创建时间
  ttl_seconds: {N}                            # 信号有效期（超时后失效）
```

### A.2 信号版本兼容性

```
协议版本 2.0：
  · 兼容 Agent引擎 v5（15,967 行，不做修改）
  · 兼容 闭环校准系统 原版（7,607 行，不做修改）
  · 总线层独立版本管理

信号格式演进规则：
  · 新增字段 → 向后兼容（旧版消费者忽略新字段）
  · 删除字段 → 标记 deprecated，保留 2 个大版本后删除
  · 字段类型变更 → 大版本升级，旧版信号拒绝
```

---

---

## 附录 B：总线消息格式规范

### B.1 消息整体结构

所有通过进化反馈总线传递的消息 MUST 遵循"消息头 / 消息体 / 消息尾"三层结构：

```yaml
# ═══════════════════════════════════════════════
# 消息头（Message Header）—— 路由与元数据
# ═══════════════════════════════════════════════
header:
  protocol_version: "2.0"                       # 总线协议版本
  message_id: "{STAGE}-{timestamp}-{seq}"        # 消息唯一标识（全局唯一）
  correlation_id: "{关联的请求消息ID}"             # 请求-响应配对（响应消息必填）
  direction: "AGENT_TO_YANG | YANG_TO_AGENT"     # 信号方向
  stage: "STAGE1 | STAGE2 | STAGE3 | SOLO"       # 注入点标识
  priority: "URGENT | NORMAL | LOW"              # 消息优先级（见 B.2）
  timestamp: "{ISO8601}"                          # 消息创建时间
  ttl_seconds: {N}                                # 消息有效期（超时后失效）
  retry_count: {N}                                # 已重试次数（初始为 0）
  max_retries: {N}                                # 最大重试次数（见 B.4）
  source_service: "{发送方服务标识}"                # 如 "AGENT_STAGE1" / "YANG_STAGE2"
  target_service: "{接收方服务标识}"                # 如 "YANG_STAGE1" / "C-007"

# ═══════════════════════════════════════════════
# 消息体（Message Body）—— 业务载荷
# ═══════════════════════════════════════════════
payload:
  # 具体业务数据，格式由各 Stage 的 bus_stage{N}_input/output 定义
  # 见 §4.1.4 / §4.2.4 / §4.3.4（输入）和 §4.1.5 / §4.2.5 / §4.3.5（输出）
  ...

# ═══════════════════════════════════════════════
# 消息尾（Message Trailer）—— 校验与追踪
# ═══════════════════════════════════════════════
trailer:
  checksum: "{SHA-256 of payload}"               # 消息体校验和（防篡改/防损坏）
  encoding: "yaml"                                # 消息体编码格式
  schema_version: "{payload schema 版本}"          # 业务 schema 版本号
  trace_id: "{分布式追踪ID}"                        # 跨注入点追踪（可选，用于端到端调试）
  annotations:                                    # 附加标注（可选）
    - key: "{标注键}"
      value: "{标注值}"
```

### B.2 消息头字段详细规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `protocol_version` | string | 是 | 总线协议版本，当前为 "2.0"。接收方 MUST 校验版本兼容性 |
| `message_id` | string | 是 | 全局唯一消息标识，格式：`{STAGE}-{UNIX_TIMESTAMP}-{4位序号}` |
| `correlation_id` | string | 条件 | 响应消息必填，值为对应请求消息的 `message_id` |
| `direction` | enum | 是 | 信号方向枚举，仅允许 `AGENT_TO_YANG` 或 `YANG_TO_AGENT` |
| `stage` | enum | 是 | 注入点标识，仅允许 `STAGE1` / `STAGE2` / `STAGE3` / `SOLO` |
| `priority` | enum | 是 | 消息优先级，见 §B.3 |
| `timestamp` | ISO8601 | 是 | 消息创建时间，精度到毫秒 |
| `ttl_seconds` | integer | 是 | 消息有效期，超时后消息失效不再处理 |
| `retry_count` | integer | 是 | 已重试次数，初始为 0 |
| `max_retries` | integer | 是 | 最大重试次数，见 §B.4 |
| `source_service` | string | 是 | 发送方服务标识 |
| `target_service` | string | 是 | 接收方服务标识 |

### B.3 消息尾字段详细规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `checksum` | string | 是 | 消息体的 SHA-256 校验和，用于检测传输损坏 |
| `encoding` | enum | 是 | 消息体编码格式，当前仅支持 `yaml` |
| `schema_version` | string | 是 | 业务 payload 的 schema 版本号 |
| `trace_id` | string | 否 | 分布式追踪 ID，用于跨注入点端到端调试 |
| `annotations` | array | 否 | 附加标注键值对，用于传递非标准元数据 |

---

## 附录 C：消息优先级定义

### C.1 优先级等级与判定规则

总线消息分为三个优先级等级，决定消息的处理顺序和资源分配：

| 优先级 | 标识 | 判定规则 | 处理策略 |
|--------|------|---------|---------|
| **紧急** | `URGENT` | 满足以下任一条件：<br>① Bump 评估信号（UPGRADE_BUMP / DOWNGRADE_BUMP）<br>② 乖离率 ≥ 1.0（偏差 ≥ 100%）的复盘信号<br>③ 系统降级/恢复信号（BUS_DEGRADED 切换）<br>④ calibration_samples 跨越置信度等级边界的事件 | ① 立即处理，跳过排队<br>② 分配最高计算资源<br>③ 超时时间加倍（Stage1: 60s / Stage2: 120s / Stage3: 180s）<br>④ 失败后立即重试，不进入退避等待 |
| **普通** | `NORMAL` | 不满足 URGENT 也不满足 LOW 的所有标准业务信号：<br>① Stage1 选题意图信号<br>② Stage2 脚本定稿信号<br>③ Stage3 常规复盘信号（乖离率 < 1.0）<br>④ Observation / Pattern 候选信号 | ① 按到达顺序排队处理<br>② 标准超时时间（Stage1: 30s / Stage2: 60s / Stage3: 90s）<br>③ 失败后按指数退避重试 |
| **低优先级** | `LOW` | 满足以下任一条件：<br>① 定期热点扫描信号（TRG-1.4 触发）<br>② CALIBRATION_MATURE 信号（非紧急模式切换）<br>③ Solo 模式下的状态查询（SOLO-4）<br>④ 对标数据时间折价警告信号 | ① 排队处理，在 NORMAL 消息之后<br>② 超时时间减半（Stage1: 15s / Stage2: 30s / Stage3: 45s）<br>③ 超时后不重试，直接丢弃并记录日志<br>④ 资源紧张时可延迟处理 |

### C.2 优先级动态升级规则

消息在以下情况下可被动态升级优先级：

```
优先级升级触发条件：
  · NORMAL → URGENT：
    - 消息处理过程中检测到乖离率 ≥ 1.0
    - 连续 ≥3 次同向偏差在消息处理中被发现
    - C-006 审计结果为 FAIL

  · LOW → NORMAL：
    - 低优先级消息在队列中等待超过 60 秒
    - 定期热点扫描发现重大热点变化（热点等级 = 爆发级）
    - CALIBRATION_MATURE 条件满足且 calibration_samples 首次达到阈值

优先级降级触发条件：
  · URGENT → NORMAL：
    - 紧急消息处理完成后的后续跟踪消息
    - Bump 评估已被 C-001 裁决完成

  · NORMAL → LOW：
    - 同类消息在 24 小时内重复发送（去重后降级）
    - 消息的 calibration_samples = 0 且非首次信号
```

### C.3 优先级与注入点的交叉矩阵

| 注入点 | URGENT 典型场景 | NORMAL 典型场景 | LOW 典型场景 |
|--------|----------------|-----------------|-------------|
| Stage1 | Bump 触发的选题方向紧急调整 | 常规选题意图信号 | 定期热点扫描 |
| Stage2 | D-Tier 预测触发的紧急否决 | 脚本定稿盲预测 | Solo 模式脚本评测 |
| Stage3 | 乖离率 ≥ 1.0 的复盘 | 常规 T+3 复盘 | 状态查询 / 对标折价警告 |

---

## 附录 D：消息重试与死信队列机制

### D.1 重试策略

总线对处理失败的消息执行结构化重试，策略如下：

```
重试策略总览：

  ┌──────────────────────────────────────────────────────────────┐
  │                    消息处理失败                                │
  │                        │                                      │
  │            ┌───────────┼───────────┐                          │
  │            ▼           ▼           ▼                          │
  │     可重试错误    不可重试错误   超时                           │
  │     (格式错误    (边界违规    (TTL 耗尽                       │
  │      校验和      信息边界      处理超时)                       │
  │      不匹配)    违规)                                         │
  │         │           │           │                              │
  │         ▼           ▼           ▼                              │
  │     进入重试队列  直接进死信队列  进入重试队列                    │
  │         │                       │                              │
  │         ▼                       ▼                              │
  │     指数退避重试            指数退避重试                         │
  │         │                       │                              │
  │         ▼                       ▼                              │
  │     重试成功？              重试成功？                           │
  │     ├── 是 → 完成          ├── 是 → 完成                       │
  │     └── 否 → 重试次数+1    └── 否 → 重试次数+1                  │
  │              │                    │                             │
  │              ▼                    ▼                             │
  │        达到 max_retries?     达到 max_retries?                  │
  │        ├── 是 → 进死信队列   ├── 是 → 进死信队列                │
  │        └── 否 → 继续退避     └── 否 → 继续退避                  │
  └──────────────────────────────────────────────────────────────┘
```

### D.2 重试参数配置

| 优先级 | 最大重试次数 (`max_retries`) | 退避策略 | 首次退避时间 | 退避上限 |
|--------|---------------------------|---------|------------|---------|
| URGENT | 5 | 指数退避 + 抖动 | 1 秒 | 30 秒 |
| NORMAL | 3 | 指数退避 + 抖动 | 2 秒 | 60 秒 |
| LOW | 1 | 固定间隔 | 5 秒 | 5 秒 |

退避时间计算公式：

```
backoff = min(base_delay × 2^retry_count + random_jitter, max_backoff)

其中：
  base_delay  = 首次退避时间（按优先级）
  retry_count = 当前重试次数（从 0 开始）
  random_jitter = random(0, base_delay × 0.1)  // 防止重试风暴
  max_backoff = 退避上限（按优先级）
```

### D.3 可重试错误 vs 不可重试错误

| 错误类型 | 错误码 | 可重试？ | 说明 |
|---------|--------|---------|------|
| 格式校验失败 | `BUS_ERR_FORMAT` | 是（发送方可修正后重试） | payload 格式不符合 schema |
| 校验和不匹配 | `BUS_ERR_CHECKSUM` | 是（可能是传输损坏） | trailer.checksum 与实际不一致 |
| 处理超时 | `BUS_ERR_TIMEOUT` | 是 | 接收方未在 TTL 内完成处理 |
| 闭环校准系统 暂时不可用 | `BUS_ERR_SERVICE_DOWN` | 是 | 闭环校准系统 服务临时不可达 |
| 信息边界违规 | `BUS_ERR_BOUNDARY` | 否 | payload 包含禁止传递的数据，重试无意义 |
| 置信度计算错误 | `BUS_ERR_CONFIDENCE` | 否 | 需人工修正后重新发送 |
| 版本不兼容 | `BUS_ERR_VERSION` | 否 | protocol_version 不兼容，需升级 |

### D.4 死信队列（Dead Letter Queue）

当消息重试耗尽后，进入死信队列（DLQ）。死信队列是总线最后的保障机制：

```
死信队列规范：

  存储位置：
    .yang-state.json → dead_letter_queue[] 数组

  死信记录格式：
    {
      "original_message_id": "{原消息ID}",
      "original_priority": "URGENT|NORMAL|LOW",
      "original_stage": "STAGE1|STAGE2|STAGE3|SOLO",
      "error_code": "{最终错误码}",
      "error_message": "{错误详情}",
      "retry_attempts": {N},               // 实际重试次数
      "first_attempt_at": "{ISO8601}",      // 首次尝试时间
      "last_attempt_at": "{ISO8601}",       // 最后一次尝试时间
      "original_payload_summary": "{payload 摘要（前200字符）}",
      "requires_manual_intervention": true|false
    }

  死信处理策略：
    ┌──────────────────────────────────────────────────────────────┐
    │  URGENT 消息进入死信队列：                                     │
    │    · requires_manual_intervention = true                     │
    │    · 总线 MUST 在下次 Agent引擎 产线循环中向 C-001 上报        │
    │    · C-001 决定：手动重发 / 降级处理 / 放弃                    │
    │    · 死信记录保留 30 天后自动清理                               │
    │                                                              │
    │  NORMAL 消息进入死信队列：                                     │
    │    · requires_manual_intervention = false                    │
    │    · 总线记录日志，不主动上报                                   │
    │    · 产线继续运行（降级空信号替代）                              │
    │    · 死信记录保留 14 天后自动清理                               │
    │                                                              │
    │  LOW 消息进入死信队列：                                        │
    │    · requires_manual_intervention = false                    │
    │    · 仅记录日志，不影响任何业务流程                              │
    │    · 死信记录保留 7 天后自动清理                                │
    └──────────────────────────────────────────────────────────────┘

  死信队列容量限制：
    · 最大条目数：100 条
    · 超出后按 FIFO 淘汰最旧记录
    · yang-status 可查询当前死信队列状态

  死信队列监控指标：
    · dlq_size：当前死信队列大小
    · dlq_urgent_count：紧急消息死信数量
    · dlq_oldest_age_seconds：最旧死信的存活时间
    · dlq_total_entries：历史死信总条目数（累计）
```

### D.5 重试与死信队列的端到端示例

```
场景：Stage2 盲预测信号处理失败

T0: Agent引擎 发送 Stage2 脚本定稿信号
    header.priority = NORMAL
    header.retry_count = 0
    header.max_retries = 3
    → 总线翻译 → 发送至 闭环校准系统

T0+60s: 闭环校准系统 处理超时（BUS_ERR_TIMEOUT）
    → retry_count = 1
    → 退避 2s + jitter(0~0.2s)

T0+62.1s: 第 1 次重试
    → 闭环校准系统 仍然超时
    → retry_count = 2
    → 退避 4s + jitter(0~0.4s)

T0+66.4s: 第 2 次重试
    → 闭环校准系统 返回 BUS_ERR_FORMAT（payload 格式错误）
    → retry_count = 3
    → 退避 8s + jitter(0~0.8s)

T0+74.9s: 第 3 次重试（最后一次）
    → 闭环校准系统 仍然返回 BUS_ERR_FORMAT
    → retry_count = 3 = max_retries
    → 消息进入死信队列

死信记录：
    {
      "original_message_id": "S2-1747264800-0001",
      "original_priority": "NORMAL",
      "original_stage": "STAGE2",
      "error_code": "BUS_ERR_FORMAT",
      "error_message": "payload.script.content 字段缺失",
      "retry_attempts": 3,
      "first_attempt_at": "2026-06-14T10:00:00.000Z",
      "last_attempt_at": "2026-06-14T10:01:14.900Z",
      "original_payload_summary": "bus_stage2_input: signal_id=S2-1747264800-0001, signal_type=script_finalized...",
      "requires_manual_intervention": false
    }

Agent引擎 侧行为：
    → 总线发送降级空信号（Stage2 超时降级）
    → Agent引擎 不创建 H2xx 假设记录
    → 脚本直接进入发布流程
    → C-007 记录"Stage2 预测缺失，本轮无盲预测"
```

---

> **本文档版本**：v2.0  
> **创建日期**：2026-05-11  
> **维护者**：阿洋  
> **下次评审日期**：每 3 个 Bump 周期或每季度，以先到者为准。  

> **引用路径**：  
> - 总线协议（本文档）：`evolution-bus/bus-protocol.md`  
> - Stage1 Hook 实现：`evolution-bus/hooks/stage1-seed-hook.md`  
> - Stage2 Hook 实现：`evolution-bus/hooks/stage2-predict-hook.md`  
> - Stage3 Hook 实现：`evolution-bus/hooks/stage3-retro-hook.md`  
> - 信号翻译规则：`evolution-bus/bridge-rules.md`  
> - 闭环校准系统：`skills/yang-*/SKILL.md`（全部18个外部子skill）  
> - 多Agent运行时引擎：独立Agent引擎Host系统（不做修改，Yang.skills作为总线挂载入Host）