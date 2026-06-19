---
name: yang-recommend
version: "2.1"
description: 从 candidates.md 按当前 rubric 排序推荐 top N 选题，每条带 composite + 一句 rationale + 锚点对比，并按 buffer 颜色调整策略。**candidates 不存在时给引导而非报错**。触发词："推荐选题"/"next topic"/"下一篇做什么"/"recommend topics"/"挑一个选题"。
trigger-words: [推荐选题, next topic, 下一篇做什么, recommend topics, 挑一个选题, 选哪个, 推荐拍什么, 帮我选题]
tags: [recommend, 候选池排序, buffer策略, 选题推荐, composite排序]
author: 阿洋
argument-hint: "[--top N] [--filter tier1|all|safe|risky]"
allowed-tools: Read, Glob, Grep
---

# yang-recommend · 候选池排序推荐

读 candidates.md → 按 composite 排序 → 输出 top N 推荐，每条带评分细节 + 锚点对比 + 推荐理由。

## Overview

```
[用户：推荐选题]
  ↓
[Phase 0: 检查 candidates.md 存在性]   ← 不存在则引导，不报错
  ↓
[Phase 1: 解析 candidates 列表]
  ↓
[Phase 2: 过滤（tier / 安全性 / 已发过）]
  ↓
[Phase 2.5: Buffer 颜色覆盖（最高优先级）]
  ↓
[Phase 3: 排序 by composite + 选 1 稳 + 1 实验 + 找锚点]
  ↓
[Phase 4: 输出 top N + 每条 rationale + 锚点对比]
```

**搜索意图选题推荐**：推荐列表中至少1条来自Channel E（搜索意图），确保不全是热榜驱动。Channel E的内容空白检测选题优先级等同🅰。

## Constants

- **TOP_N = 5** — 默认推荐 top 5
- **STRATEGY = stable+experimental** — 推 ≥2 时按 [cadence-protocol.md](../../shared-protocols/cadence-protocol.md) 的"1 稳分 + 1 实验性"策略；推 1 时只推 top 稳分
- **POOL_PATH = candidates.md** — 候选池路径
- **EXCLUDE_PUBLISHED = true** — 排除已发布的（与 `predictions/*.md` 去重）
- **EXCLUDE_REJECTED = true** — 排除用户主动跳过的（`tier=skip`）
- **REQUIRE_SCORED = true** — 只推荐已打分的——避免推没读过的素材
- **DUPLICATE_CATEGORY_LOOKBACK** — 派生自 `state.target_publish_cadence_days`：max(3, cadence_days × 3) 天内已发同类目候选不推（避免审美疲劳）

> 💡 调用时覆盖：`/yang-recommend --top 3 --filter safe`

## Inputs

| 必填 | 来源 |
|---|---|
| `candidates.md` | 用户项目根 |
| `predictions/*.md` | 用于去重 |
| `.yang-state.json` | 当前 rubric_version / buffer 计算 |

## Workflow

### Phase 0: 候选池存在性检查

读 `candidates.md`：

| 状态 | 处理 |
|---|---|
| 文件不存在 | **不报错**。输出引导：见下方"无候选池引导" |
| 文件存在但空（< 1 个 entry） | 同上 |
| 文件存在且非空 | 进入 Phase 1 |

**无候选池引导**（核心：不让用户第一次遇到 yang-recommend 时被劝退）：

```
你目前没有候选池（candidates.md 不存在或为空）。

绝大部分人没有候选池——这很正常。四个建立方式，挑一个：

1. 🌱 [推荐] 跑 /yang-seed
   一次性的种子动作：3 个问题（兴趣 / 调性 / 红线）→ 四通道选题
   （A 知识库选题法 · B 竞品数据库 · C 热点 · D 高赞评论金句）→ 输出候选让你挑。
   说："找选题" 或 "seed"

2. 🔥 [日常补充] 用 /yang-trends 抓带打分的候选
   说："抓热点" — 零配置多源聚合器从 微博/知乎/B站/百度/抖音/头条 各拉 N 条
   适合已经跑过 /yang-seed、想日常补充候选池的用户

3. ✍️  手动建：把候选标题贴进 candidates.md，每行一条
   我会自动给每条粗打分

4. 📋 从外部源导入：跑 /yang-init 配置 adapter

你也可以跳过候选池，直接给我具体稿子说"启动预测"。

> /yang-seed vs /yang-trends 的区别：
> - seed 是种子动作（四通道，含 brainstorm），适合"我从零开始没选题"
> - trends 是日常多源抓取（零配置聚合器），适合"日常补充候选池"
```

完成引导 → 退出，不继续后续 phase。

### Phase 1: 解析 candidates

> 🔍 **CHECKPOINT 0**：candidates.md 已解析，所有 entry 的 id/title/tier/composite 提取完成

按 [candidate-schema.md](../../shared-protocols/candidate-schema.md) 的"Markdown 表示"格式解析每个 H3 entry：

```markdown
### [tier1] 标题
- **id**: a3f2c1d4e5b6
- **composite (v2)**: 8.47 — ER=4 HP=4 QL=5 NA=3 AB=5 SR=3 SAT=3
- **predicted bucket**: 5-30w
...
```

提取每条的 `id` / `title` / `tier` / `composite` / `dimension_scores` / `note`。

容错：`candidates.md` 格式被用户手改过 → 询问用户 schema，**不要静默忽略不识别的 entry**。

### Phase 2: 过滤

> 🔍 **CHECKPOINT 1**：已发布/已拒绝/未打分条目已过滤，剩余候选池大小已确认

```
1. EXCLUDE_PUBLISHED=true → 扫 predictions/*.md 的 header，提取所有 id；从候选池过滤掉
2. EXCLUDE_REJECTED=true → 过滤 tier=skip
3. REQUIRE_SCORED=true → 过滤 composite=null（未打分的不推荐）
4. filter 参数：
   - tier1: 只保留 tier=tier1
   - all: 不过滤（tier1+2+3）
   - safe: 排除 tier=risky
   - risky: 仅显示 tier=risky（用于"我今天就想发风险议题"）
```

### Phase 2.5: Buffer 颜色覆盖（**最高优先级**）

读 `state.shoots` + `state.target_publish_cadence_days` 算 buffer 颜色（[cadence-protocol.md](../../shared-protocols/cadence-protocol.md)）：

| Buffer 颜色 | 推荐策略覆盖 |
|---|---|
| 🔴 红 | **只推 top 1 稳分**——不推实验性。回："buffer 已 0/1 篇，下个发布日断更风险高，今天必须拍 ≥1 条稳分。下面是 top 1 稳分（不推实验性）" |
| 🟠 橙 | 标准 1 稳 + 1 实验，但提示"建议优先拍稳分" |
| 🟢 绿 | 标准 1+1（默认） |
| 🔵 蓝 | **拒绝推荐**。回："你 buffer 已 N 条，cadence-protocol 规定积压时暂停拍摄。先发存货 + 复盘。手动覆盖请说 '我就要拍'" |
| 灵活模式 (`target_publish_cadence_days=null`) | 不应用 buffer 覆盖，标准策略 |

### Phase 3: 排序 + 选 1 稳 + 1 实验（按 STRATEGY）

> 🔍 **CHECKPOINT 2**：稳分/实验性候选已选定，锚点对比已完成

#### 第 1 条（稳分）

1. 按 `composite` 降序排
2. 过滤掉 `tier=risky`（稳分要安全议题）
3. 过滤掉 `category` 与最近 `DUPLICATE_CATEGORY_LOOKBACK` 天已发/已推过的重复（避免审美疲劳）
4. 取 top 1

#### 第 2 条（实验性）

1. 在 candidates.md 中找：
   - 维度组合与最近已发样本**差异最大**（增加校准信息量），或
   - 含明确的 pattern/dimension hypothesis（如 "MS=5 的 A/B 对照"），或
   - tier=risky 但用户主动愿意试（用 `--filter risky` 覆盖）
2. composite 不一定 top——但有"信息价值"
3. 如 candidates 池里没有合适的实验性候选 → 回："候选池里没有明显的实验性样本，给你 2 条稳分"

#### 剩余 (TOP_N - 2) 条

按 composite 降序补满，标 "（备选）"。

#### 锚点

对每条找 1-2 个 composite 接近的**已发布**作品作为锚点（从 `predictions/*.md` 读）。优先**同时长**锚点（按 `state.typical_duration_seconds` ±20%）。

### Phase 4: 输出

> 🔍 **CHECKPOINT 3**：推荐列表已生成，每条含维度评分 + 锚点 + rationale

```
🎯 候选池推荐（rubric: v2 / buffer: 🟢 绿 / cadence: 隔日更）

📌 第 1 条 — **稳分**（推荐立即拍）：
  **[tier1] [👍 9.18] "为你好"高密体系**
   - 维度：ER=5 HP=5 QL=4 NA=4 AB=5 SR=5 SAT=4
   - 粗预测桶：30-100w（中枢 ~60w）
   - rationale：ER+SR 双 5 顶配，"高密度家庭议题"普适且分享安全
   - 锚点：仓鼠 (composite 9.41, 实绩 124w) — 同走"理论框架+具象样本"路线
   - 风险：议题厚重，不适合连续 2 篇都打这种

🧪 第 2 条 — **实验性**（验证特定假设）：
  **[tier1] [👍 8.71] 哈哈长度**
   - 维度：ER=3 HP=5 QL=5 NA=4 AB=5 SR=4 SAT=5
   - 粗预测桶：30-100w（中枢 ~55w）
   - **测试目标**：候选维度组合 vs 最近样本差异最大，拍它能补足校准信息
   - 信息价值：拍这条对 rubric 升级有强证据贡献
   - 锚点：谁问你了 (composite 8.24, 实绩 11.7w)

（备选 top 3）：
  3. ……
  4. ……
  5. ……

下一步：
- 选稳分 + 实验性各拍 1 条 → 改写 script → "启动预测"
- 只拍 1 条 → 选稳分（buffer 颜色越红，越应该选稳分）
- 想抓更多候选 → 说"抓热点"
- 都不满意 → 说"过滤改 all"看其他 tier 或 "regen"
```

如 buffer 颜色为 🔴：
```
🔴 buffer 警戒：你 buffer 已 0/1 篇，**下个发布日可能断更**。
   按节奏协议，只推 top 1 稳分（不推实验性）：

  **[tier1] [👍 9.18] "为你好"高密体系**
   - ...（同上稳分格式）

今天必须拍这条。挑候选 → "抓热点"。
```

如 buffer 颜色为 🔵：
```
🔵 buffer 积压：你 buffer 已 N 条，**暂停推荐**。
   按节奏协议，先发存货 + 复盘。
   - 已拍未发：N 条（最早一条 X 天前拍的）
   - 待复盘：N 条
   说 "已发布 ..." 出队，或 "复盘" 处理待复盘项。
   如果你坚持要拍新的，回 "我就要拍"，我会推 top 1 稳分。
```

每条必有：维度评分（让用户能挑战打分）+ 锚点（让用户校准 composite 的可信度）+ rationale（让用户理解推荐逻辑）。**不允许只输出 composite 排序而无解释**——那是黑箱。

## Key Rules

1. **不报错，给引导**。candidates 缺失是默认状态，不是错误
2. **不推未打分的**。REQUIRE_SCORED=true 是诚实门槛——推未读过的素材是占星
3. **必带锚点**。composite 8.47 在不同账号意味不同，锚点把抽象数字 ground 到真实样本
4. **必带 rationale**。一句话——为什么这条比第二条强？
5. **去重 published**。已发过的不推（用户可显式覆盖）

## Refusals

- 「直接给我 composite 最高的，不用解释理由」 → 拒绝。展示评分 + 锚点是发现"打错"的唯一机会
- 「把 candidates.md 里所有 entry 都重新打分一遍」 → 路由到 `/yang-score` 单条做；批量重打分是 `/yang-bump` 的一部分，不在 recommend 范围
- 「按预测桶排，不要按 composite」 → 询问理由。bucket 是 composite 的离散化，按 composite 排即按 bucket 排，差异在桶内序

## Integration

- 上游：`/yang-trends` 把外部热点拉进 candidates.md → recommend 自动看到；`/yang-seed` 四通道产出候选
- 下游：用户挑一条后写稿 → `/yang-predict`（candidate 的粗 composite 不进入 prediction，prediction 重新打）
- 与 `/yang-status` 协调：status 显示 "candidates 池有 N 条 tier1 未发"，recommend 提供具体推荐

📚 知识依据：composite 维度锚定 `[来源：A-数据]` `[来源：B-脚本]`；选题安全性/分享性参考 `[来源：A-流量]`。

## 失败模式编码

| 编码 | 名称 | 描述 |
|------|------|------|
| `YR-E01` | 候选池缺失 | candidates.md 不存在或为空，无法推荐 |
| `YR-E02` | 全部未打分 | 候选池有条目但全部 composite=null，REQUIRE_SCORED 过滤后为空 |
| `YR-E03` | 格式异常 | candidates.md 被手改导致解析失败，无法提取 id/tier/composite |
| `YR-E04` | 锚点缺失 | predictions/ 目录为空，无法为推荐条目找到已发布锚点 |
| `YR-E05` | 稳分池耗尽 | 过滤后无 tier≠risky 的候选，无法选出稳分推荐 |
| `YR-E06` | Buffer 策略冲突 | buffer 🔵 积压但仍被要求推荐，需用户手动覆盖 |

## 反例黑名单

1. **禁止推荐未打分的候选**——REQUIRE_SCORED=true 是诚实门槛，推未读过的素材是占星
2. **禁止只输出 composite 排序而无解释**——维度评分 + 锚点 + rationale 是发现"打错"的唯一机会
3. **禁止在候选池缺失时报错退出**——给引导而非报错，第一次使用 yang-recommend 不应被劝退
4. **禁止在 buffer 🔴 时推荐实验性候选**——断更风险下只推稳分，实验性推给用户是误导
5. **禁止静默忽略格式异常的候选**——必须询问用户确认 schema，不得跳过不报
6. **禁止推荐已发布的候选**——EXCLUDE_PUBLISHED=true 是硬规则，避免重复劳动
7. **禁止在无锚点时省略锚点对比**——无锚点须明确标注"⚠ 无已发布锚点，composite 可信度无法校验"
8. **禁止按预测桶排序替代 composite 排序**——bucket 是 composite 的离散化，按 composite 排即按 bucket 排，差异在桶内序

## 特有量化标准：推荐多样性指数

每次推荐输出须计算**推荐多样性指数**（Recommendation Diversity Index, RDI），衡量推荐列表在维度空间上的覆盖广度：

| 指标 | 公式 | 门槛 |
|------|------|------|
| 维度覆盖度 | 推荐列表中 7 维度各自最高分维度覆盖数 / 7 | ≥ 4/7 |
| 类目去重率 | 推荐列表中不同类目数 / 推荐总数 | ≥ 0.4 |
| 稳实验比 | 稳分:实验性 = 1:1（推 ≥2 条时） | 1:1 |

RDI 不达标时，须在输出末尾标注 `⚠ 推荐多样性不足（维度覆盖 X/7 / 类目去重率 Y%），候选池可能过于集中，建议补充不同方向候选`。

RDI 写入 `.yang-state.json` 的 `last_recommend_rdi` 字段，yang-status 看板可引用此值展示候选池健康度。

---

## 推荐多样性保障

> 确保推荐列表不全是同一类型选题，避免审美疲劳和校准信息损失。本段定义多样性的硬性规则和保障机制。

### 多样性硬性规则

| 规则 | 约束 | 违反处理 |
|------|------|---------|
| 类目去重 | 同一推荐列表中，相同类目（category）的选题不超过 2 条 | 超出部分降级为备选，从其他类目补充 |
| 维度覆盖 | 推荐列表中至少覆盖 4/7 维度的最高分项 | 不达标时标注 `⚠ 推荐多样性不足` |
| 稳实验比 | 推荐≥2条时，稳分:实验性 = 1:1 | 强制执行，不可全推稳分或全推实验性 |
| 风险分散 | 同一推荐列表中，tier=risky 不超过 1 条 | 超出部分替换为 tier1/tier2 |
| 时长分散 | 推荐列表中至少含 1 条不同时长档位（如短+中 或 中+长） | 全部同时长时标注"时长单一" |
| 情绪分散 | 推荐列表中不全是同一情绪基调（如全严肃/全搞笑） | 全部同基调时标注"情绪单一" |

### 多样性检查流程

在 Phase 3 排序完成后、Phase 4 输出前，执行多样性检查：

1. **类目扫描**：统计推荐列表中各类目出现次数 → 同类目 > 2 → 替换为次优不同类目候选
2. **维度覆盖**：检查推荐列表中 7 维度的最高分维度覆盖数 → < 4 → 从候选池补充不同维度组合的选题
3. **情绪基调**：检查推荐列表的情绪标签 → 全部相同 → 替换 1 条为不同基调的候选
4. **时长档位**：检查推荐列表的时长分布 → 全部同时长 → 替换 1 条为不同时长档位

### 多样性不足时的降级策略

当候选池本身缺乏多样性时（如全部是同一类目）：
- 不强制替换（无候选可替换）
- 在输出末尾标注 `⚠ 候选池多样性不足：{具体原因}，建议通过 /yang-seed 或 /yang-trends 补充不同方向候选`
- 记录到 `.yang-state.json` 的 `diversity_warnings` 数组，yang-status 看板可展示

---

## 推荐与Buffer状态联动

> 推荐策略必须与 buffer 状态深度联动，确保推荐结果符合当前创作节奏需求。本段定义 buffer 状态如何影响推荐的优先级和策略。

### Buffer 状态对推荐的完整影响矩阵

| Buffer 颜色 | 稳分优先级 | 实验性推荐 | 推荐数量 | 附加建议 |
|------------|-----------|-----------|---------|---------|
| 🔴 红（0-1篇） | 最高 | 不推 | top 1 稳分 | "今天必须拍，断更风险极高" |
| 🟠 橙（2-3篇） | 高 | 可推 1 条 | top 3（1稳+1实验+1备选） | "优先拍稳分，实验性可延后" |
| 🟢 绿（4-5篇） | 标准 | 标准 1:1 | top 5（1稳+1实验+3备选） | "节奏健康，可自由选择" |
| 🔵 蓝（≥6篇） | 拒绝推荐 | 拒绝推荐 | 0 | "先发存货+复盘，暂停拍摄" |
| 灵活模式 | 标准 | 标准 | top 5 | 不应用 buffer 覆盖 |

### Buffer 不足时的推荐优先级调整

当 buffer 颜色为 🔴 或 🟠 时，推荐优先级按以下规则调整：

1. **composite 稳定性加权**：稳分候选的 composite 波动性（历史预测偏差标准差）越小，优先级越高
2. **拍摄难度优先**：buffer 不足时优先推荐拍摄难度低、制作周期短的选题（如口播 > 实拍 > 复杂剪辑）
3. **发布时效性**：优先推荐时效敏感的选题（热点类），避免因拖延错过窗口
4. **历史表现锚定**：优先推荐与历史高表现作品维度组合相似的选题

### Buffer 过剩时的替代推荐

当 buffer 🔵 积压时，虽然不推荐拍摄，但可提供替代建议：

- "建议先发布：{最早拍摄的未发布视频}（已拍 {N} 天）"
- "建议先复盘：{待复盘项列表}"
- "如需优化已拍内容：可运行 /yang-polish 对已拍视频润色"

---

## 推荐解释性

> 每个推荐选题必须附带推荐理由，让用户理解推荐逻辑、挑战打分、发现盲区。本段定义推荐理由的格式规范。

### 推荐理由格式规范

每条推荐必须包含以下 3 层解释：

#### 第 1 层：一句话理由（必填）

格式：`rationale：{核心优势维度}+{次优势维度} 双高，{一句话定性}`

示例：
- `rationale：ER+SR 双 5 顶配，"高密度家庭议题"普适且分享安全`
- `rationale：HP+QL 双高，"强钩子+深度内容"组合，适合建立专业形象`

#### 第 2 层：维度评分解读（必填）

格式：列出各维度评分 + 与候选池均值的偏差

示例：
```
维度：ER=5(↑1.2) HP=5(↑0.8) QL=4(↑0.3) NA=4(↑0.5) AB=5(↑1.0) SR=5(↑1.5) SAT=4(↑0.2)
  ↑ 相对候选池均值：ER/SR/AB 显著高于均值，是核心优势维度
```

#### 第 3 层：锚点对比 + 风险提示（必填）

格式：
```
锚点：{已发布作品名} (composite {N}, 实绩 {播放量}) — {相似点}
风险：{潜在风险描述}
```

示例：
```
锚点：仓鼠 (composite 9.41, 实绩 124w) — 同走"理论框架+具象样本"路线
风险：议题厚重，不适合连续 2 篇都打这种
```

### 稳分 vs 实验性的解释差异

| 推荐类型 | 第 1 层侧重 | 第 2 层侧重 | 第 3 层侧重 |
|---------|-----------|-----------|-----------|
| 稳分 | composite 高 + 维度均衡 | 优势维度突出 + 历史验证 | 锚点实绩强 + 风险可控 |
| 实验性 | 信息价值 + 校准贡献 | 维度组合差异 + 假设验证 | 锚点差异大 + 风险明确 |

### 推荐理由质量检查

输出前须检查每条推荐理由是否满足：
- ✅ 一句话理由含具体维度名称，非泛化描述（如"这个不错"）
- ✅ 维度评分解读含与均值的偏差，非仅列数字
- ✅ 锚点为已发布作品（非候选），含实绩数据
- ✅ 风险提示非空，且与选题内容相关（非模板化）

不满足时须重写推荐理由，不得输出无解释的推荐。
