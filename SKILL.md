---
name: Yang.skills
version: 6.0.0
description: 全能内容创作运营超级Skills包。融合知识库A、知识库B、知识库C三大运营知识体系，提供搜索意图研究→选题→打分→活人感量化评分润色→盲预测→发布→复盘→进化rubric的全闭环内容创作工作流。方法论文本形态通用：视频/文章/播客/Newsletter/短文。首次使用必须先跑 /yang-init。兼容 Claude Code、Codex CLI、OpenCode、OpenClaw 等 Agent runtime。不要用于从零创建一个新Skill、不要用于普通的代码review、不要用于与内容创作运营无关的任务。
argument-hint: "[draft-path] [--mode: cold-start|calibration]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
compatibility:
  claude-code: full
  codex-cli: functional
  opencode: functional
  openclaw: functional
  cursor: partial
  github-copilot: partial
author: 阿洋
trigger-words:
  - 初始化 / init / 首次使用 / setup / 帮我开始 / 怎么用
  - 打分这篇 / score this / 评估这篇 / 评分 / 帮我看看这稿子 / 这稿子能打几分
  - 启动预测 / start prediction / 预测这条 / 盲预测 / 给这稿子打分并预测 / 预测一下效果
  - 已发布 / I shipped it / 发布登记 / publish log / 发布链接是 / 刚发了
  - 复盘 / retro this / T+3d 数据来了 / 回顾这条 / 看看数据 / 数据回来了
  - 升级rubric / bump rubric / 校准池够了 / 进化评分规则 / 更新公式 / 优化打分标准
  - 推荐选题 / next topic / 下一篇做什么 / recommend topics / 挑一个选题 / 不知道写什么
  - 抓热点 / fetch trends / 现在有什么热点 / 热点有哪些 / 今天有什么可做的 / 最近什么火
  - 状态 / status / 看板 / dashboard / 现在什么进度 / 我到哪一步了
  - 找对标 / 学这个账号 / 拆这几个对标视频 / learn from / 导入对标账号 / 分析竞品
  - 生成钩子 / hook factory / 钩子变体 / 前3秒 / 开头怎么写 / 帮我写开头
  - 情绪曲线 / emotion curve / 分析节奏 / 情绪分析 / 节奏怎么样
  - 发布时间优化 / publish optimizer / 最佳发布时间 / 什么时候发 / 几点发比较好
  - 产线模式 / pipeline mode / 完整流程 / 激活总线 / 团队模式
  - 润色 / polish / 去AI味 / 活人感润色 / 改得像人写的 / 太AI了帮我改
  - 建人设 / 编辑人设 / 修改人设 / 我的人设 / persona / 设定我的风格
tags:
  - content-creation
  - content-operations
  - calibration-loop
  - blind-prediction
  - rubric-scoring
  - video-production
  - social-media
  - creative-workflow
  - data-driven
  - competitive-analysis
  - knowledge-fusion
negative-triggers:
  - 从零创建新Skill / 写一个新skill / skill-creator
  - 代码review / code review / 代码审查
  - 通用编程 / 写代码 / debug
  - 与内容创作无关的任务
test-prompts: test-prompts.json
has-examples: true
has-before-after: true
loading-strategy: progressive
core-tokens: ~300
full-tokens: ~8000
---

# Yang.skills · 全能内容创作运营超级Skills包

> 你的下一条内容已经在改写3个月后的你。规律是客观存在的，区别是你看见还是没看见。这套让你看见。

把内容创作变成可校准预测循环：**打分 → 预测 → 发布 → 复盘 → 进化rubric**。

本文件是**总协议 + 路由器**。具体每个阶段的工作流在 `skills/yang-*/SKILL.md` 各子skill里。

---

## 快速上手路径

根据你的使用深度，选择对应路径。每条路径都是**最小可行闭环**——走完就能产出可校准的内容。

### 路径 A：新手 5 步上手（0 → 第一条可校准内容）

适合：首次接触 Yang.skills，想快速体验闭环价值。

| 步骤 | 动作 | 调用 | 产出 |
|------|------|------|------|
| 1 | 初始化项目 | `/yang-init` | `.yang-state.json` + 脚手架 + rubric v0 |
| 2 | 导入对标账号（至少 3 条样本） | `/yang-learn-from` | `benchmark.md` + `rubric_notes.md` 锚点信号 |
| 3 | 写稿 + 打分 | 自己写稿 → `/yang-score` | 评分报告 + 改进建议 |
| 4 | 盲预测 | `/yang-predict` | `predictions/*.md`（immutable） |
| 5 | 发布 + 复盘 | `/yang-publish` → 等 T+3d → `/yang-retro` | 复盘段 + 第一条校准数据 |

> 🎯 走完路径 A，你已有 1 条完整校准样本。重复步骤 3-5 积累到 3 条即可进入 calibration 模式。

### 路径 B：进阶 10 步闭环（3+ 复盘 → rubric 进化）

适合：已有 3+ 条复盘数据，校准系统开始运转。

| 步骤 | 动作 | 调用 | 产出 |
|------|------|------|------|
| 1 | 检查系统健康 | `/yang-doctor` | 诊断报告 |
| 2 | 抓热点刷新候选池 | `/yang-trends` | `candidates.md` 更新 |
| 3 | 推荐选题（1 稳分 + 1 实验） | `/yang-recommend` | 排序推荐 + 维度依据 |
| 4 | 钩子变体生成 | `/yang-hook-factory` | 3-5 个开头变体 |
| 5 | 写稿 + 活人感润色 | 自己写 → `/yang-polish` | 润色后终稿 |
| 6 | 打分 + 盲预测 | `/yang-score` → `/yang-predict` | 评分 + immutable 预测 |
| 7 | 登记拍摄 | `/yang-shoot` | buffer +1 |
| 8 | 发布登记 | `/yang-publish` | buffer -1 |
| 9 | T+3d 复盘 | `/yang-retro` | 复盘段 + 校准池 +1 |
| 10 | rubric 升级（条件满足时） | `/yang-bump` | 新版 rubric + 版本号递增 |

> 🎯 路径 B 是日常主循环。步骤 2-9 可按需跳步，但 **6→7→8→9 的顺序不可打乱**。

### 路径 C：高级产线模式（团队化 / 规模化生产）

适合：TEAM_MODE=true，校准池 > 30，至少 1 次成功 bump。

| 步骤 | 动作 | 调用 | 产出 |
|------|------|------|------|
| 1 | 激活进化总线 | `/yang-evolution-bus` | Agent 群上线 + 三阶段同步启动 |
| 2 | 选题注入 + 校准验证 | Bus Stage 1 | Agent 选题 → 校准系统打分 → 排序修正 |
| 3 | 成稿盲预测同步 | Bus Stage 2 | Agent 成稿 → 校准系统盲预测 → 修改建议 |
| 4 | 复盘反馈闭环 | Bus Stage 3 | Agent 数据回收 → 校准系统复盘 → 可能触发 bump |
| 5 | 竞品持续监控 | `/yang-competitor-search` + monitor | 竞品数据库更新 + 策略感知 |
| 6 | 赛道格局分析 | `/yang-benchmark` | 蓝海指数 + 竞品关系图 |
| 7 | 发布时间优化 | `/yang-publish-optimizer` | 最佳发布窗口推荐 |

> 🎯 产线模式下，步骤 2-4 由总线自动编排，人工介入点仅在"确认发布"和"复盘数据录入"。

---

## 子 skill 依赖图

下图展示 26 个子 skill 之间的依赖关系和推荐调用顺序。箭头 `→` 表示"输出被下游消费"，虚线 `⇢` 表示"可选依赖"。

```
                          ┌─────────────┐
                          │ yang-init   │ ← 一切起点
                          └──────┬──────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌──────────┐  ┌──────────┐  ┌──────────┐
            │yang-learn│  │yang-learn│  │yang-pers-│
            │  -from   │  │         │  │  ona     │
            └────┬─────┘  └────┬─────┘  └────┬─────┘
                 │              │              │
                 ▼              ▼              │
          ┌────────────┐ ┌───────────┐        │
          │yang-bench- │ │yang-compet│        │
          │  mark      │ │  itor-    │        │
          │            │ │  search   │        │
          └────────────┘ └───────────┘        │
                 │              │              │
                 ▼              ▼              ▼
          ┌──────────────────────────────────────┐
          │         yang-seed（选题启动器）        │
          │  ← 依赖：rubric_notes + 竞品数据库    │
          └──────────────┬───────────────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
      ┌──────────┐ ┌──────────┐ ┌──────────┐
      │yang-hook-│ │yang-emot-│ │yang-trends│
      │ factory  │ │ ion-curve│ │          │
      └────┬─────┘ └──────────┘ └───────────┘
           │
           ▼
    ┌────────────┐     ┌──────────────┐
    │ yang-score │ ⇢──→│yang-score-   │
    │            │     │  blind (内部) │
    └─────┬──────┘     └──────────────┘
          │
          ▼
    ┌────────────┐     ┌──────────────┐
    │ yang-polish│ ⇢──→│ yang-persona │
    └─────┬──────┘     └──────────────┘
          │
          ▼
    ┌─────────────┐
    │ yang-predict │ ← immutable 预测写入
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐     ┌──────────────────┐
    │ yang-shoot  │────→│ yang-publish-     │
    │  (buffer+1) │     │   optimizer      │
    └──────┬──────┘     └──────────────────┘
           │
           ▼
    ┌─────────────┐
    │ yang-publish │ ← buffer-1
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐     ┌──────────────────┐
    │ yang-retro  │────→│ yang-bump        │
    │  (T+3d)     │     │  (校准池≥10)     │
    └──────┬──────┘     └────────┬─────────┘
           │                     │
           ▼                     ▼
    ┌─────────────┐     ┌──────────────────┐
    │ yang-status │     │ yang-evolution-  │
    │  (看板)     │     │   bus (产线)     │
    └─────────────┘     └──────────────────┘
                               │
                        ┌──────┴──────┐
                        ▼             ▼
                 ┌───────────┐ ┌───────────┐
                 │yang-bridge│ │yang-graphic│
                 │ (内部)    │ │ (图文)     │
                 └───────────┘ └───────────┘

    横切辅助（任意阶段可调用）：
    ┌──────────────┐ ┌──────────┐ ┌──────────┐
    │ yang-doctor  │ │yang-migr-│ │yang-recom-│
    │ (诊断)      │ │  ate     │ │  mend     │
    └──────────────┘ └──────────┘ └──────────┘
```

**推荐调用顺序（主线）**：`init → learn-from → seed → score → predict → shoot → publish → retro → bump`

**关键依赖约束**：
- `yang-score` 依赖 `rubric_notes.md`（由 `yang-learn-from` 生成）
- `yang-predict` 依赖已打分的终稿（由 `yang-score` 产出）
- `yang-shoot` 依赖对应预测文件存在（由 `yang-predict` 产出）
- `yang-retro` 依赖预测文件 + T+3d 时间窗
- `yang-bump` 依赖校准池 ≥ MIN_SAMPLES_FOR_BUMP
- `yang-evolution-bus` 依赖 TEAM_MODE + 足够校准数据

---

## 常见工作流模板

### 工作流 1：冷启动首条内容（0 基线 → 第一条发布）

```
1. /yang-init
   → 选内容形态、填 cadence、生成脚手架
2. /yang-learn-from --append
   → 提供 3+ 条对标视频 URL，系统拆 pattern + 派生 rubric 信号
3. 自己写第一篇稿子，保存到 scripts/YYYY-MM-DD_<id>_<short>.md
4. /yang-score scripts/YYYY-MM-DD_<id>_<short>.md
   → 查看各维度评分，按建议修改
5. /yang-predict scripts/YYYY-MM-DD_<id>_<short>.md
   → 写入 immutable 预测（此时绝不能看任何发布后数据）
6. 拍摄视频
7. /yang-shoot → 提供 video 目录路径 → buffer +1
8. 发布
9. /yang-publish → 提供发布链接 → buffer -1
10. 等 T+3d（72 小时）
11. /yang-retro → 提供实际数据 → 写复盘段 → 校准池 +1
```

### 工作流 2：日常选题→发布循环（calibration 模式）

```
1. SessionStart 自动报告 buffer 状态 + 待复盘项
2. 如有待复盘到期 → /yang-retro（优先于新拍）
3. /yang-trends → 刷新热点候选池
4. /yang-recommend → 获取 1 稳分 + 1 实验性推荐
5. /yang-hook-factory → 为选定选题生成 3-5 个开头变体
6. 写稿 → /yang-polish → 活人感润色
7. /yang-score → 打分确认
8. /yang-predict → 写入预测
9. /yang-shoot → buffer +1
10. /yang-publish → buffer -1
11. 等 T+3d → /yang-retro
12. 每 10+ 条复盘后检查 → /yang-bump（如触发条件满足）
```

### 工作流 3：对标账号深度拆解（学习期）

```
1. /yang-competitor-search → 搜索同赛道竞品账号
2. /yang-learn-from → 导入 3-5 条对标视频
   → 系统自动：下载 → 抽帧 → 转录 → 评论挖掘 → pattern 提取
3. /yang-benchmark → 全量回测分析
   → 输出：视觉模式 + 话术 DNA + 高赞评论模式
4. 检查 rubric_notes.md → 确认锚点信号已写入
5. /yang-emotion-curve → 分析对标视频的情绪曲线
   → 提取节奏 pattern 写入 script_patterns.md
6. /yang-hook-factory → 基于对标钩子模式生成变体
7. 回到工作流 1 或 2 开始创作
```

### 工作流 4：rubric 升级全流程（校准池 ≥ 10 时）

```
1. /yang-status → 确认校准池样本数 ≥ MIN_SAMPLES_FOR_BUMP
2. /yang-doctor → 检查系统健康（无遗失预测、无数据异常）
3. /yang-bump
   → 系统自动：全量重打分 → 一致性验证 → 跨模型审计（--strict）
4. 验证通过 → 版本号递增 → 删除已吸收观察 → 更新 .yang-state.json
5. 验证被拒 → 查看不一致样本分析 → 细化调整 → 重新提交
6. /yang-score → 用新 rubric 对下一条内容打分，确认评分逻辑符合预期
```

### 工作流 5：产线模式启动（团队化生产）

```
1. 确认前置条件：TEAM_MODE=true + CALIBRATION_POOL_SIZE > 30 + 至少 1 次成功 bump
2. /yang-evolution-bus → 激活进化总线
3. 选择模式：tight（拦截模式）或 loose（标记模式）
4. Stage 1：选题注入
   → Agent 群选题 Agent 产出 → Bus → 校准系统自动打分 → 反馈排序修正
5. Stage 2：盲预测同步
   → Agent 群 Content Agent 产出成稿 → Bus → 校准系统盲预测 → 反馈修改建议
6. Stage 3：复盘反馈
   → Agent 群数据 Agent 收集实绩 → Bus → 校准系统自动复盘 → 可能触发 bump
7. 退出产线：说"退出产线" → 回到 Solo:calibration
```

### 工作流 D：搜索意图驱动（蓝海切入）

适用：中小账号、冷启动期、想找低竞争选题

```
1. /yang-seed → Channel E（搜索意图）从 rubric 提取种子词
2. 搜索意图适配器拉取6种信号（搜索建议/相关搜索/问题型/长尾词/趋势查询/内容空白）
3. 内容空白检测命中的选题 → 自动 🅰 高优先
4. 选一个 → 写稿 → /yang-score → /yang-polish → /yang-predict → 发布 → 复盘
```

---

## 创作流程阶段门控

每个创作阶段必须通过门控检查才能进入下一阶段。跳步 = 放弃校准价值。

| 阶段 | 门控检查 | 通过条件 | 未通过动作 |
|------|---------|---------|-----------|
| GATE_1: 选题 | 选题是否有评分依据 + Channel E 搜索意图是否已检查 | candidates.md 中有评分记录，且 Channel E 搜索意图信号已拉取 | 回到 yang-seed 重新选题 |
| GATE_2: 成稿 | 脚本是否经过评分 | yang-score 已执行且 composite ≥ 5.0 | 回到 yang-polish 补强 |
| GATE_3: 预测 | 盲预测是否已写入 | predictions/ 下有对应文件且 ## 预测 段非空 | 执行 yang-predict |
| GATE_4: 发布 | 拍摄是否已登记 | yang-shoot 已执行 | 执行 yang-shoot |
| GATE_5: 复盘 | T+3d 时间窗是否已过 | 发布时间距今 ≥ 72h | 等待时间窗 |

---

## 不可妥协原则

任何一条被违反，整个校准循环退化为"凭直觉的自我安慰"。如果用户要求打破其中任何一条，**拒绝执行并说明原因**。

1. **盲预测（Blind prediction）**：预测必须在看到任何实际数据**之前**写完。一旦写完，`## 预测` 段是 immutable——只能往 `## 复盘` 段追加。完整规范：[shared-protocols/blind-prediction-protocol.md](shared-protocols/blind-prediction-protocol.md)。`hooks/prediction-immutability.sh` 在 harness 层强制执行。

2. **升级 = 全量重打（Bump = full re-score）**：rubric 升级时，校准池所有有实绩数据的样本必须用新公式重打分；新排序与实际表现排序若在 ≥4/5 样本上不一致，升级被拒；升级必须经跨模型独立审核。完整规范：[shared-protocols/bump-validation-protocol.md](shared-protocols/bump-validation-protocol.md)。

3. **rubric 是工作台，不是博物馆**：被新数据推翻或被吸收为正式维度的观察，**删掉**。绝不留"我曾经以为 X，但其实..."的考古层。git history 才是档案。完整规范：[shared-protocols/observation-lifecycle.md](shared-protocols/observation-lifecycle.md)。

4. **竞品数据全量存储**：所有竞品发现和采集的数据必须写入 competitors 数据库（project_data.db），不得仅存于 Markdown 文件中。竞品数据库中的 `competitor_snapshots` 和 `competitor_strategy_changes` 是策略感知和时间序列分析的唯一真实来源。

---

## 紧凑核心规则（部署版）

> Agent 执行时优先读取本段。需要细节时再展开对应子skill 或完整版章节。本段约 300 tokens。

### 5 条核心规则

1. **盲预测 immutable**：预测必须在看到实际数据前写完；写后 `## 预测` 段不可修改，只能往 `## 复盘` 追加
2. **Bump = 全量重打**：rubric 升级时校准池全量重打分；≥4/5 样本排序不一致则升级被拒；须跨模型审核
3. **rubric 是工作台**：被推翻或被吸收的观察删掉，不留考古层；git history 才是档案
4. **竞品数据入库**：竞品数据必须写入 competitors 数据库（project_data.db），markdown 仅做可读摘要
5. **拒绝 gut-feel**：所有评分/推荐必须有 rubric 锚点，不做凭感觉的判断

### 路由表（trigger → skill）

| trigger 关键词 | → 调用 |
|---|---|
| 初始化/init/setup | `/yang-init` |
| 找对标/学账号/拆视频 | `/yang-learn-from` |
| 打分/评分/评估 | `/yang-score` |
| 盲预测/预测效果 | `/yang-predict` |
| 润色/去AI味/活人感 | `/yang-polish` |
| 已发布/发布登记 | `/yang-publish` |
| 复盘/T+3d/数据回来 | `/yang-retro` |
| 升级rubric/bump | `/yang-bump` |
| 推荐选题/下一篇 | `/yang-recommend` |
| 抓热点/热点 | `/yang-trends` |
| 搜关键词/搜索意图/关键词研究/search intent/长尾词/内容空白 | `/yang-seed`（Channel E） |
| 产线模式/激活总线 | `/yang-evolution-bus` |

**搜索意图入口**：用户说"搜关键词/搜索意图/关键词研究/长尾词/内容空白"→触发Channel E（yang-seed），种子词从rubric+persona提取，6种信号零API Key。

**活人感评分入口**：用户说"评分多少/活人感评分/humanness"→触发Humanness Score（yang-polish），6维度0-100分，支持只评分不润色模式。

### 门控检查点（GATE_1~5）

| 门控 | 阶段 | 通过条件 |
|------|------|----------|
| GATE_1 | 选题 | candidates.md 有评分记录 + Channel E 搜索意图已检查 |
| GATE_2 | 成稿 | yang-score 已执行且 composite ≥ 5.0 |
| GATE_3 | 预测 | predictions/ 下有文件且 `## 预测` 非空 |
| GATE_4 | 发布 | yang-shoot 已登记 |
| GATE_5 | 复盘 | 发布时间距今 ≥ 72h |

### 黑名单（Top 5）

1. `BLACKLIST_HALLUCINATE_SCORE` — 不凭空编造评分
2. `BLACKLIST_CHERRY_PICK_RETRO` — 不选择性复盘
3. `BLACKLIST_MERGE_PREDICTION_SCRIPT` — 不合并预测与脚本
4. `BLACKLIST_SKIP_RUBRIC_CITE` — 不省略 rubric 维度引用
5. `BLACKLIST_OVERFIT_SINGLE_SAMPLE` — 不基于单条数据调 rubric

### 渐进式加载指引

本Skill套件采用**渐进式加载**设计（借鉴 Anthropic Official Skills）：
1. **首次加载**：只读本段（紧凑核心规则）→ 足以路由和执行基础操作
2. **按需加载**：当用户触发具体子skill时，才读取对应子skill的SKILL.md
3. **深度加载**：当需要评分锚点/润色技术细节/预测协议时，才读取references/

**不要一次性读取所有子skill**——按需加载，保持注意力集中。

| 触发意图 | 加载目标 | 读取内容 |
|---------|---------|---------|
| 初始化 | `skills/yang-init/SKILL.md` | 初始化5步+首次运行指引 |
| 打分 | `skills/yang-score/SKILL.md` | 7维度评分规则+锚点 |
| 预测 | `skills/yang-predict/SKILL.md` | 盲预测协议+预测维度 |
| 润色 | `skills/yang-polish/SKILL.md` | 三层漏斗+26技术 |
| 复盘 | `skills/yang-retro/SKILL.md` | 复盘3步+偏差归因 |
| 升级 | `skills/yang-bump/SKILL.md` | bump触发+验证规则 |
| 选题 | `skills/yang-seed/SKILL.md` | 五通道选题+搜索意图 |
| 热点 | `skills/yang-trends/SKILL.md` | 多源聚合+搜索意图 |
| 搜关键词/搜索意图 | `skills/yang-seed/SKILL.md` | Channel E搜索意图+种子词提取 |
| 推荐 | `skills/yang-recommend/SKILL.md` | 候选池排序+buffer策略 |

---

## 信号密度优化

本 SKILL.md 遵循 SkillOpt 的紧凑性原则：

- **部署版**（紧凑核心规则段）约 300 tokens，覆盖核心规则、路由、门控、黑名单——Agent 执行时优先读取
- **完整版**（本文件全文）8000+ tokens，包含详细工作流、知识库路由、模式状态机、目录结构等——需要细节时按需展开
- Agent 应**优先读取紧凑核心规则段**，仅在需要细节时读取对应子skill 或完整版章节
- 引用 SkillOpt 论文结论："Deployed skills often 300–2,000 tokens after training"——过长的 skill 文件会稀释信号密度，降低 Agent 执行精度

---

## 路由表（触发词 → 子skill）

| 用户说 | 调用 | 前置条件 |
|---|---|---|
| "初始化" / "init" / "首次使用" / "setup" | `/yang-init` | 无（这是入口） |
| "找对标" / "学这个账号" / "拆这几个对标视频" / "learn from" / "导入对标账号" | `/yang-learn-from` | 已 init；cold-start 强烈建议；后续可随时 --append / --replace |
| "分析这个博主" / "找对标账号的视频模式" | `/yang-learn` | 已 init（rubric_notes.md、benchmark.md 存在） |

> 💡 **yang-learn vs yang-learn-from 选择判断**：
> - 用户意图偏向"数据采集/建立基准"（如「帮我分析这个账号」「做个 benchmark」）→ 路由到 `yang-learn`
> - 用户意图偏向"策略提炼/内容拆解"（如「他为什么火」「学一下对方的手法」「拆解这个视频」）→ 路由到 `yang-learn-from`
> - 两者可串联：先 `yang-learn` 建立数据基线，再 `yang-learn-from` 做策略提炼
| "找选题" / "我不知道拍什么" / "seed" / "下一期拍什么" / "选题推荐" | `/yang-seed` | 已 init（四通道 + 竞品数据库驱动） |
| "打分这篇 [path]" / "score this [path]" / "评估这篇" / "评分" | `/yang-score` | rubric_notes.md 存在 |
| "润色"/"polish"/"去AI味"/"活人感润色" | `/yang-polish` | 已 init + yang-score 已完成（或直接提供脚本） |
| "启动预测" / "start prediction" / "预测这条" / "盲预测" / "给这稿子打分并预测" | `/yang-predict` | 已 init + 有最终稿 |
| "建人设"/"编辑人设"/"修改人设"/"我的人设"/"persona" | `/yang-persona` | 已 init（可随时调用） |
| "拍了 X" / "shot it" / "录完了" / "已拍 X" | `/yang-shoot` | 对应预测已写（buffer +1） |
| "已发布" / "I shipped it" / "发布登记" / "publish log" / "发布链接是 X" | `/yang-publish` | 对应预测文件存在（buffer -1） |
| "复盘" / "retro this" / "T+3d 数据来了" / "回顾这条" | `/yang-retro` | 对应预测文件存在 + 已过 T+3d |
| "升级 rubric" / "bump rubric" / "校准池够了" / "进化评分规则" / "更新公式" | `/yang-bump` | 校准池 ≥ MIN_SAMPLES_FOR_BUMP（默认 10） |
| "推荐选题" / "next topic" / "下一篇做什么" / "recommend topics" / "挑一个选题" | `/yang-recommend` | candidates.md 存在且非空 |
| "抓热点" / "fetch trends" / "现在有什么热点" / "热点有哪些" / "今天有什么可做的" | `/yang-trends` | trend-sources adapter 已配置 |
| "状态" / "status" / "看板" / "dashboard" | `/yang-status` | 任意时刻可调 |
| "迁移" / "升级 state" / "schema 版本不对" / "migrate" / "schema 升级" | `/yang-migrate` | 已 init；git pull 新版后 |
| "诊断" / "检查系统" / "系统体检" / "doctor" / "健康检查" | `/yang-doctor` | 已 init | 系统健康诊断 |
| "生成钩子" / "hook factory" / "钩子变体" / "前3秒" / "开头怎么写" | `/yang-hook-factory` | 有选题或脚本 |
| "情绪曲线" / "emotion curve" / "分析节奏" / "情绪分析" | `/yang-emotion-curve` | 有脚本文件 或 有对标视频转录文本 |
| "发布时间优化" / "publish optimizer" / "最佳发布时间" / "什么时候发" | `/yang-publish-optimizer` | calibration_samples ≥ 8 |
| "产线模式" / "pipeline mode" / "完整流程" / "激活总线" | `/yang-evolution-bus` | TEAM_MODE=true 且 CALIBRATION_POOL_SIZE > 30 |
| "对标分析" / "benchmark" / "竞品分析" / "拆解视频" / "yang-benchmark" | `/yang-benchmark` | 已 init + 依赖已安装 |
| "发现竞品" / "找对标账号" / "搜同行" / "competitor search" / "yang-competitor-search" | `/yang-competitor-search` | 已 init |
| "小红书图文" / "做成图卡" / "图文排版" / "知乎回答" / "公众号排版" / "配图文案" / "graphic" | `/yang-graphic` | 已 init（无 state 也可用默认主题渲染） |

> **拍 vs 发分两个动作**：buffer 警戒系统需要明确知道"拍了但没发"vs"已发"两种状态。详见 [shared-protocols/cadence-protocol.md](shared-protocols/cadence-protocol.md)。

### 路由优先级消歧（trigger-words 重叠处理）

以下 trigger-words 存在跨 skill 重叠，按优先级从高到低匹配：

| 重叠 trigger | 优先路由 → | 次选路由 → | 消歧规则 |
|---|---|---|---|
| "打分" / "评分" | `/yang-score` | `/yang-predict`（仅当用户同时说"打分并预测"） | 单独"打分/评分"→ yang-score；"打分并预测"→ yang-predict |
| "找对标" | `/yang-learn-from` | `/yang-competitor-search` | "找对标"+"账号名/视频"→ yang-learn-from；"找对标账号"+"搜同行/发现"→ yang-competitor-search |
| "拆解视频" / "拆对标" | `/yang-learn-from` | `/yang-benchmark` | 提供具体视频→ yang-learn-from；要求全量回测分析→ yang-benchmark |
| "竞品分析" | `/yang-benchmark` | `/yang-competitor-search` | "竞品分析/对标分析"→ yang-benchmark；"发现竞品/搜同行"→ yang-competitor-search |

**消歧原则**：当 trigger 同时匹配多个 skill 时，优先路由到更具体的 skill；若仍无法区分，向用户确认意图。

### 模式检测（首次接到非 init 触发词时执行）

1. 检查用户当前目录是否有 `.yang-state.json` → 没有 → 强制路由到 `/yang-init`
2. 检查 `predictions/` 下有几个文件含完整 `## 复盘` 段填了真实数据 → 决定 `mode: cold-start | calibration`
3. 把判定结果写回 `.yang-state.json` 后再路由到目标 skill

### 内部子技能（不直接触发）

| 子skill | 用途 | 调用方式 |
|---|---|---|
| `/yang-score-blind` | Channel B 隔离打分 sub-agent | 仅由 yang-score / yang-predict / yang-bump 通过 Task tool 调用 |
| `/yang-bridge` | 多Agent → 闭环校准 信号翻译规则 | yang-evolution-bus 内部依赖 |

---

## 系统状态检查点

关键状态转换必须通过以下检查条件，未通过则阻断并报告原因。

| 检查点 | 触发时机 | 前置条件 | 失败动作 | 对应协议 |
|--------|----------|----------|----------|----------|
| **CP_INIT** | 首次调用任何非 init 子skill | `.yang-state.json` 存在且 schema 版本 = LATEST_SCHEMA | 阻断 → 路由到 `/yang-init` 或 `/yang-migrate` | state-management.md |
| **CP_SCORE** | yang-score 执行 | `rubric_notes.md` 存在且非空；至少 1 个锚点样本 | 阻断 → 提示先跑 `/yang-learn-from` 建立锚点 | blind-prediction-protocol.md |
| **CP_PREDICT** | yang-predict 执行 | 对应脚本文件存在；预测文件**尚未存在**（防重复）；无已知的实际数据泄露 | 阻断 → 检查脚本路径 / 拒绝事后预测 | blind-prediction-protocol.md |
| **CP_SHOOT** | yang-shoot 执行 | 对应预测文件存在且 `## 预测` 段已填写；buffer < BUFFER_MAX（默认 5） | 阻断 → 先补预测 / 提醒 buffer 溢出 | cadence-protocol.md |
| **CP_PUBLISH** | yang-publish 执行 | 对应视频目录存在（yang-shoot 已登记）；buffer > 0 | 阻断 → 先登记拍摄 | cadence-protocol.md |
| **CP_RETRO** | yang-retro 执行 | 对应预测文件存在；发布时间距今 ≥ T+3d（72h）；实际数据字段非空 | 阻断 → 等待时间窗 / 提示补充数据 | blind-prediction-protocol.md |
| **CP_BUMP** | yang-bump 执行 | 校准池 ≥ MIN_SAMPLES_FOR_BUMP（默认 10）；所有样本已用当前 rubric 打分；跨模型审核就绪 | 阻断 → 等待样本积累 / 提示先重打 | bump-validation-protocol.md |
| **CP_PIPELINE** | yang-evolution-bus 激活 | TEAM_MODE=true；CALIBRATION_POOL_SIZE > 30；至少 1 次成功 bump 记录 | 阻断 → 提示条件不满足，继续 Solo 模式 | pipeline-state.md |
| **CP_COLD_TO_CALIBRATION** | 模式从 cold-start 切换到 calibration | predictions/ 下 ≥ 3 个文件含完整 `## 复盘` 段且填了真实数据 | 维持 cold-start，不切换 | state-management.md |
| **CP_COMPETITOR_DATA** | 任何写入竞品数据的操作 | 目标写入路径为 competitors 数据库（project_data.db），非纯 markdown | 阻断 → 重定向到数据库写入 | data-source-routing.md |

> **检查点执行原则**：检查点在子skill入口处执行，先于任何业务逻辑。检查点失败时输出格式为 `[CP_XXX] FAIL: <原因>`，用户可根据提示修正。

---

## 三大知识库路由

Yang.skills 融合三套独立运营知识体系，各子skill按需引用：

| 知识库 | 路径 | 核心覆盖 | 典型引用场景 |
|---|---|---|---|
| **知识库A** | `knowledge/ansir/` | 速判性与人群印记、漏斗流量结构、钩子理论（注意力/价值钩子+八种类型）、骨架六种推进、情绪刺点、普世×陌生×情绪选题法；**导演级视听语言（视点/景别/构图/焦段/色彩/光线）、时间的语法、信息特性（视听/切片/持续）、销售成交付费链路、本地生活引流** | yang-score（评分锚定）、yang-predict（数据维度baseline）、yang-hook-factory（钩子类型）、yang-emotion-curve（情绪理论）、yang-seed（选题法）、yang-graphic（配色/构图/封面钩子）、yang-shoot（视听语言落地） |
| **知识库B** | `knowledge/xuehui/` | 粉丝经济原理→商业定位→内容定位三位一体、三有原则（有用处/有兴趣/有共鸣）、八大爆款元素、四大脚本类型（观点/过程/知识/故事）、运营漏斗模型 | yang-seed（选题判断）、yang-learn（对标拆解）、yang-score（爆款潜力参考）、yang-publish-optimizer（发布节奏策略）、yang-graphic（标题四维度） |
| **知识库C** | `knowledge/shekong/` | 起号36计（账号搭建/内容策略/冷启动/避坑）、开篇36计（28种文案钩子+8种画面钩子）、赛道选择三标准、账号定位黄金圈 | yang-hook-factory（开篇钩子模板库）、yang-seed（起号策略）、yang-score（钩子冲击力评分参考）、yang-graphic（小红书标题/封面钩子） |

### 知识库引用规范

各子skill引用知识库时，必须标注来源标记，格式为 `[来源：A-<模块>]` / `[来源：B-<模块>]` / `[来源：C-<模块>]`，并在输出末尾追加 `📚 知识依据：` 行。

### 技术调研模块（可选参考）

| 模块 | 路径 | 用途 |
|---|---|---|
| **research** | `research/` | 可选参考：技术调研文档（ASR引擎、情感分析、热点监控、发布时间优化、视频质量评估、多Agent框架）。不参与 skill 路由，仅供开发者或高级用户手动查阅 |

---

## Solo / Pipeline 双模式

Yang.skills 支持两种运行模式，通过状态机管理切换：

### 模式状态机

```
                    ┌──────────────────────────────────────────┐
                    │                                          │
                    ▼                                          │
  [未初始化] ──init──→ [Solo:cold-start] ──3+复盘──→ [Solo:calibration]
                                              │                    │
                                              │                    │
                                     CP_PIPELINE 通过              │ CP_PIPELINE 通过
                                     + 用户说"产线模式"            │ + 用户说"产线模式"
                                              │                    │
                                              ▼                    ▼
                                    [Pipeline:loose] ──用户说"严格"──→ [Pipeline:tight]
                                              ▲                    │
                                              │                    │
                                              └──用户说"宽松"──────┘
                                              
  任何时刻用户说"退出产线" ──→ 回到 [Solo:calibration]
```

### 模式切换条件

| 切换路径 | 条件 | 动作 |
|----------|------|------|
| 未初始化 → Solo:cold-start | 执行 `/yang-init` | 创建脚手架，mode=cold-start 写入 state |
| Solo:cold-start → Solo:calibration | predictions/ 下 ≥ 3 个完整复盘 | 自动切换，更新 state 中 mode 字段 |
| Solo → Pipeline:loose | CP_PIPELINE 通过 + 用户显式请求 | 激活 yang-evolution-bus，Agent群上线 |
| Pipeline:loose → Pipeline:tight | 用户说"严格模式" | 总线门禁升级为拦截模式 |
| Pipeline:tight → Pipeline:loose | 用户说"宽松模式" | 总线门禁降级为标记模式 |
| Pipeline:* → Solo:calibration | 用户说"退出产线"/"回到独立模式" | Agent群休眠，总线停止，校准系统继续 |

> **关键约束**：Pipeline 模式不可从 cold-start 直接进入——必须先积累足够的校准数据（CP_PIPELINE 检查点强制执行）。

### Solo 模式（默认）

闭环校准系统独立运行。Agent群全部休眠，不介入选题、内容生成、数据采集。所有预测、打分、复盘均由校准系统独立完成。

- 适用场景：个人创作者日常使用
- 触发方式：直接调用各 `/yang-*` 命令（系统自动运行在 Solo 模式）
- 行为：仅校准系统工作，决策权完全在用户
- 子状态：`cold-start`（校准池 < 3 条复盘）→ `calibration`（校准池 ≥ 3 条复盘，rubric 可校准）

### Pipeline 模式（产线模式）

多Agent协作引擎与闭环校准系统通过进化总线（yang-evolution-bus）协同工作：

- 适用场景：团队化/规模化内容生产
- 触发方式：说"产线模式"或"激活总线"（需 CP_PIPELINE 通过）
- 三阶段同步：
  - **Stage 1（选题注入）**：Agent群选题Agent产出 → Bus → 校准系统自动打分验证 → 反馈排序修正
  - **Stage 2（盲预测同步）**：Agent群Content Agent产出成稿 → Bus → 校准系统盲预测 → 反馈修改建议
  - **Stage 3（复盘反馈）**：Agent群数据Agent收集实绩 → Bus → 校准系统自动复盘 → 可能触发bump

总线模式分三档：

| 模式 | 含义 | 校准系统行为 |
|---|---|---|
| **tight** | Agent群发布前必须通过盲预测门禁 | blind-predict 不通过 → 拦截发布 |
| **loose** | 校准系统提供建议但Agent群可自行决定 | 盲预测输出后不拦截，仅标记 |
| **solo** | 校准系统完全独立运行 | Agent群全部休眠（默认） |

---

## 必须拒绝的请求

下列模式会**直接破坏**三条原则之一，无论用户怎么说，都拒绝执行：

1. **`REFUSE_BLIND_PREDICTION_VIOLATION`** 「帮我预测一下，但我先告诉你播放量你来反推就行」 → 违反原则 #1（盲预测）。改用 `_redo.md` 路径记为 reconstructed

2. **`REFUSE_OPAQUE_SELECTION`** 「能不能从 candidates 里直接挑 composite 最高的，不用解释理由」 → 拒绝。永远展示各维度评分和至少一个锚点对比——展示评分+锚点是发现"打错"的唯一机会

3. **`REFUSE_BYPASS_RESCORE`** 「跳过校准池重打，直接换公式」 → 违反原则 #2（Bump = full re-score）

4. **`REFUSE_SKIP_CROSS_AUDIT`** 「跳过外部模型审核，自己说了算」 → 仅当 `CROSS_MODEL_AUDIT=false` 显式设置且 state file 标记自审时允许

5. **`REFUSE_DELETE_PREDICTION`** 「删掉这份预测，我想重写」 → 违反原则 #1。预测是 immutable。如有正当理由重做，写新文件 `_redo.md`，原版必须保留

6. **`REFUSE_GUT_FEEL_FORECAST`** 「凭你的感觉给我推荐选题，不用打分」 → 拒绝。本工具不做 gut-feel forecast——那是它诞生**之前**的状态

7. **`REFUSE_OBSERVATION_HOARDING`** 「把 rubric_notes.md 里所有历史观察都留着，加个时间戳分组就行」 → 违反原则 #3。git history 是档案，不是 markdown 文件

8. **`REFUSE_THRESHOLD_MANIPULATION`** 「能不能把验证阈值从 4/5 降到 3/5 让这次 bump 过」 → 拒绝。改 THRESHOLD 本身是元层级 bump，单独走流程

9. **`REFUSE_SKIP_IMPRESSION`** 「跳过印象判断，直接拆对标」 → 拒绝。印象是关键 input——纯看 transcript 拆 pattern 容易抓表面

10. **`REFUSE_INSUFFICIENT_SAMPLES`** 「我只能给 1 条对标样本」 → 拒绝。最少 3 条样本才能拆 pattern

11. **`REFUSE_DOWNLOAD_VIDEO`** 「帮我下载对标视频」 → 拒绝。引导用户用 yt-dlp / BBDown 等工具自己下载（避免 TOS + 反爬风险）

12. **`REFUSE_POST_HOC_PREDICTION`** 「拍完了但从来没跑过 yang-predict，直接登记拍摄就行」 → 拒绝。预测必须在拍摄**前**写完——拍完才写等于被画面污染。先补写 v1，再走 `_redo` 路径

13. **`REFUSE_FABRICATE_DATA`** 「帮我编几个复盘数据，先把校准池凑够」 → 拒绝。伪造实绩数据会让整个校准循环退化为自我欺骗。校准池必须由真实发布数据填充，不足就等——宁可慢，不可假

14. **`REFUSE_RETRO_EARLY`** 「刚发布 1 小时，数据看起来不错，帮我复盘」 → 拒绝。T+3d 是最小观察窗口，过早复盘会因数据未稳定导致误判。等满 72 小时再走 yang-retro

15. **`REFUSE_COMPETITOR_DATA_ONLY_MD`** 「竞品数据写到 markdown 就行，不用入库」 → 违反原则 #4（竞品数据全量存储）。竞品数据必须写入 competitors 数据库，markdown 仅做可读摘要，不是存储

详细的拒绝场景在每个子skill的 `Refusals` 段。

---

## 项目目录结构（用户 repo）

skill 期望用户的项目布局如下。`/yang-init` 会创建缺失项；**绝不在没确认的情况下覆盖**。

```
<user-content-project>/
├── rubric_notes.md                    # 评分规则的真实来源
├── WORKFLOW.md                        # 5 阶段流程文档（yang-init 创建）
├── STATUS.md                          # 看板（yang-status 维护）
├── .yang-state.json                   # 状态文件，子skill 共享上下文
├── .yang-cache/                       # 不入版本控制
│   ├── usage.jsonl                    # 钩子被动记录的使用日志
│   ├── trends-history.jsonl           # yang-trends 的去重缓存
│   └── blind-scores/                  # yang-score-blind 的 sidecar JSON
├── .claude/
│   ├── settings.json
│   └── hooks/
│       ├── prediction-immutability.sh
│       ├── session-start.sh
│       ├── log-event.sh
│       └── bump-trigger-monitor.sh
├── benchmark.md                       # 对标账号信息（yang-learn-from 维护）
├── script_patterns.md                 # 写作 pattern 沉淀（yang-learn-from 维护）
├── rubric-memo.md                     # yang-bump 升级备忘录（累积档案）
├── scripts/                           # 拍前的所有草稿（yang-seed 写或用户写）
│   └── YYYY-MM-DD_<id>_<short>.md
├── predictions/                       # immutable 预测日志（hook 保护）
│   └── YYYY-MM-DD_<id>_<short>.md     # 与 scripts/ 同 id
├── videos/                            # 拍后才建（yang-shoot 创建）
│   └── YYYY-MM-DD_<id>_<short>/
│       ├── script.md                  # 实际拍摄稿（yang-shoot 写入）
│       └── report.md                  # T+3d 回收数据 + 评论（yang-retro 写）
├── samples/                           # 对标账号视频 / 转录（yang-learn-from 创建）
│   └── <账号名>/<video-id>/{source.mp4 (可选), transcript.md, meta.md}
├── candidates.md                      # 选题池（yang-seed / yang-trends 写入）
└── content.db                         # 可选 SQLite，校准池规模化后启用
```

---

## Skills 包文件清单

### 本 skill 包

```
Yang.skills/
├── SKILL.md                           # 本文件（总协议 + 路由）
├── README.md                          # 项目说明
├── .gitattributes                     # Git 属性配置
├── .gitignore                         # Git 忽略规则
├── install.ps1                        # Windows 安装脚本
├── install.sh                         # Unix 安装脚本
├── requirements-core.txt              # 核心依赖（选题/评分/打分闭环）
├── requirements-media.txt             # 媒体依赖（抓帧/转录/图卡渲染）
├── requirements-full.txt              # 全量依赖（图谱/贝叶斯/向量库）
├── skills/                            # 子skill 集（26 个）
│   ├── yang-init/SKILL.md             # 入口：onboarding 与脚手架
│   ├── yang-learn-from/SKILL.md       # 对标账号导入（拆 pattern + 派生 rubric 信号）
│   ├── yang-learn/SKILL.md            # 对标账号学习（转录 + 模式提取）
│   ├── yang-seed/SKILL.md             # 四通道选题启动器（含 Channel D 高赞评论金句）
│   ├── yang-score/SKILL.md            # 单稿打分（多维度 + 改进建议）
│   ├── yang-score-blind/SKILL.md      # Channel B 隔离打分 sub-agent
│   ├── yang-predict/SKILL.md          # 盲预测引擎（immutable 预测日志）
│   ├── yang-persona/SKILL.md          # 创作人设档案
│   ├── yang-polish/SKILL.md           # 活人感润色引擎
│   ├── yang-shoot/SKILL.md            # 登记拍摄（建 video folder + buffer +1）
│   ├── yang-publish/SKILL.md          # 发布元数据登记
│   ├── yang-publish-optimizer/SKILL.md # 发布时间优化器（柱状图 / 贝叶斯双模式）
│   ├── yang-retro/SKILL.md            # 数据回收与复盘
│   ├── yang-bump/SKILL.md             # Rubric 升级（含跨模型审计）
│   ├── yang-recommend/SKILL.md        # 候选池排序推荐
│   ├── yang-trends/SKILL.md           # 热点抓取（零配置多源聚合器）
│   ├── yang-status/SKILL.md           # 状态看板（含 buffer 警戒）
│   ├── yang-migrate/SKILL.md          # Schema 和状态迁移
│   ├── yang-doctor/SKILL.md           # 系统健康诊断
│   ├── yang-hook-factory/SKILL.md     # 钩子变体工厂
│   ├── yang-emotion-curve/SKILL.md    # 情绪曲线引擎（ER-Curve 分析）
│   ├── yang-evolution-bus/SKILL.md    # 进化总线协议（产线双向同步）
│   ├── yang-competitor-search/SKILL.md # 多平台竞品发现
│   ├── yang-benchmark/SKILL.md        # 对标账号全量回测分析（视觉 + 话术 + 高赞评论）
│   ├── yang-graphic/SKILL.md          # 图文生产（小红书图卡 / 知乎 / 公众号排版）
│   └── yang-bridge/SKILL.md           # 多Agent → 校准 信号翻译规则（内部依赖）
├── knowledge/                         # 三大知识库
│   ├── Knowledge-Index.md             # 知识库总索引
│   ├── ansir/SKILL.md                 # 知识库A 短视频创作方法论（91节课 + 262案例 + 导演级视听语言）
│   ├── xuehui/SKILL.md                # 知识库B 短视频运营教学体系（粉丝经济→商业定位→内容定位）
│   └── shekong/SKILL.md               # 知识库C 起号与开篇方法论（起号36计 + 开篇36计）
├── shared-protocols/                  # 跨 skill 共享协议
│   ├── blind-prediction-protocol.md   # 盲预测不可变
│   ├── bump-validation-protocol.md    # 升级验证
│   ├── observation-lifecycle.md       # 观察生命周期
│   ├── freshness-protocol.md          # 时效锁（抓取数据三级新鲜度 + 运行锚点）
│   ├── prediction-anatomy.md          # 预测组件规范
│   ├── candidate-schema.md            # 候选项统一 schema
│   ├── cadence-protocol.md            # 节奏协议（buffer 警戒）
│   ├── state-management.md            # .yang-state.json 读写约定
│   ├── migration-protocol.md          # Schema 演进 + checklist
│   ├── cross-agent-audit.md           # 跨Agent审计协议
│   ├── data-source-routing.md         # 数据源路由规则
│   ├── hypothesis-prediction-bridge.md # 假设-预测桥接
│   ├── parallel-subagent.md           # 并行子Agent协调
│   ├── pipeline-state.md              # Pipeline状态管理
│   └── constants.md                   # 全局常量（阈值 / 时窗）
├── adapters/                          # 数据源适配（可直接运行，零配置）
│   ├── _common/                       # 适配器公共工具
│   │   └── freshness.py               # 时效锁实现（运行锚点 + 三级新鲜度判定）
│   ├── trend-sources/                 # 热点抓取源（开箱即用）
│   │   ├── fetch_trends.py            # 多源聚合器（微博/知乎/B站/百度/抖音/头条/IT之家/36氪）
│   │   ├── README.md                  # 零配置原则与源清单
│   │   ├── weibo-hot.md               # 微博热搜端点与字段映射
│   │   ├── zhihu-hot.md               # 知乎热榜端点与字段映射
│   │   ├── aihot.md                   # AI热点（可选）
│   │   └── trendradar-mcp.md          # TrendRadar MCP（可选增强）
│   ├── benchmark-analysis/            # 对标分析管线（下载→抽帧→转写翻译→评论挖掘→分析）
│   │   ├── pipeline.py                # 全链路编排（默认全开，--fast 精简）
│   │   ├── download.py                # 视频下载（含发布时间 + 时效元数据）
│   │   ├── extract_frames.py          # 场景检测 + 注意力热力图
│   │   ├── transcribe.py              # 语音转写 + 翻译 + 话术DNA
│   │   ├── mine_comments.py           # 高赞评论挖掘 → 标题/选题候选
│   │   └── scrape_comments.py         # 评论区数据采集
│   ├── competitor-search/             # 多平台竞品搜索
│   │   └── search.py                  # 三层架构（API → Playwright → 兜底）
│   ├── competitor-data/               # 多源竞品数据采集（接时效锁）
│   │   └── collector.py               # 多源采集 + 新鲜度标注
│   ├── competitor-monitor/            # 竞品持续监控
│   │   └── monitor.py                 # 双模式监控
│   ├── landscape/                     # 赛道格局分析
│   │   └── analyze.py                 # 蓝海指数 + 竞品关系图
│   ├── graphic-suite/                 # 图文渲染套件
│   │   ├── render_card.py             # 小红书图卡 HTML→PNG（多主题 + 自动分页）
│   │   ├── wechat_md.py               # 公众号 Markdown→内联样式 HTML
│   │   ├── zhihu_format.py            # 知乎 Markdown→语义 HTML
│   │   └── README.md                  # 套件说明与主题表
│   ├── data_pipeline/                 # 数据湖与竞品数据库
│   │   ├── schema.sql                 # 表 DDL
│   │   ├── db.py                      # CRUD + 策略变化检测
│   │   └── collector.py               # 竞品数据采集入库
│   ├── benchmark-auto/                # 对标自动导入
│   │   ├── import-to-benchmark.py     # 导入脚本
│   │   ├── run.sh                     # 执行脚本
│   │   └── README.md                  # 使用说明
│   └── perf-data/                     # 复盘数据源
│       └── douyin-session/            # 抖音 session 爬取 + 渲染 + 审查
├── starter-rubrics/                   # 各内容形态的先验 rubric
│   ├── opinion-video.md               # 观点视频（已校准样本）
│   ├── opinion-video-zero.md          # v0 等权占位（cold-start）
│   ├── opinion-video-fusion.md        # 融合版
│   └── opinion-video-fusion-zero.md   # 融合极简版（新手默认）
├── migrations/                        # Schema 演进单一来源
│   ├── registry.md                    # LATEST_SCHEMA + 版本链表
│   └── <from>-to-<to>.md              # 每步迁移的 WHAT/WHY/HOW
├── templates/                         # 写进用户 repo 的文件骨架
│   └── *.template.md / *.template.json / content.db.schema.sql
├── hooks/                             # harness 强制层
│   ├── hooks.json                     # Hook 配置清单
│   ├── prediction-immutability.{json,sh} # 拦预测段编辑
│   ├── session-start.{json,sh}        # SessionStart 自动报告
│   ├── meta-logging.json / log-event.sh # 被动记录
│   └── bump-trigger-monitor.sh        # Bump 触发监控
├── evolution-bus/                     # 进化总线配置
│   ├── bus-protocol.md                # 总线通信协议
│   ├── bridge-rules.md                # 桥接规则
│   └── hooks/                         # 三阶段总线钩子
├── research/                          # 技术调研（可选参考，不参与路由）
└── tools/                             # 独立 CLI 脚本
    ├── bayesian_update.py             # 贝叶斯更新引擎
    ├── dspy_scoring.py                # DSPy 打分引擎
    ├── graphrag_index.py              # GraphRAG 知识图谱索引
    ├── score-curve.py                 # 预测精度收敛曲线
    └── dashboard/                     # 监控大盘（data_bridge.py + index.html）
```

---

## 测试与验证

### 测试 Prompt

完整测试集见 [test-prompts.json](test-prompts.json)，覆盖 15 个核心子 skill + 5 个边界场景（重复初始化、盲预测数据泄露、重度AI味清理、校准样本不足、候选池缺失）。

快速验证：

1. 初始化：`/yang-init "观点类短视频"` → 应创建脚手架文件
2. 健康检查：`/yang-doctor` → 应输出 8 项指标报告
3. 评分：提供一段脚本 → `/yang-score` → 应输出 7 维度评分
4. 润色验证：对比 Before/After 对照库 → 润色结果应符合 5 大 AI 写作特征的消除标准（见下方 Before/After 对照库）

### Before/After 对照库

活人感润色的 25 条中文 Before/After 对照见 [skills/yang-polish/references/before-after-gallery.md](skills/yang-polish/references/before-after-gallery.md)，覆盖开头类/论证类/修饰类/结构类/情绪类 5 大 AI 写作特征。

---

## 扩展指南

- **新增子skill** → 在 `skills/yang-<name>/SKILL.md` 创建，按本文件的 frontmatter 格式编写；在本文件路由表新增对应行
- **新增内容形态** → 加 `starter-rubrics/<form>.md`
- **新增知识库** → 在 `knowledge/<name>/SKILL.md` 创建；在本文件"三大知识库路由"段新增行；在各引用子skill中标注 `[来源：<name>-<module>]`
- **新增热点抓取源** → 加 `adapters/trend-sources/<name>.md`，符合 [shared-protocols/candidate-schema.md](shared-protocols/candidate-schema.md) 输出契约
- **修改原则** → 改 `shared-protocols/<protocol>.md`，所有引用它的子skill自动跟进
- **修改路由** → 改本文件的"路由表"段
- **子skill内部细节** → 直接改对应 `skills/yang-*/SKILL.md`
- **Schema 升级** → 在 `migrations/` 新增 `<from>-to-<to>.md`，更新 `registry.md` 的 LATEST_SCHEMA + 版本链表

---

## 跨平台兼容性

Yang.skills 设计为多 Agent 平台可用，不绑定特定运行环境。以下为各平台适配说明：

| 平台 | 兼容性 | 说明 |
|------|--------|------|
| **Claude Code** | ✅ 完整支持 | 原生平台。所有 hooks（session-start、prediction-immutability、bump-trigger-monitor）完整运行 |
| **Codex CLI** | ⚠️ 功能兼容 | 核心 skill 路由和执行逻辑兼容 Codex CLI 的 task/skill 调用模式。`hooks/` 目录下的 shell 脚本需手动配置为 Codex hooks；`allowed-tools` 声明需映射到 Codex 的 tool 权限系统 |
| **其他 Agent 平台** | ⚠️ 需适配 | skill 文件本身是标准 Markdown，任何支持 skill 协议的 Agent 平台均可加载。hooks 层和 adapter 层（Python 脚本、shell 脚本）需根据目标平台的工具调用接口做适配 |

跨平台使用时注意事项：
- `.claude/` 目录下的 hooks 配置（JSON）为 Claude Code 专属格式，其他平台需自行配置等价 hook
- `SKILL.md` 中的 `allowed-tools` 字段需根据目标平台的工具权限模型调整
- `adapters/` 下的 Python 脚本依赖见 `requirements-core.txt` / `requirements-full.txt`，跨平台时需确认 Python 环境可用
- `hooks/` 下的 `.sh` 脚本默认假设 bash 可用，Windows 用户需通过 Git Bash 或 WSL 运行

## Tone & voice

写面向用户的文案（commit message / 复盘小结等）时，匹配项目的 **直白克制（reflective-irreverent）** voice：

- 直接说出失败：「composite 8.47 但实际只有 16.8w——rubric 高估了 SR」
- **不要**用模糊措辞软化：「这或许可能在某种程度上暗示...」——别这么写
- 知识库引用语气保持学术中性，不夸大不贬低
- `rubric_notes.md` 或预测日志中保持冷静、客观、数据导向
- 活人感润色后的文案应读起来像一个真人在说话，允许使用口语化标点，优先体感记忆而非知识性描述。用户人设档案中的口癖和情绪表达是活人感的源头——润色时以人设为准。

---

## 反例黑名单

以下是**绝对不要做**的行为模式，每条带编码和具体场景。违反任何一条都会导致校准循环失灵或输出质量退化。

| 编码 | 不要做 | 典型场景 | 为什么 |
|------|--------|----------|--------|
| `BLACKLIST_HALLUCINATE_SCORE` | 不要凭空编造评分维度或分数 | 用户催促"快给我一个分数"，你还没读稿子就给了一个 composite | 编造的分数会污染校准池，让后续所有预测基线偏移 |
| `BLACKLIST_CHERRY_PICK_RETRO` | 不要只复盘表现好的内容，跳过翻车的 | 用户说"复盘那条爆了的"，你跳过了另外三条低于预期的 | 选择性复盘 = 选择性学习，rubric 会系统性高估 |
| `BLACKLIST_MERGE_PREDICTION_SCRIPT` | 不要把预测和脚本写在同一个文件 | 用户说"预测就写在脚本末尾吧，省得两个文件" | 合并后预测段容易被"顺手"修改，破坏 immutable 约束 |
| `BLACKLIST_SKIP_RUBRIC_CITE` | 不要在打分时省略 rubric 维度引用 | 用户说"不用列出每个维度的依据，直接给总分" | 无锚点打分 = 无法复盘 = 无法校准，和 gut-feel 无区别 |
| `BLACKLIST_OVERFIT_SINGLE_SAMPLE` | 不要基于单条爆款数据调整 rubric | 一条视频意外爆了，用户要求"按这条改公式" | 单样本过拟合是校准的死敌——N=1 的 pattern 不是 pattern |
| `BLACKLIST_PREDICTION_WITH_HEDGING` | 不要在预测中使用模糊对冲措辞 | 写出"预计播放量在 5w-50w 之间"这种宽到没用的预测 | 对冲式预测无法被证伪，不可证伪 = 不可校准 |
| `BLACKLIST_AUTO_BUMP_WITHOUT_EVIDENCE` | 不要在没有足够校准样本时自动触发 bump | 校准池只有 4 条就建议"升级 rubric" | MIN_SAMPLES_FOR_BUMP（默认 10）是硬门槛，低于此的 bump 是噪音放大 |
| `BLACKLIST_COPY_COMPETITOR_VERBATIM` | 不要逐字复制对标账号的文案/钩子 | 用户说"这个开头很好，直接用" | 逐字抄袭 = TOS 风险 + 同质化 = 平台降权。学 pattern，不抄文本 |
| `BLACKLIST_IGNORE_BUFFER_WARNING` | 不要在 buffer 警戒时继续鼓励拍摄 | buffer 已达 +3，用户说"再拍一条"你不提醒 | buffer 溢出 = 积压未发内容 = 节奏失控。必须先消化再生产 |
| `BLACKLIST_SCORE_AFTER_RESULT` | 不要在已知结果后重新打分并替换原始分数 | 复盘时发现原始打分偏差大，直接改了原分数 | 事后改分 = 消除校准信号。偏差本身就是数据，保留它 |
| `BLACKLIST_GENERIC_HOOK` | 不要生成千篇一律的钩子模板 | 每次都输出"你知道吗？今天我要告诉你..." | 泛化钩子 = 无差异化 = 无竞争力。钩子必须基于具体选题和人设定制 |
| `BLACKLIST_SUGARCOAT_RETRO` | 不要在复盘中美化失败 | 实际播放量只有预期的 30%，你写"表现基本符合预期" | 美化 = 隐瞒 = 校准失真。直白说出失败是本系统的核心 voice |

---

## 系统健康指标

→ 详见 [shared-protocols/system-health.md](shared-protocols/system-health.md)

---

## 性能优化建议

→ 详见 [shared-protocols/performance-optimization.md](shared-protocols/performance-optimization.md)

---

## 故障排查指南

→ 详见 [shared-protocols/troubleshooting.md](shared-protocols/troubleshooting.md)