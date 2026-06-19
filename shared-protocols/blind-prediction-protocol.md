<!-- 作者: 阿洋 -->
# Blind Prediction Protocol（盲预测协议）

被这些子 skill 引用：`yang-predict`、`yang-retro`、主 SKILL.md。

这是项目原则 #1 的完整规范。任何子 skill 在写预测前都必须执行本协议。

---

## 核心定义

**盲预测**：在预测者（人或模型）看到任何关于该作品发布后真实表现数据**之前**完成的预测。

预测一旦写入 `predictions/*.md` 的 `## 预测` 段，该段即为 **immutable**——只能在文件末尾追加 `## 复盘` 段，不能修改预测段任何字符。

---

## "见过数据"的边界（关键，常被违反）

下列任一条件成立 → 已不再 blind，**禁止写预测**：

| 信息 | 是否破坏 blind | 例外 |
|---|---|---|
| 该作品任何平台的播放数 / 阅读数 | ✗ 破坏 | 无 |
| 该作品的点赞 / 评论 / 转发数 | ✗ 破坏 | 无 |
| 该作品的具体评论内容 | ✗ 破坏 | 无 |
| 该作品的算法推荐位 / 热门榜位置 | ✗ 破坏 | 无 |
| 该作品发布后的截图 / 后台数据 | ✗ 破坏 | 无 |
| **同期发布的其他人**作品的表现 | ○ 不破坏 | — |
| **历史上类似主题**作品的表现 | ○ 不破坏（这正是锚点对比要做的） | — |
| 该作品**发布前**的稿子内容 | ○ 不破坏 | 这是预测的输入 |
| 用户口述的"我感觉这条还行" | △ 谨慎 | 用户的主观感觉不算"数据"，但要在预测里标注用户偏见 |

**判断捷径**：只要这条信息**只能在作品发布后才能获得**，就算"数据"。

---

## 预测者必须主动声明的情况

子 skill 在启动 `yang-predict` 前，必须自检并向用户**主动声明**：

1. **作品已发布超过 RETRO_WINDOW_DAYS 天**（默认 3 天）→ 必须拒绝写"预测"，改记为 `**Reconstructed retrospective**`，明确标注非预测
2. **作品已发布但 < RETRO_WINDOW_DAYS 天，用户尚未透露任何数据**→ 允许 blind 预测，但在文件头部标记 `published_before_prediction: true` + `blind_status: confirmed_no_data_seen`
3. **用户在对话里已粘贴了任何后续数据**→ 同 #1 处理，记为 reconstructed

`BLIND_CHECK=strict`（默认）：上述任何破坏条件命中，**拒绝执行**。
`BLIND_CHECK=lenient`：仅警告 + 强制标注，允许继续——只用于离线测试或学术演练，**不推荐用于真实校准**。

---

## Immutable 的工程边界

`## 预测` 段的不可修改是**用户体验承诺**，由 hook 层强制：

- `hooks/prediction-immutability.sh` 在 PreToolUse(Edit|Write) 上检查 `predictions/` 下文件
- 命中 `## 预测` 与下一个二级标题之间任何 diff → exit 1 阻塞
- `## 复盘` 段的追加 → 放行

**禁止的"绕开"模式**（子 skill 必须拒绝）：
- "把预测段重写得更准一点" → 拒绝。如有正当理由重做，创建新文件 `<原文件名>_redo.md`，原文件保留
- "我的概率分布写错了 0.5%，让我改一下" → 拒绝。在复盘段追加 `修正：原概率分布 X% 应为 Y%，于 <date> 发现笔误`
- "我前面没考虑 SR=4，重打一下分" → 拒绝。同上路径

唯一允许编辑预测段的场景：**纯 markdown 排版错误**（标题层级错误、列表 bullet 格式错），且用户明确说明这是格式修复。这种情况 hook 仍会阻塞，需要用户显式 bypass（手动设置环境变量 `CHEAT_BYPASS_IMMUTABILITY=1` 单次）——bypass 应在 git history 留痕。

---

## 文件名约定（**三处一致**）

一个内容三处文件，**用同一组 `<date>_<id>_<short>` 命名**：

```
scripts/<date>_<id>_<short>.md        ← pre-shoot 草稿（yang-seed 写或用户写）
predictions/<date>_<id>_<short>.md    ← immutable 预测（yang-predict 写）
videos/<date>_<id>_<short>/           ← 拍后才建（yang-shoot 创建）
  ├── script.md                       ← 用户提供的最终拍摄稿
  └── report.md                       ← T+3d 数据（yang-retro 写）
```

- `<date>`：**草稿首次落盘日期**（即 `scripts/<id>.md` 的创建日），不是预测日 / 拍摄日 / 发布日。理由：保持 ID 稳定——草稿大改后 hash 变了仍想保持文件可追溯
- `<id>`：12 位 sha256 前缀，对**草稿首次落盘的内容**做 hash。用户 edit 草稿后**不变**——便于跨文件引用
- `<short>`：3-8 字中文或英文短名，便于人类辨识

Reconstructed 重做：在 `<short>` 后加 `_redo`，三处都加：
- `scripts/<date>_<id>_<short>_redo.md`
- `predictions/<date>_<id>_<short>_redo.md`
- `videos/<date>_<id>_<short>_redo/`

原文件保留（不删）。

---

## 子 skill 必须做的检查清单

`yang-predict` 启动时：
1. 读 `BLIND_CHECK` 常量
2. 询问用户该作品当前发布状态（未发 / 已发 < RETRO_WINDOW_DAYS / 已发 ≥ RETRO_WINDOW_DAYS）
3. 询问对话历史里是否提到过该作品的任何后续数据（如有，自检对话里有没有 "播放/阅读/点赞/评论" 等关键词）
4. 若 #2 或 #3 命中破坏条件 → 按 `BLIND_CHECK` 模式处理
5. 通过后才允许写 `predictions/*.md`

`yang-retro` 启动时：
1. 读目标 prediction 文件
2. **先在内存里 cache 住 `## 预测` 段**——后续任何对该文件的写都必须先校验该段未变
3. 抓数据 → 追加 `## 复盘` 段
4. 写完后**再次校验**：写入后该文件的 `## 预测` 段哈希应等于步骤 2 的 cache。不等 → 报错并回滚

主 SKILL.md：
- 用户说出"重写预测" / "改一下预测段" / "你之前预测错了我帮你改" 时，**直接拒绝并解释**，引导改用 `_redo.md` 路径

---

## 异常状态处理

| 场景 | 处理 |
|---|---|
| 预测文件不小心被人手编辑了预测段 | 不自动回滚（破坏更大）。下次 `yang-retro` 检测到不一致 → 在复盘段追加 `**Integrity warning**: 预测段于 <ISO timestamp> 被外部修改，无法保证盲度`，校准价值降级为"参考"，不计入 bump 校准池 |
| 预测文件遗失 / 被删 | git log 找回。找不到 → 在 `rubric_notes.md` 记录"<id> 预测文件遗失，校准池缺该样本" |
| 用户原本是 cold-start，半路想"补"已发作品的预测 | 一律记为 `**Reconstructed retrospective**`，不计入校准池——这是补的不是预测。可作为"观察"记录到 `rubric_notes.md` |

---

## 反模式（必须拒绝的请求）

- 「帮我预测一下，但我先告诉你播放量你来反推就行」 → 拒绝。直接破坏盲度
- 「这条已经发了 5 天数据出来了，但你假装没看到，给我做个预测看会不会准」 → 拒绝。请改用 `_redo.md` 走 reconstructed 路径
- 「上次预测算错了，帮我把概率分布改一下」 → 拒绝。在复盘段说明
- 「能不能跳过 blind check 我有特殊原因」 → 询问原因；只有"格式修复"是合法的 bypass 理由

---

## 执行检查清单（5 项必检）

`yang-predict` 启动时，必须逐项通过以下 5 项检查。任何一项未通过，预测流程**立即阻断**。

| # | 检查项 | 通过条件 | 未通过处理 |
|---|--------|----------|------------|
| 1 | **发布状态确认** | 用户已明确声明作品当前状态（未发 / 已发 < RETRO_WINDOW_DAYS / 已发 ≥ RETRO_WINDOW_DAYS） | 阻断，要求用户确认发布状态 |
| 2 | **数据盲度验证** | 对话历史中无该作品的任何发布后数据（播放/阅读/点赞/评论/推荐位/后台截图） | 按 `BLIND_CHECK` 模式处理：strict→拒绝；lenient→警告+强制标注 |
| 3 | **预测文件唯一性** | `predictions/` 下不存在同 id 的预测文件（防止重复预测覆盖） | 阻断，提示已有预测文件，引导走 `_redo.md` 路径 |
| 4 | **脚本文件存在性** | 对应 `scripts/<id>.md` 文件存在且非空 | 阻断，提示先写脚本或提供脚本路径 |
| 5 | **rubric 就绪** | `rubric_notes.md` 存在且包含至少 1 个评分维度定义 | 阻断，提示先跑 `/yang-learn-from` 建立锚点 |

检查通过后，在预测文件头部写入确认标记：

```yaml
blind_check:
  publish_status: "未发" | "已发<N天" | "已发≥RETRO_WINDOW_DAYS"
  data_leakage: false
  file_uniqueness: true
  script_exists: true
  rubric_ready: true
  check_timestamp: "YYYY-MM-DDTHH:mm:ssZ"
```

---

## 违规自动检测规则

以下规则由 hook 层和子 skill 运行时联合执行，**无需人工触发**。

### 规则 1：预测段不可变检测

- **触发**：`hooks/prediction-immutability.sh` 在 `PreToolUse(Edit|Write)` 事件上拦截
- **检测逻辑**：对 `predictions/` 下文件的 `## 预测` 段（从 `## 预测` 到下一个 `##` 二级标题之间）计算 SHA256
- **判定**：diff 命中预测段任何字符 → `exit 1` 阻塞
- **例外**：`## 复盘` 段的追加 → 放行；纯 markdown 排版修复需 `CHEAT_BYPASS_IMMUTABILITY=1`

### 规则 2：事后预测检测

- **触发**：`yang-predict` 启动时
- **检测逻辑**：检查用户声明的发布状态 + 对话历史关键词扫描（播放/阅读/点赞/评论/推荐/热搜/后台/数据）
- **判定**：已发 ≥ RETRO_WINDOW_DAYS → 拒绝写预测，改记 `Reconstructed retrospective`
- **判定**：对话中出现该作品发布后数据关键词 → 按 `BLIND_CHECK` 模式处理

### 规则 3：复盘段完整性校验

- **触发**：`yang-retro` 写入复盘段后
- **检测逻辑**：写入后重新读取文件，对 `## 预测` 段计算 SHA256，与写入前 cache 比对
- **判定**：哈希不一致 → 报错并回滚写入操作
- **恢复**：从 git 恢复文件到写入前状态，在 `rubric_notes.md` 记录 integrity warning

### 规则 4：预测文件命名一致性检测

- **触发**：`yang-shoot` / `yang-publish` / `yang-retro` 引用预测文件时
- **检测逻辑**：检查 `scripts/`、`predictions/`、`videos/` 三处文件名中 `<date>_<id>_<short>` 部分一致
- **判定**：不一致 → 警告并要求用户确认关联关系

### 规则 5：校准池样本盲度标记检测

- **触发**：`yang-bump` 计算校准池时
- **检测逻辑**：遍历校准池所有样本，检查预测文件头部 `blind_check` 标记
- **判定**：`data_leakage: true` 或 `publish_status: "已发≥RETRO_WINDOW_DAYS"` 的样本 → 从 bump 校准池排除，降级为"参考"

---

## 预测文件格式规范

### 必填字段

以下字段**必须**出现在每个预测文件中，缺失则 `yang-predict` 拒绝写入。

```markdown
---
# YAML frontmatter（必填）
id: "<date>_<id>_<short>"           # 与 scripts/ 同 ID
created_at: "YYYY-MM-DD"            # 预测写入日期
blind_check:                        # 执行检查清单结果
  publish_status: "未发"
  data_leakage: false
  file_uniqueness: true
  script_exists: true
  rubric_ready: true
  check_timestamp: "YYYY-MM-DDTHH:mm:ssZ"
---

## 预测

### 评分快照
- composite: <float>                # 综合评分
- 各维度评分: <dimension>: <score>  # 每个维度及分数

### 核心预测
- 预计播放量: <具体数值或窄区间>     # 禁止"5w-50w"式宽对冲
- 预计互动率: <百分比>               # (点赞+评论+转发)/播放
- 置信度: <高/中/低>                 # 基于锚点对比的信心水平

### 预测依据
- 锚点对比: [与哪条历史内容对比，差异在哪]
- 关键假设: [列出 2-3 个核心假设]

### 风险因素
- [列出可能导致预测偏差的因素]
```

### 可选字段

以下字段视情况添加，不强制要求。

```markdown
### 概率分布（可选）
- P(播放量 > X): <百分比>
- P(互动率 > Y): <百分比>

### 用户偏见标注（可选）
- 用户主观预期: <用户口述的预期>
- 偏见方向: <高估/低估/中性>

### 选题关联（可选）
- candidate_id: <关联的候选选题 ID>
- 选题来源: <seed/trends/manual>

### 实验性标注（可选）
- is_experimental: true             # 标记为实验性内容
- hypothesis_tested: <验证的假设>    # 实验性内容验证的假设
```

### 格式红线

| 规则 | 说明 | 违反处理 |
|------|------|----------|
| 预测区间宽度 ≤ 3× | 预计播放量区间上限不超过下限的 3 倍 | 阻断，要求缩窄区间 |
| 禁止模糊对冲 | 不得使用"可能""或许""大概"等不确定性措辞替代具体数值 | 阻断，要求给出具体数值 |
| 必须有锚点对比 | 预测依据中至少引用 1 条历史锚点 | 阻断，提示先建立锚点 |
| composite 必须与评分一致 | 预测文件中的 composite 必须等于 `/yang-score` 的输出 | 警告，提示确认评分来源 |

---

## Why（为什么这套这么严）

盲预测是整个 Yang.skills 校准循环的**唯一信号源**。一旦预测段被事后修改，所有"哪个维度被验证 / 推翻"的判断都失去基线——你不知道当初是真预测对了，还是事后改对了。

校准价值 = 预测精度 × 预测可信度。
- 预测精度可以靠 rubric 升级慢慢提升。
- 预测可信度一旦破坏不可恢复——**这是为什么 immutability 是 hook 层强制，不是君子协定**。
