<!-- 作者: 阿洋 -->
<!--
knowledge_index_version: "7.0.0"
author: 阿洋
change_id: refine-yang-skills-knowledge-split-fusion
-->
# 知识库与 Skills 正向联动拓扑图

> **用途**：描述三大知识库拆分后，与 6 个核心子 skill 形成的正向联动拓扑。本文件是 [`Knowledge-Index.md`](./Knowledge-Index.md) 第十五章"知识库与 Skills 的正向联动机制"的详细展开。
> **版本**：7.0.0
> **作者**：阿洋

---

## 一、联动拓扑总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                  知识库 ↔ Skills 正向联动拓扑                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  ansir/ (12文件)  │  │  shekong/ (7文件) │  │  xuehui/ (10文件) │  │
│  │                  │  │                  │  │                  │  │
│  │ hooks.md         │  │ copywriting-     │  │ industry-        │  │
│  │ emotion-system.md│  │   hooks.md       │  │   matrix.md      │  │
│  │ audiovisual.md   │  │ visual-hooks.md  │  │ copywriting-     │  │
│  │ content-methods  │  │ cold-start.md    │  │   scripts.md     │  │
│  │ practice-sop.md  │  │                  │  │ shooting-        │  │
│  │ advanced-insights│  │                  │  │   editing.md     │  │
│  │ industries.md    │  │                  │  │                  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                     │             │
│           ▼                     ▼                     ▼             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              6 条联动通道（正向联动）                          │  │
│  │                                                              │  │
│  │  ① yang-hook-factory    ↔ 钩子体系（3文件）                  │  │
│  │  ② yang-score           ↔ 评分框架（3文件）                  │  │
│  │  ③ yang-polish          ↔ 润色增强（3文件）                  │  │
│  │  ④ yang-emotion-curve   ↔ 情绪曲线（2文件）                  │  │
│  │  ⑤ yang-shoot           ↔ 拍摄登记（2文件）                  │  │
│  │  ⑥ yang-seed            ↔ 选题启动（3文件）                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、联动通道详解

### 通道 1：yang-hook-factory ↔ 钩子体系

| 属性 | 值 |
|------|-----|
| **skill 名称** | yang-hook-factory |
| **引用的知识库文件** | `knowledge/ansir/hooks.md`<br>`knowledge/shekong/copywriting-hooks.md`<br>`knowledge/shekong/visual-hooks.md` |
| **联动方式** | 将 `ansir/hooks.md` 的8种钩子类型理论（悬念/冲突/共鸣/反常识/故事/情绪/利益/身份）与注意力钩子、价值钩子理论，作为钩子生成的**理论框架**；将 `shekong/copywriting-hooks.md` 的28种文案钩子模板（圈定人群/直接提问/自我否定/反认知/高价值展示/直击痛点/损失厌恶/对比对立/头牌借势/警告避坑/吓唬人/内幕揭秘/速成/引发共鸣/极限数字/不同视角/最**/未来趋势/对赌对抗/金钱相关/盘点推荐/跨界组合/送惊喜/荷尔蒙/盲盒/奇葩/负面/具体的事）作为钩子生成的**文案模板库**；将 `shekong/visual-hooks.md` 的8种画面钩子（高情绪/强节奏/凑热闹/沉浸感/反差感/特殊视角/故事感/复古怀旧）作为钩子生成的**画面模板库**。三者组合形成"理论 + 文案模板 + 画面模板"的三层钩子生成体系，使 skill 能生成7种基础钩子 + 5种扩展钩子（人群印记/损失厌恶/挑衅式/新奇有趣/数据背书）共12种钩子变体。 |
| **联动时机** | ① 用户请求生成钩子变体时（触发词：生成钩子/hook factory/钩子变体/前3秒/开头怎么写）<br>② yang-hook-factory 执行 Step 3"七种钩子原型"生成时，加载 `ansir/hooks.md` 扩展5种钩子类型<br>③ yang-hook-factory 执行 Step 4"生成变体矩阵"时，加载 `shekong/copywriting-hooks.md` 和 `shekong/visual-hooks.md` 提供具体模板填充<br>④ 知识库A降级时，钩子类型从8种降级为C的4大类（情绪型/悬念型/利益型/冲突型），此时仅加载 `shekong/` 的2个文件 |

#### 联动数据流

```
ansir/hooks.md ──────────┐
                         ▼
              [8种钩子类型理论 + 扩展5种]
                         │
shekong/copywriting-hooks.md ──┐
                         ▼     │
              [28种文案钩子模板]│
                               │ → yang-hook-factory
shekong/visual-hooks.md ────┐  │
                         ▼  │  │
              [8种画面钩子] │  │
                            └──┴──→ 生成12种钩子变体
```

#### 降级策略

| 降级场景 | 降级行为 |
|---------|---------|
| `ansir/hooks.md` 缺失 | 8种钩子类型详解不可用，扩展5种钩子类型不可用，降级为 `shekong/` 的4大类钩子 |
| `shekong/copywriting-hooks.md` 缺失 | 28种文案钩子模板不可用，钩子变体的具体文案填充降级为通用模板 |
| `shekong/visual-hooks.md` 缺失 | 8种画面钩子不可用，钩子变体的视觉暗示维度降级为通用4类 |
| 三者全部缺失 | 钩子生成完全降级为7种基础钩子原型，无扩展类型，无模板填充 |

---

### 通道 2：yang-score ↔ 评分框架

| 属性 | 值 |
|------|-----|
| **skill 名称** | yang-score |
| **引用的知识库文件** | `knowledge/ansir/practice-sop.md`<br>`knowledge/ansir/advanced-insights.md`<br>`knowledge/xuehui/industry-matrix.md` |
| **联动方式** | 将 `ansir/practice-sop.md` 的评分框架（11项刻意练习作业、核心术语速查表、自查清单、常见误区、创作流程SOP）作为评分的**通用框架基础**，提供评分维度的术语对照和自查标准；将 `ansir/advanced-insights.md` 的进阶洞察（BGM声音设计、从0到1起号流程、进阶问答、To B vs To C策略、心态建设、底层哲学、跨界思维）作为评分的**进阶维度补充**，增强评分锚定的深度；将 `xuehui/industry-matrix.md` 的行业配比矩阵（各行业内容配比矩阵、起号方法全流程、知识点索引）作为评分的**行业基准参考**，使评分能结合具体行业特点给出差异化判断。三者交叉形成"通用评分框架 + 进阶维度 + 行业基准"的三维评分体系。 |
| **联动时机** | ① 用户请求单稿评分时（触发词：打分这篇/score this/评估这篇/评分/评估内容）<br>② yang-score 执行 Step 2"知识检索与评分准备"时，加载3个评分相关子文件<br>③ yang-score 执行 Step 3"调用 Channel B 执行 3-Judge 评分"时，3个文件的内容作为评分锚定的参考知识<br>④ 知识库A降级时，`practice-sop.md` 和 `advanced-insights.md` 不可用，评分锚定降级为B/C混合 |

#### 联动数据流

```
ansir/practice-sop.md ─────┐
                           ▼
              [通用评分框架 + 自查清单]
                           │
ansir/advanced-insights.md ┐
                           ▼ │
              [进阶洞察 + BGM设计]│
                             │ → yang-score
xuehui/industry-matrix.md ─┐ │
                           ▼ │ │
              [行业配比矩阵]  │ │
                             └─┴──→ 7维评分 + 行业基准
```

#### 降级策略

| 降级场景 | 降级行为 |
|---------|---------|
| `ansir/practice-sop.md` 缺失 | 通用评分框架不可用，评分锚定降级为B的八大爆款元素和C的开篇36计 |
| `ansir/advanced-insights.md` 缺失 | 进阶维度补充不可用，评分深度降低，标注"进阶维度降级" |
| `xuehui/industry-matrix.md` 缺失 | 行业基准参考不可用，评分无法结合行业特点，标注"行业基准降级" |
| 三者全部缺失 | 评分完全依赖 rubric_notes.md 自身规则，无知识库增强 |

---

### 通道 3：yang-polish ↔ 润色增强

| 属性 | 值 |
|------|-----|
| **skill 名称** | yang-polish |
| **引用的知识库文件** | `knowledge/ansir/content-methods.md`<br>`knowledge/shekong/copywriting-hooks.md`<br>`knowledge/xuehui/copywriting-scripts.md` |
| **联动方式** | 将 `ansir/content-methods.md` 的内容方法论（普世×陌生×情绪三维模型、刻意练习、对标拆解、漏斗模型、账号五期策略）作为润色的**方法论基础**，指导L3内容质量检查中的观点支撑和知识输出方式；将 `shekong/copywriting-hooks.md` 的28种文案钩子模板作为润色的**钩子话术库**，在开头优化（hook < 6时重写开头）阶段提供具体的钩子话术参考；将 `xuehui/copywriting-scripts.md` 的文案写作体系（文案三要素、四大脚本类型总览、观点型脚本选题公式）作为润色的**文案技巧库**，增强L2风格一致性检查中的口语化节奏和金句密度判断。三者融合形成"方法论 + 钩子话术 + 文案技巧"的润色增强体系。 |
| **联动时机** | ① 用户请求活人感润色时（触发词：润色/polish/去AI味/活人感润色/帮我改一下/太AI了）<br>② yang-polish 执行 Step 4"执行润色"时，加载3个润色相关子文件<br>③ yang-polish 执行 Step 5"四层自检"中的L2（风格一致性）和L3（内容质量）时，引用3个文件的内容<br>④ 当诊断报告中 hook < 4 时，从 `shekong/copywriting-hooks.md` 选取合适的钩子模板重写开头 |

#### 联动数据流

```
ansir/content-methods.md ──┐
                            ▼
              [内容方法论 + 三维模型]
                            │
shekong/copywriting-hooks.md┐
                            ▼ │
              [28种文案钩子模板]│
                              │ → yang-polish
xuehui/copywriting-scripts.md┐│
                            ▼ ││
              [文案写作体系]   ││
                              └┴──→ L2/L3 自检增强
```

#### 降级策略

| 降级场景 | 降级行为 |
|---------|---------|
| `ansir/content-methods.md` 缺失 | 内容方法论不可用，L3内容质量检查降级为通用规则 |
| `shekong/copywriting-hooks.md` 缺失 | 钩子话术库不可用，开头优化降级为4种必杀技通用模板 |
| `xuehui/copywriting-scripts.md` 缺失 | 文案技巧库不可用，L2风格一致性检查的口语化判断降级为通用规则 |
| 三者全部缺失 | 润色完全依赖人设档案和通用活人感规则，无知识库增强 |

---

### 通道 4：yang-emotion-curve ↔ 情绪曲线

| 属性 | 值 |
|------|-----|
| **skill 名称** | yang-emotion-curve |
| **引用的知识库文件** | `knowledge/ansir/emotion-system.md`<br>`knowledge/ansir/advanced-insights.md` |
| **联动方式** | 将 `ansir/emotion-system.md` 的情绪刺点理论（骨架六种推进方式、情绪刺点理论、点赞/评论/收藏/分享/关注五大刺点）作为情绪曲线分析的**核心理论框架**，指导Step 3情绪标注和Step 5节奏分析中的情绪密度、动态范围、峰值位置判断；将 `ansir/advanced-insights.md` 的BGM声音设计、进阶问答、To B vs To C策略作为情绪曲线分析的**进阶应用补充**，增强情绪曲线与BGM节奏的协同分析能力。两者组合形成"刺点理论 + 声音设计 + 进阶应用"的情绪分析体系。 |
| **联动时机** | ① 用户请求情绪曲线分析时（触发词：情绪曲线/emotion curve/分析节奏/情绪分析/节奏设计）<br>② yang-emotion-curve 执行 Step 3"情绪标注"时，加载 `emotion-system.md` 的五大刺点理论指导标注<br>③ yang-emotion-curve 执行 Step 5"节奏分析"时，加载 `advanced-insights.md` 的BGM声音设计增强节奏分析<br>④ 知识库A降级时，情绪刺点理论不可用，降级为通用ER-Curve框架（正负唤醒度7级标注） |

#### 联动数据流

```
ansir/emotion-system.md ───┐
                            ▼
              [情绪刺点理论 + 五大刺点]
                            │
                            │ → yang-emotion-curve
                            │
ansir/advanced-insights.md ┐
                            ▼ │
              [BGM设计 + 进阶问答]│
                              └──→ ER-Curve + 节奏分析增强
```

#### 降级策略

| 降级场景 | 降级行为 |
|---------|---------|
| `ansir/emotion-system.md` 缺失 | 情绪刺点理论不可用，五大互动词典不可用，降级为通用ER-Curve框架 |
| `ansir/advanced-insights.md` 缺失 | BGM声音设计不可用，情绪曲线与BGM的协同分析降级为通用节奏判断 |
| 两者全部缺失 | 情绪曲线分析完全依赖通用ER-Curve框架，标注"A-占位（通用ER-Curve替代）" |

---

### 通道 5：yang-shoot ↔ 拍摄登记

| 属性 | 值 |
|------|-----|
| **skill 名称** | yang-shoot |
| **引用的知识库文件** | `knowledge/ansir/audiovisual.md`<br>`knowledge/xuehui/shooting-editing.md` |
| **联动方式** | 将 `ansir/audiovisual.md` 的导演级视听语言系统（四层结构、叙事层六要素、空间架构、时间控制、时间的语法、摄影机七种运动、影像八体、行动日历）作为拍摄登记的**视听语言理论指导**，在改稿检测时辅助判断脚本中的视听元素是否在拍摄中得到保留；将 `xuehui/shooting-editing.md` 的拍摄及呈现体系（运镜7种、景别、构图、六种打光、剪辑五步骤）作为拍摄登记的**拍摄剪辑实操指导**，在v2重判触发时辅助判断改稿是否影响了拍摄可行性。两者组合形成"视听语言理论 + 拍摄剪辑实操"的拍摄指导体系。 |
| **联动时机** | ① 用户登记拍摄完成时（触发词：拍了/shot/已拍/录完了/拍摄完成/拍好了）<br>② yang-shoot 执行 Phase 2"建 video folder + 询问稿子一致性"时，加载2个视听相关子文件<br>③ yang-shoot 执行 Phase 3"写 videos/<id>/script.md + 触发v2预测"时，引用2个文件的内容辅助判断改稿是否影响视听元素<br>④ 当 diff ≥ 30% 触发 v2 重判时，引用 `audiovisual.md` 和 `shooting-editing.md` 辅助判断改稿对拍摄的影响 |

#### 联动数据流

```
ansir/audiovisual.md ──────┐
                            ▼
              [导演级视听语言 + 七种运动]
                            │
                            │ → yang-shoot
                            │
xuehui/shooting-editing.md ┐
                            ▼ │
              [拍摄剪辑体系 + 运镜/打光]│
                              └──→ 改稿检测 + v2重判辅助
```

#### 降级策略

| 降级场景 | 降级行为 |
|---------|---------|
| `ansir/audiovisual.md` 缺失 | 导演级视听语言不可用，改稿检测中的视听元素判断降级为通用规则 |
| `xuehui/shooting-editing.md` 缺失 | 拍摄剪辑实操指导不可用，v2重判的拍摄可行性判断降级为通用规则 |
| 两者全部缺失 | 拍摄登记完全依赖脚本diff计算，无视听语言增强 |

---

### 通道 6：yang-seed ↔ 选题启动

| 属性 | 值 |
|------|-----|
| **skill 名称** | yang-seed |
| **引用的知识库文件** | `knowledge/ansir/industries.md`<br>`knowledge/shekong/cold-start.md`<br>`knowledge/xuehui/industry-matrix.md` |
| **联动方式** | 将 `ansir/industries.md` 的30行业爆款分析（30个行业爆款视频拆解分析、核心方法论提炼）作为选题启动的**行业案例库**，在Channel A（Rubric导向选题）和Channel B（对标拉升选题）中提供行业爆款参考；将 `shekong/cold-start.md` 的冷启动策略（反向操作、扮猪吃老虎、以物换物、借物喻人、跨界组合、赛道叠加、一句话故事感、加人物关系、一饰多角、情境还原）作为选题启动的**冷启动策略库**，在Channel C（热点冲浪选题）和Channel D（高赞评论金句选题）中提供冷启动角度参考；将 `xuehui/industry-matrix.md` 的行业配比矩阵（各行业内容配比矩阵、起号方法全流程、知识点索引）作为选题启动的**行业配比参考**，在选题分级时结合行业特点给出差异化判断。三者组合形成"行业案例 + 冷启动策略 + 行业配比"的选题生成体系。 |
| **联动时机** | ① 用户请求冷启动选题时（触发词：找选题/我不知道拍什么/seed/下一期拍什么/选题推荐）<br>② yang-seed 执行 Channel A"Rubric导向选题"时，加载 `industries.md` 提供行业爆款参考<br>③ yang-seed 执行 Channel B"对标拉升选题"时，加载 `industry-matrix.md` 提供行业配比参考<br>④ yang-seed 执行 Channel C/D"热点冲浪/高赞评论金句选题"时，加载 `cold-start.md` 提供冷启动角度参考<br>⑤ 知识库A降级时，`industries.md` 不可用，选题的行业案例参考降级为B/C的通用框架 |

#### 联动数据流

```
ansir/industries.md ───────┐
                            ▼
              [30行业爆款分析]
                            │
shekong/cold-start.md ─────┐│
                            ▼ │
              [10种冷启动策略]│
                              │ → yang-seed
xuehui/industry-matrix.md ──┐│
                            ▼ ││
              [行业配比矩阵]  ││
                              └┴──→ 五通道选题增强
```

#### 降级策略

| 降级场景 | 降级行为 |
|---------|---------|
| `ansir/industries.md` 缺失 | 30行业爆款分析不可用，Channel A/B的行业案例参考降级为通用选题框架 |
| `shekong/cold-start.md` 缺失 | 10种冷启动策略不可用，Channel C/D的冷启动角度参考降级为通用热点/评论分析 |
| `xuehui/industry-matrix.md` 缺失 | 行业配比矩阵不可用，选题分级无法结合行业特点，标注"行业配比降级" |
| 三者全部缺失 | 选题启动完全依赖五通道自身逻辑，无知识库增强 |

---

## 三、联动通道汇总表

| # | 联动通道 | skill | 引用子文件数 | 联动时机 | 降级策略 |
|---|---------|-------|------------|---------|---------|
| 1 | 钩子工厂联动 | yang-hook-factory | 3 | 生成钩子变体时 | A降级→C的4大类钩子 |
| 2 | 评分框架联动 | yang-score | 3 | 单稿评分时 | A降级→B/C混合锚定 |
| 3 | 润色增强联动 | yang-polish | 3 | 活人感润色时 | A降级→通用活人感规则 |
| 4 | 情绪曲线联动 | yang-emotion-curve | 2 | 情绪曲线分析时 | A降级→通用ER-Curve |
| 5 | 拍摄登记联动 | yang-shoot | 2 | 拍摄登记与改稿检测时 | A/B降级→通用diff计算 |
| 6 | 选题启动联动 | yang-seed | 3 | 冷启动选题时 | A降级→B/C通用框架 |

---

## 四、联动机制维护规则

### 4.1 新增联动通道

1. 在本文件第二章新增"通道 N"小节，描述 skill 名称、引用子文件、联动方式、联动时机、降级策略
2. 在 [`Knowledge-Index.md`](./Knowledge-Index.md) 第十五章 15.2 速查表新增行
3. 在对应子 skill 的 SKILL.md 新增"知识库联动"章节
4. 更新本文件第三章汇总表

### 4.2 更新联动路径

当知识库子文件重命名/拆分/合并时：

1. 更新本文件第二章对应通道的"引用的知识库文件"
2. 更新 [`Knowledge-Index.md`](./Knowledge-Index.md) 第十五章 15.2 速查表
3. 更新对应子 skill 的"知识库联动"章节
4. 更新本文件第三章汇总表

### 4.3 移除联动通道

当某子 skill 不再依赖某知识库子文件时：

1. 从本文件第二章移除对应通道小节
2. 从 [`Knowledge-Index.md`](./Knowledge-Index.md) 第十五章 15.2 速查表移除对应行
3. 从对应子 skill 的"知识库联动"章节移除对应引用
4. 更新本文件第三章汇总表

### 4.4 联动完整性校验

yang-doctor 诊断时，应校验以下联动完整性规则：

| 校验项 | 规则 | 不通过时的动作 |
|-------|------|-------------|
| 联动子文件存在性 | 6条联动通道引用的所有子文件均存在 | 报告"联动子文件缺失"并列出缺失文件 |
| 联动章节存在性 | 6个子skill的SKILL.md中均存在"知识库联动"章节 | 报告"联动章节缺失"并列出缺失的skill |
| 联动路径正确性 | 联动章节中引用的子文件路径与本文件一致 | 报告"联动路径不一致" |
| 联动通道完整性 | 本文件第二章的6条通道与 [`Knowledge-Index.md`](./Knowledge-Index.md) 第十五章 15.2 速查表一致 | 报告"联动通道不一致" |

---

## 五、版本记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 7.0.0 | 2026-06-20 | 初始创建。描述6条联动通道：yang-hook-factory、yang-score、yang-polish、yang-emotion-curve、yang-shoot、yang-seed 与三大知识库拆分后子文件的正向联动拓扑。 | 阿洋 |

---

> **作者**：阿洋
> **版本**：7.0.0
> **关联文件**：[`Knowledge-Index.md`](./Knowledge-Index.md) 第十五章"知识库与 Skills 的正向联动机制"
