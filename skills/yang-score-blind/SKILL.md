---
name: yang-score-blind
version: "2.0"
description: |
  INTERNAL sub-agent for blind 7-dim rubric scoring. **NOT a user-facing skill — do NOT invoke from main conversation.** Called via Task tool by yang-score / yang-predict / yang-bump to get a context-isolated score on a script. Receives ONLY script_path + rubric_notes_path; refuses any other input. Outputs strict JSON: 7 dimensions × {score 0-10, confidence enum, one-line reason}. **Hard refuses to Read** .yang-state.json, predictions/*, retro 段, or anything that could leak post-publish data. This is channel B in the 3-channel calibration model (A=main, B=blind sub, C=cross-model).
trigger-words: [score-blind, 盲打分, channel-b, 盲评分, 隔离打分, blind-score]
author: 阿洋
allowed-tools: Read, Glob, Grep
argument-hint: "<script-path> <rubric-notes-path>"
tags: [盲打分, 隔离评分, Channel-B, rubric评分, 反污染]
---

# /yang-score-blind — Channel B (blind scorer sub-agent)

> 🔒 **这是子 agent，不是用户 skill**。只能由 `yang-score` / `yang-predict` / `yang-bump` 通过 Task tool spawn。用户直接 trigger 没有意义——主对话已经被污染，调用 blind sub-agent 在主 context 里跑不构成隔离。

---

## Why this exists（绝不可省的背景）

Yang.skills 的 7/9 维打分原本 inline 在主对话——但主 Claude 已经看过：
- 用户对话历史（含偶然提到的播放数 / 评论 / 情绪）
- 已发布作品的实绩数据
- 历史 `predictions/*.md` 含复盘段（**严重污染**）
- 用户的赞美 / 抱怨 / 期待

inline 打分 = **被污染的"盲"预测**。问题在 `yang-bump` Phase 2 校准池重打时最严重：Claude 知道每条实绩才回追 TN/CC 分，rank 一致性可能 overfit 不是真信号。

**channel B 的角色**：用 Task tool 把打分动作丢进一个**全新 context**——这个 sub-agent 没看过主对话、没读过 state、没碰过 predictions/。它只看 script 全文 + rubric_notes.md，按 rubric 打分。

输出回传主对话后，主 Claude 自己对比、做最终决策。隔离的是**打分这个动作的输入**，不是决策权。

## 三 channel 模型

| Channel | 输入 | 用途 | 风险 |
|---|---|---|---|
| **A** = 主对话 | 全部上下文 | 跟用户交互、写 retro、决策 | 被实绩 / 用户态度污染 |
| **B** = blind sub-agent (this) | **只** script + rubric_notes.md | 给一份未受污染的打分作为 anchor | 仍是 Claude，RLHF prior 共享 |
| **C** = 跨模型 audit (`mcp__llm-chat__chat` to qwen-max) | 校准池数据 + 新公式 | bump 终局 sanity check | RPM 限制、模型差异、单点 |

A 决策时把 B 当对照看 disagreement，**不当真理**。C 只在 bump 终局调一次。

---

## Inputs（**唯一被允许的输入**）

| 必填 | 来源 | 说明 |
|---|---|---|
| `<script-path>` | 主 Claude 通过 Task prompt 显式传入 | `scripts/<id>.md` 全文 |
| `<rubric-notes-path>` | 同上 | 用户项目根 `rubric_notes.md` 当前 rubric 公式 + 维度定义 |

**仅此两个文件可读**。其他一切**硬拒绝**——见下方 "Hard refusals" 段。

## 禁止读取（hard list）

下面这些路径 / 模式 sub-agent **绝不能 Read** —— 即使主 Claude 在 Task prompt 里手滑塞进来，也要拒绝并在 JSON 输出标对应 `refusal` 码：

| 路径模式 | 为什么禁 | refusal_code |
|---|---|---|
| `.yang-state.json` | 含 calibration_samples / pending_retros / last_published_at / shoots — 全是后视数据 | `blocked_contaminated_input` |
| `predictions/*.md` | 含 `## 预测` 段 + `## 复盘` 段，复盘段就是实绩 | `blocked_contaminated_input` |
| `videos/*/report.md` | T+3d 抓回的真实数据 | `blocked_contaminated_input` |
| `videos/*/script.md` | 后改拍摄稿，复盘时被对照 | `blocked_contaminated_input` |
| `STATUS.md` | yang-status 渲染的看板，含过去数据 | `blocked_contaminated_input` |
| `.yang-cache/usage.jsonl` | 行为 log | `blocked_contaminated_input` |
| **`rubric-memo.md`** | **yang-bump 升级 Memo 累积档案——含真实视频名 + 实绩 + 派生证据。这是 channel B 的最大泄漏入口（PR #11 实测复现）** | **`blocked_rubric_memo`** |
| 任何含"播放 / 阅读 / 点赞 / 评论数 / 转发 / w / 万 / k / M"的文件 | 直接污染 | `blocked_contaminated_input` |

**白名单只有两个**：
- `scripts/<id>.md`（pre-shoot 草稿，传入参数）
- `rubric_notes.md`（评分公式 + 维度定义，**应**只含通用语言；如发现实绩数字 → 标 `non_blind_warning` 并降 confidence）

如果主 Claude Task prompt 漏传了某条路径，sub-agent 主动询问"我只允许读 script + rubric_notes，缺哪个？"——**绝不**自己去 Glob 探测项目结构补全。

> ⚪ **白名单兜底自检**：读完 `rubric_notes.md` 后必跑 `grep -E '\\d+\\s*[wWmMkK万]|播放|实绩|实际'`——命中 → 标 `self_check.any_contamination_signal: true` + `refusal: "non_blind_warning"`，所有维度 confidence 降 medium 并把违禁 snippet 摘抄进 contamination_note 字段。**仍输出 dimensions** 让主 Claude 知道发生了什么——拒绝输出比误判更糟，但要诚实标注。
>
> ⚪ **量程数字自检**：读完 `rubric_notes.md` 后也必须验证各维度的 score range 为 0-10。若发现异常量程（如 0-5、0-100），标 `self_check.scale_tampered: true` + 拒绝打分并输出 `refusal: "scale_range_violated"`。量程检测的 regex 参考：逐维度定位 `score range` 或 `量程` 标签，提取边界数字并校验 `min === 0 && max === 10`。

---

## 前置条件检查

> [前置条件] 本 skill 为辅助 skill，无严格流水线前置依赖。本 sub-agent 不读取 `.yang-state.json`，不检测 `in_progress_session`——隔离上下文中不应有任何状态感知。

---

## Workflow

### Phase 0：边界自检

> 🔍 **检查点 CP-1**：`<script-path>` 和 `<rubric-notes-path>` 均在白名单内，路径合法

1. 解析 Task prompt 拿 `<script-path>` 和 `<rubric-notes-path>`
2. 校验路径符合白名单——不在 `scripts/` 下的 .md → 拒绝（除非主 Claude 显式说明"这是临时草稿临时路径，标 `non_standard_path: true`"）
3. Read `<rubric-notes-path>` → 解析当前 rubric_version + 维度数量（7 或 9）+ 公式
4. Read `<script-path>` → 拿到 script 全文 + 字数

🚫 **不要做的事**：
- 不要为了"看看用户做啥账号"去 Read `benchmark.md` —— benchmark 是 Channel A 的 context，不属于本 sub-agent
- 不要为了"看看历史风格"去 Glob `predictions/` —— 那是污染源
- 不要去 Read `.yang-state.json` 看 calibration 进度 —— 你**完全不需要知道**主 Claude 跑了多少篇

### Phase 1：按 rubric 打 N 维分

> 🔍 **检查点 CP-2**：rubric_notes.md 已解析，维度数量和公式已确认；script 全文已读取

按 `rubric_notes.md` 当前 rubric 公式：

- v0：7 维等权（ER / SR / HP / QL / NA / AB / SAT）—— 默认起步
- v1：用户校准过的（权重不同）
- 所有版本均从 rubric_notes.md 动态读取维度列表

对每个维度：
1. 给一个 **0-10 整数分**
2. 给一个 **per-dim confidence** enum：`high | medium | low`
   - high：稿子里有直接证据（一句话指向该维度）
   - medium：可推断但需要解释
   - low：稿子信号太弱，纯估
3. 给一行 **理由** ≤ 30 字，**必须引用稿子里具体词或场景**

不算 composite——composite 是公式行为，主 Claude 用回传的维度分自己算。

### Phase 2：返回严格 JSON

> 🔍 **检查点 CP-3**：所有维度均已打分，confidence 和 reason 已填写；self_check 已执行
>
> 🔍 **检查点 CP-4**：JSON 格式合法（可被 `json.loads()` 解析），无尾部逗号/注释/Markdown 围栏

输出**只能**是一个有效 JSON。所有 markdown 解释都封禁——主 Claude 要的是结构化数据回主 context 解析。

```json
{
  "subagent_version": "v1",
  "rubric_version": "v2",
  "a_degraded": false,
  "script_path": "scripts/2026-05-04_abc123_短title.md",
  "script_hash": "<sha256:12 of script content>",
  "scored_at": "<ISO 8601 +08:00>",
  "dimensions": {
    "ER": { "score": 4, "confidence": "high",   "reason": "PPT加油猫猫开头—具象画面，情绪反差强" },
    "SR": { "score": 3, "confidence": "medium", "reason": "AI焦虑是议题但非热点对峙" },
    "HP": { "score": 5, "confidence": "high",   "reason": "首句\"第七页大屏中央 加油猫猫\"具象反差" },
    "QL": { "score": 5, "confidence": "high",   "reason": "\"加油猫猫救了我一命\"双关金句" },
    "NA": { "score": 4, "confidence": "medium", "reason": "单线反思+收束，清晰但不复杂" },
    "AB": { "score": 4, "confidence": "medium", "reason": "一人公司题但AI焦虑普适" },
    "SAT": { "score": 2, "confidence": "high",  "reason": "共情调，几乎无讽刺" }
  },
  "input_status": {
    "rubric_notes_read": true,
    "script_read": true,
    "any_other_file_read": false
  },
  "self_check": {
    "saw_play_numbers": false,
    "saw_comments": false,
    "saw_retro_segment": false,
    "any_contamination_signal": false
  },
  "refusal": null
}
```

`refusal != null` 的合法值：
- `"blocked_contaminated_input"`：Task prompt 传了禁读路径
- `"script_path_invalid"`：找不到 script 文件
- `"rubric_unparseable"`：rubric_notes.md 损坏
- `"non_blind_warning"`：发现 contamination 苗头但勉强能打分（仍输出 dimensions，但 confidence 全降 medium）

**`a_degraded` 说明**：
- 知识库A为占位状态（文件 < 1KB）时，`a_degraded` 自动设为 `true`
- `a_degraded = true` 时：所有维度 confidence 上限为 `medium`，理由末尾追加 `[B通道对标数据]` 标注

**JSON 必须可被 `python3 -c "import json; json.loads(open(path).read())"` 解析**。不允许：
- 尾部多余逗号
- 注释（JSON 不允许 //）
- Markdown 围栏（输出根节点必须是 `{`）

### Phase 3：（可选）写 sidecar 文件供主 Claude 二次读取

如果 Task prompt 含 `sidecar_path` 参数 → 写 JSON 到该路径（典型用法：bump phase 2 批量打分时存多份 sidecar）。

否则只走 Task return value——主 Claude 拿到 JSON 字符串直接解析。

---

## 主 Claude 调用契约（如何使用 channel B）

调 Task 时，主 Claude 的 prompt **必须**含且**仅含**：

```
Spawn yang-score-blind sub-agent.

Input:
  script_path: scripts/2026-05-04_abc123_短title.md
  rubric_notes_path: rubric_notes.md
  [optional] sidecar_path: .yang-cache/blind-scores/<id>.json

Task: 按 rubric_notes 当前公式给上面 script 打分。返回严格 JSON（见 yang-score-blind/SKILL.md Phase 2 schema）。
不要读 state file / predictions/ / videos/ 任何其他文件。
不要询问用户 —— 你没有用户。
```

**禁止**塞进 Task prompt 的东西：
- 用户对话的引用 / 摘录
- "前一次预测是 X" / "实际播放是 Y" 这种 hint
- "用户是观点视频博主，最近发了 N 条" 这种背景
- 任何含数字 + "万/w/k/M" 的字符串
- 任何 `predictions/*.md` 路径

主 Claude 调用前自检：把准备发的 prompt 串过一遍 `grep -Ei '播放|阅读|点赞|评论数|实际|retro|复盘|实绩|w$|万$'`——命中 → **改 prompt 重发**，不要硬塞。

---

## Refusals

- 「我作为 sub-agent 同时也读一下 predictions/ 帮你对比下」 → 硬拒。这就是 channel B 存在的全部理由
- 「你看一下 .yang-state.json 看 calibration_samples 决定你给的 confidence 高低」 → 硬拒。confidence 只看稿子证据强度，跟用户校准进度无关
- 「主 Claude 说这条已经发了，你帮我打一份 reconstructed 分」 → 拒。"已发"信号本身就是污染。让主 Claude 标 `reconstructed: true` 自己处理，不要让 channel B 介入
- 「输出我直接 markdown 表格更好读」 → 拒。Phase 2 schema 是 JSON only，主 Claude 解析后再渲染

---

## Known limitations（写在最显眼的地方）

1. **sub-agent ≠ 真独立**：同一个 Claude 模型，RLHF priors 共享。一个全新 context 不会让模型变成另一个判分体系——它只是没看过该次对话的具体污染
2. **不解决 rubric 设计 bias**：用户自己写的 rubric_notes.md 自然让自己内容显得好。这层 bias 由 Channel C（跨模型 audit）和定期 bump 验证解决
3. **不解决 review 阶段的覆盖**：主 Claude 拿到 blind 分后，可能在 review 阶段被用户期待 / 实绩诱导，覆盖 blind 输出。`yang-predict` Phase 2.5 通过 disagreement detection + 用户裁定来减轻，但不消除
4. **同 prompt 两次调可能给不同分**：Claude 不是 deterministic。主 Claude 应该把每次 blind score 当一次采样，不当唯一真理——但要记录而不是丢弃差异

## Channel C 跨模型审计配置

### MCP 服务安装
1. 确保已安装 `mcp__llm-chat__chat` MCP 工具
2. 配置 API Key：设置环境变量或配置文件中的 API Key
3. 默认使用 qwen-max 作为独立审计模型

### API Key 配置
通过以下方式之一配置 API Key：
- 环境变量: `export DASHSCOPE_API_KEY=your-key`
- MCP 配置文件: 在 mcp.json 中设置 qwen-max 的 api_key

### 可用性检测
yang-bump --strict 模式执行前检测 Channel C 是否可用：
- 若 mcp__llm-chat__chat 工具可用 → 执行跨模型审计
- 若不可用 → 提示降级信息

### 降级策略
若 Channel C 不可用：
1. 允许降级为自审模式
2. 在 rubric-memo.md 中标注 `[自审] CROSS_MODEL_AUDIT=false`
3. 在 .yang-state.json 中标记 `last_bump_self_audited: true`
4. 降低 bump 置信度标签（"高" → "中"）

### 知识库A 状态检测

读取 `knowledge/ansir/SKILL.md`:
- 若文件大小 < 1KB → 判定为占位状态
  → 在知识来源标注中显示 "A-占位（内容降级）"
  → 降低知识库A 的权重依赖
- 若 ≥ 1KB → 正常加载

**降级行为（yang-score-blind）**：评分分析视角从A降级读取
- 当A降级时：结构精细化三要素（钩子/骨架/情绪刺点）的分层视角不可用
- 打分维度的语义理解 → 从A的三要素框架降级为纯rubric定义的维度解释
- 钩子相关维度 → 去掉A的结构判断逻辑，仅依赖rubric_notes.md的公式定义
- 情绪相关维度 → 去掉A的情绪刺点判断，仅依赖稿件的直接情绪信号
- 所有维度的confidence标注 → 统一降低一级（high→medium, medium→low）
- 知识依据标注自动调整：`A-结构` → `A-占位（纯rubric评分）`

---

## 知识库依赖

本 skill 在盲打分执行过程中引用以下知识库内容（仅作为 rubric 维度的语义理解框架，不直接读取知识库文件）：

- 知识库A：结构精细化三要素（钩子/骨架/情绪刺点）—— 作为 script 内容分析的分层视角 `[来源：A-结构]`
- 知识库B：八大爆款元素（成本/人群/奇葩/反差/最差/头牌/怀旧/荷尔蒙）—— 作为爆款潜力评估的参考维度 `[来源：B-爆款]`

本 sub-agent 不直接读取知识库文件，但打分维度定义来源于上述知识体系。

```
📚 知识依据：A-结构 | B-爆款
```

---

## Integration

> 🔍 **检查点 CP-5**：主 Claude 调用契约已满足——Task prompt 仅含 script_path + rubric_notes_path，无污染信息

- **`yang-score`** Phase 2：默认 delegate 到本 sub-agent（替代旧的 inline 打分）
- **`yang-predict`** Phase 2：默认 delegate；Phase 2.5 用 disagreement detection
- **`yang-bump`** Phase 2：**强制** delegate，bump 时**不接受 self-scored fallback**
- **`yang-retro`**：不调用——retro 本来就看实绩，blind 无意义

---

## 失败模式编码

| 编码 | 含义 | 触发条件 | 处置 |
|------|------|----------|------|
| `SB-E01` | 禁读路径传入 | Task prompt 含 `.yang-state.json`/`predictions/`等禁读路径 | 标 `refusal: "blocked_contaminated_input"`，拒绝打分 |
| `SB-E02` | script 路径无效 | `<script-path>` 文件不存在或不在白名单 | 标 `refusal: "script_path_invalid"`，拒绝打分 |
| `SB-E03` | rubric 不可解析 | `rubric_notes.md` 格式损坏或维度定义缺失 | 标 `refusal: "rubric_unparseable"`，拒绝打分 |
| `SB-E04` | 污染信号检测 | `rubric_notes.md` 含播放/实绩等数字 | 标 `refusal: "non_blind_warning"`，confidence 全降 medium |
| `SB-E05` | 量程篡改 | rubric 维度 score range 非 0-10 | 标 `refusal: "scale_range_violated"`，拒绝打分 |
| `SB-E06` | 知识库A降级 | `knowledge/ansir/SKILL.md` < 1KB | `a_degraded = true`，confidence 上限 medium |

---

## 反例黑名单

1. **禁止读取禁读路径**：`.yang-state.json`/`predictions/`/`videos/`/`STATUS.md`/`.yang-cache/`/`rubric-memo.md` 绝不可读，即使主 Claude 在 Task prompt 中传入
2. **禁止自行探测项目结构**：不得用 Glob 探测 `predictions/` 或其他目录补全信息
3. **禁止输出 Markdown 格式**：Phase 2 输出只能是纯 JSON，不得含 Markdown 围栏/注释/尾部逗号
4. **禁止跳过 self_check**：读完 `rubric_notes.md` 后必须执行污染信号自检和量程自检
5. **禁止用实绩调整 confidence**：confidence 仅看稿子证据强度，不得因"知道校准进度"而调整
6. **禁止接受 reconstructed 打分请求**：已知"已发"的视频不得由 Channel B 打分
7. **禁止白名单外读取**：只读 `scripts/<id>.md` 和 `rubric_notes.md`，其他一切硬拒绝
8. **禁止忽略 a_degraded**：知识库A占位时必须执行降级行为，不得假装正常

---

## 量化标准：盲打分隔离纯度

盲打分的有效性由**隔离纯度**衡量：

- **隔离纯度** = `self_check` 中所有污染信号检测项为 false 的比例
- **合格线**：隔离纯度 = 100%（`any_contamination_signal` 必须为 false）
- **降级线**：隔离纯度 < 100% 时，所有维度 confidence 降为 medium，标 `non_blind_warning`
- 理由引用率：reason 中引用稿件具体词/场景的维度占比 ≥ 80%（不足则说明打分流于泛泛）
- confidence 分布合理性：`high` 占比应在 30%-70% 之间（全 high 或全 low 均为异常信号）
- 隔离纯度 < 100% 时，必须标注污染来源并降级，不得隐瞒

---

## 盲打分隔离验证

Channel B 的隔离性是其存在的核心价值，必须定期验证隔离是否真正有效：

### 隔离验证方法

**方法一：输入审计（每次执行自动运行）**

| 检查项 | 检查方式 | 通过标准 | 失败处置 |
|--------|---------|---------|---------|
| 白名单合规 | 检查 Read 调用的文件路径是否在白名单内 | 仅读取 script + rubric_notes | 标 `blocked_contaminated_input` |
| 污染信号扫描 | grep rubric_notes.md 中的播放/实绩等关键词 | 无命中 | 标 `non_blind_warning` |
| 量程校验 | 检查各维度 score range 是否为 0-10 | min=0, max=10 | 标 `scale_range_violated` |
| self_check 完整性 | 验证 JSON 输出中 self_check 所有字段均为 false | 全部 false | 按对应规则降级 |

**方法二：对照实验（定期手动执行）**

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| 1 | 对同一脚本，分别在 Channel A（主对话）和 Channel B（blind sub-agent）打分 | 两份评分存在差异 |
| 2 | 对比两份评分的差异模式 | Channel B 不应出现"恰好"与实绩一致的评分 |
| 3 | 对一个已知高播放的脚本，Channel B 是否给出了异常高分 | 不应出现（否则说明隔离被破坏） |
| 4 | 对一个已知低播放的脚本，Channel B 是否给出了异常低分 | 不应出现 |

**方法三：信息泄露检测（bump 时执行）**

在 yang-bump Phase 2 批量盲打分后，分析盲打分结果与实绩的相关性：

| 检测项 | 计算方式 | 阈值 | 判定 |
|--------|---------|------|------|
| 盲打分-实绩相关系数 | 盲打分 composite 与 actual_plays 的 Spearman ρ | ρ < 0.3 | ✅ 隔离有效 |
| 盲打分-实绩相关系数 | 同上 | 0.3 ≤ ρ < 0.5 | ⚠️ 可能泄露 |
| 盲打分-实绩相关系数 | 同上 | ρ ≥ 0.5 | 🔴 隔离失效 |

### 隔离验证输出

每次 bump 后，在 rubric-memo.md 中记录隔离验证结果：

```markdown
### 隔离验证记录

日期: 2026-06-14
方法: 信息泄露检测
样本数: 12
盲打分-实绩 ρ: 0.22
判定: ✅ 隔离有效
备注: 盲打分与实绩无显著相关，Channel B 隔离性良好
```

---

## 盲打分与主评分的一致性分析

Channel A（主对话评分）和 Channel B（盲打分）的差异分析是校准系统的关键输入：

### 差异分析框架

**维度级差异分析**

对每个维度计算 A-B 差异：

| 指标 | 计算方式 | 解读 |
|------|---------|------|
| 绝对差异 | \|A_score - B_score\| | 差异幅度 |
| 方向一致性 | A > B / A = B / A < B | 差异方向 |
| 系统性偏差 | 多次评分中 A-B 的均值 | 是否存在系统性的 A 偏高或 B 偏高 |

**差异模式分类**

| 差异模式 | 特征 | 可能原因 | 处置 |
|---------|------|---------|------|
| 一致型 | \|A-B\| ≤ 1 且方向随机 | 两通道独立得出相似结论 | ✅ 评分可信度高 |
| A 偏高型 | A-B 均值 > 1.5 | 主对话被实绩/用户期待污染 | 以 B 为锚，下调 A 的权重 |
| B 偏高型 | B-A 均值 > 1.5 | rubric 定义偏向该脚本特征 | 检查 rubric 是否需要校准 |
| 随机型 | \|A-B\| > 2 但方向随机 | 评分维度定义模糊 | 细化 rubric 维度定义 |
| 特定维度偏离 | 仅某维度 \|A-B\| > 2 | 该维度定义歧义或 A 有特殊信息 | 针对该维度细化 rubric |

### 一致性分析输出

在 yang-predict Phase 2.5 的 disagreement detection 中，输出一致性分析：

```
📊 Channel A vs B 一致性分析

整体一致性: 71%（5/7 维度差异 ≤ 1）

维度差异:
  ER: A=6, B=5, Δ=+1  ✅ 一致
  SR: A=7, B=4, Δ=+3  ⚠️ A 偏高（主对话可能受用户期待影响）
  HP: A=8, B=7, Δ=+1  ✅ 一致
  QL: A=5, B=5, Δ=0   ✅ 完全一致
  NA: A=6, B=3, Δ=+3  ⚠️ A 偏高
  AB: A=7, B=6, Δ=+1  ✅ 一致
  SAT: A=4, B=4, Δ=0   ✅ 完全一致

差异模式: A 偏高型（SR/NA 维度 A 系统性偏高）
建议: SR 和 NA 维度以 B 为锚校准，A 的评分可能受上下文污染

历史一致性趋势（最近 5 次）: 57% → 63% → 68% → 71% → 71%
  趋势: 稳步提升，rubric 定义逐渐清晰
```

### 一致性趋势追踪

在 `.yang-state.json` 中记录每次 A/B 一致性数据：

```json
{
  "ab_consistency_history": [
    {
      "date": "2026-06-14",
      "overall_consistency": 0.71,
      "a_bias_dimensions": ["SR", "NA"],
      "b_bias_dimensions": [],
      "max_delta": 3,
      "mean_delta": 1.29
    }
  ]
}
```

一致性趋势判定：
- 持续上升（> 3 次）→ rubric 定义越来越清晰，评分系统趋于稳定
- 持续下降（> 3 次）→ 可能 rubric 近期变更引入歧义，需检查
- 震荡 → 正常波动，无需特别处理

---

## 隔离失效恢复

当发现 Channel B 的隔离被破坏时，必须立即执行恢复流程：

### 隔离失效判定条件

满足以下任一条件即判定为隔离失效：

| 条件 | 检测方式 | 严重程度 |
|------|---------|---------|
| 盲打分-实绩 ρ ≥ 0.5 | bump 时信息泄露检测 | 🔴 严重 |
| self_check.any_contamination_signal = true | 每次执行自动检测 | 🟡 警告 |
| Channel A/B 在已知实绩的脚本上评分高度一致（差异 < 0.5） | 对照实验 | 🟡 警告 |
| rubric_notes.md 中发现实绩数字 | 污染信号扫描 | 🔴 严重 |

### 恢复步骤

**Step 1: 紧急止血**

```
🚨 隔离失效检测

失效类型: {类型}
检测时间: {timestamp}
影响范围: {受影响的评分记录数}

紧急措施:
  1. 标记所有受影响的盲打分记录为 "isolation_compromised: true"
  2. 在 rubric-memo.md 中记录失效事件
  3. 暂停使用受影响的盲打分数据做 bump 决策
```

**Step 2: 根因分析**

| 可能根因 | 排查方式 | 修复方法 |
|---------|---------|---------|
| rubric_notes.md 被污染（含实绩数字） | grep 扫描 rubric_notes.md | 清除实绩数字，恢复纯定义文本 |
| 主 Claude Task prompt 泄露信息 | 检查 Task prompt 内容 | 修改调用契约，增加自检步骤 |
| rubric 维度定义隐含实绩关联 | 人工审查 rubric 维度描述 | 重写维度定义，使用纯内容描述 |
| sub-agent 自行探测了禁读路径 | 检查 sub-agent 的 Read 调用日志 | 强化白名单校验，增加路径拦截 |

**Step 3: 数据修复**

| 受影响数据 | 修复方式 |
|-----------|---------|
| 单次盲打分记录 | 标记 `isolation_compromised: true`，降级为参考信号（不参与 bump 决策） |
| bump 决策基于受污染数据 | 检查 bump 结果是否受影响；若受影响，回退 bump 并重新执行 |
| 一致性分析数据 | 剔除受污染记录，重新计算一致性指标 |

**Step 4: 预防加固**

| 加固措施 | 说明 |
|---------|------|
| 增强 Task prompt 自检 | 主 Claude 调用前必须过 `grep -Ei` 检查，命中则改 prompt 重发 |
| rubric_notes.md 写入保护 | bump 更新 rubric_notes.md 时，自动扫描并清除实绩数字 |
| 盲打分结果审计 | 每次盲打分后，主 Claude 检查 B 的评分是否与已知实绩异常相关 |
| 定期隔离验证 | 每 5 次盲打分执行一次对照实验，验证隔离有效性 |

### 恢复验证

隔离失效修复后，必须执行验证：

```
🔍 隔离恢复验证

1. 重新执行盲打分（使用修复后的 rubric_notes.md）
2. 检查 self_check.all = false ✅
3. 执行对照实验：A/B 差异是否恢复正常范围
4. 信息泄露检测：盲打分-实绩 ρ < 0.3 ✅

验证结果: ✅ 隔离已恢复 / ❌ 隔离仍失效，需进一步排查
```

### 隔离失效记录

所有失效事件记录到 `.yang-state.json` 的 `isolation_incidents` 数组：

```json
{
  "isolation_incidents": [
    {
      "incident_id": "INC-2026-06-14-001",
      "detected_at": "2026-06-14T10:00:00+08:00",
      "type": "rubric_contamination",
      "severity": "critical",
      "affected_scores": 3,
      "root_cause": "rubric_notes.md 中混入实绩数字（bump 时误写入）",
      "fix_applied": "清除 rubric_notes.md 中的实绩数字，重新执行盲打分",
      "verified_at": "2026-06-14T11:00:00+08:00",
      "verification_result": "passed"
    }
  ]
}
```
