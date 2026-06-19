<!-- 作者: 阿洋 -->
# Cadence Protocol（节奏协议）

被这些子 skill 引用：`yang-status`、`yang-recommend`、`yang-shoot`、`yang-publish`、SessionStart hook。

固化"哪天该做什么"——避免用户驱动每一步。让 Claude 在会话开场就能回答"我现在该拍 / 该发 / 该复盘"。

---

## 三层节奏

### 日级（每天 / 每次会话开场）

1. SessionStart hook 自动渲染 4-6 行报告：
   - 📦 Buffer 状态（颜色 + 数量）
   - ⏰ 待复盘到期项
   - 🎯 候选池 top 3（粗排）
   - 📅 上次抓热点时间
   - ⚠️ 关键 to-do
2. 不主动开始任何动作——等用户决定

### 事件级（T+`RETRO_WINDOW_DAYS` 天到期）

- 任何已发未复盘 + 时间到 → SessionStart 顶部高亮
- 用户给数据（粘 / URL）→ `/yang-retro` 自动跑

### 周级（用户决定的"集中处理日"）

- 抓热点（`/yang-trends`）刷新候选池
- 检查 rubric bump 触发条件
- 清理 STATUS.md / rubric_notes.md 是否需要清算

---

## Buffer 警戒规则

**Buffer = `state.shoots` 数组长度** = 已拍但未发布的视频数。

`/yang-shoot` 把视频加进 `state.shoots`，`/yang-publish` 移除——两个事件分开使 buffer 跟踪准确。

### 颜色阈值（按 `target_publish_cadence_days` 派生）

`buffer_days = buffer_count × target_publish_cadence_days`

| buffer_days | 颜色 | 含义 | 行动 |
|---|---|---|---|
| < 1 | 🔴 **红** | 警戒——下个发布日可能断更 | **今天必须拍**，且只拍稳分（top 1，不冒险） |
| 1-2 | 🟠 橙 | 偏低 | 应该拍 1-2 条 |
| 3-5 | 🟢 绿 | 正常 | 节奏稳定，可以拍可以休 |
| > 5 | 🔵 蓝 | 积压 | **暂停拍摄**，全力发布存货 + 复盘 |

**示例**：
- 用户 cadence = 1（日更），buffer count = 0 → buffer_days = 0 → 🔴
- 用户 cadence = 7（周更），buffer count = 1 → buffer_days = 7 → 🔵（一篇够发七天）
- 用户 cadence = 1，buffer count = 4 → buffer_days = 4 → 🟢

### 灵活节奏（target_publish_cadence_days = null）

用户在 yang-init 选"灵活/不固定" → buffer 监控**关闭**。SessionStart 报告只显示"已拍未发：N 条"，不显示颜色，不警戒。

---

## 选题策略（`/yang-recommend` 推 ≥ 2 个时）

每次推荐 2 条时遵循 **1 稳分 + 1 实验性** 原则：

### 第 1 条（稳分）

- 排序 top 1-3
- 类目与最近 N 条已发**不重复**（N = max(3, target_publish_cadence_days × 3)，避免审美疲劳）
- composite 高 + 议题安全（非 risky）

### 第 2 条（实验性）

- 候选池里能验证某个**待验证假设**的样本（如新维度的 A/B 对照）
- 或验证某个**新 pattern**（[script_patterns.md](script_patterns.md) 的 Pattern N）
- composite 不一定 top，但有"信息价值"——复盘后能让 rubric / pattern 库前进

### Buffer 颜色对推荐的覆盖

| Buffer 颜色 | 推荐策略覆盖 |
|---|---|
| 🔴 红 | **只推稳分 top 1**——不推实验性。"今天能拍出来就行" |
| 🟠 橙 | 1 稳 + 1 实验，但建议优先拍稳分 |
| 🟢 绿 | 标准 1+1 |
| 🔵 蓝 | **暂停推荐**——回 "你 buffer 积压了，先发存货 + 复盘" |

**关键约束**（任何颜色都遵守）：
- 同一 category 连发 ≤ 2 条
- 已发过的 candidate（标 done）不推
- 用户主动跳过的 candidate（标 skip）6 个月内不推

---

## 节奏元规则

按优先级（高→低）：

1. **Buffer 优先于评分**：红色警戒时不要因为"等更好的选题"而断更——拍 composite 7.5 的稳分比"等明天的 9.0"安全
2. **复盘优先于新拍**：T+RETRO_WINDOW_DAYS 到期当天**先复盘再考虑拍新的**——否则数据信号丢失，rubric 校准受损
3. **同步优先于积压**：buffer 满（蓝色）时不要再拍，先发掉再说——已拍议题的时效性会衰减
4. **实验性最多 1/天**：每天拍 2 条时至少 1 条是稳分。**不要全实验**——冷启动期实验失败率太高，伤校准节奏

---

## 标准化"今日工作流"模板

### 情况 1：buffer 充足 + 没到 T+3d 复盘

```
SessionStart 报告 → user 决定拍/不拍
├─ 拍 → "推荐选题" → yang-recommend 推 2 个 →
│       user 选 → /yang-seed 写 draft (cold-start) 或 user 自己写 →
│       user 改写 → script.md → user 拍 → "拍了 videos/<...>/" → yang-shoot
└─ 不拍 → 等
```

### 情况 2：buffer 充足 + 到 T+3d 复盘

```
SessionStart 报告含 ⏰ 复盘提醒 → user 给 video URL 或粘数据 →
yang-retro 自动跑 → 写复盘段 → 检查 bump 触发条件
├─ 触发 → 提议 /yang-bump（不强制，用户决定）
└─ 未触发 → 等下个验证样本
```

### 情况 3：buffer 红色警戒

```
🔴 SessionStart 第一行警戒 → user 决定
├─ 拍 → yang-recommend 只推 v 当前 top 1 稳分 → 立即拍
└─ 接受断更风险 → user 自负，yang-status 持续提示
```

### 情况 4：buffer 蓝色积压

```
🔵 SessionStart 报告"积压" → user 决定
├─ 发 → "已发布 https://..." → yang-publish → buffer -1
├─ 复盘 → 见情况 2
└─ 拍新 → yang-recommend 拒绝："你 buffer 已 N 条，先发掉 ≤3 条再来"
```

### 情况 5：周期性集中处理日（用户主动触发）

```
user 说"抓热点" → yang-trends → 候选池更新
+ user 说"看看 rubric 是不是该升了" → yang-status 检查同向偏差累计
+ user 说"看看 rubric_notes 行数" → yang-status 健康度检查
```

---

## 兜底：流程偏离时

如果某天违反节奏（buffer=0 但用户强行不拍 / 积压 ≥10 但用户继续拍），SessionStart 报告**显式标注**：

```
❌ 你已 N 天没发新内容（最后一次发布：YYYY-MM-DD），
   buffer = 0，你的频道目前处于"事实断更"状态
```

或：

```
❌ 你 buffer 已 N 条但还在新拍，
   过去 N 条里有 N 条已超过 X 天未发——存在时效性流失风险
```

**不会自动尝试补救**——只显式报告，由 user 决定如何回到节奏。

---

## 子 skill 责任表

| Skill | 节奏责任 |
|---|---|
| `/yang-init` | 问 cadence；写 `target_publish_cadence_days`；装 SessionStart hook |
| `/yang-shoot` | 把 video folder 加 state.shoots，buffer +1 |
| `/yang-publish` | 从 state.shoots 移除对应项，buffer -1 |
| `/yang-status` | 计算 buffer + 颜色，输出报告 |
| `/yang-recommend` | 按 buffer 颜色 + 选题策略给推荐 |
| `/yang-retro` | 复盘后更新 STATUS（自动 trigger /yang-status） |
| SessionStart hook | 调 /yang-status 渲染 4-6 行报告，写到 STATUS.md |

---

## 关键差异：Yang.skills vs 视频分析

| 维度 | 视频分析 | Yang.skills |
|---|---|---|
| Cadence 来源 | 默认日更（CADENCE.md 硬编码） | 用户自填（yang-init 问，4 档：日/隔日/周/灵活） |
| Buffer 阈值 | 0/1/2/3-5/6+（按"篇"）| 0/1-2/3-5/>5（按"buffer_days"——按用户 cadence 派生） |
| 推荐 2 条策略 | 1 稳 + 1 实验 | 同 |
| SessionStart 报告 | CLAUDE.md 文字约束 + Claude 自觉 | hook 强制 + Claude 读 hook 输出 |

---

## Buffer 警戒线具体阈值与触发动作

### 阈值定义

`buffer_days = buffer_count × target_publish_cadence_days`

| 颜色 | buffer_days 范围 | buffer_count 示例（日更 cadence=1） | buffer_count 示例（周更 cadence=7） | 含义 |
|------|------------------|--------------------------------------|--------------------------------------|------|
| 🔴 红 | buffer_days < 1 | count = 0 | count = 0 | 断更风险——下个发布日无内容可发 |
| 🟠 橙 | 1 ≤ buffer_days ≤ 2 | count = 1-2 | count = 1（不够一周） | 偏低——仅够 1-2 个发布周期 |
| 🟢 绿 | 3 ≤ buffer_days ≤ 5 | count = 3-5 | count = 1（刚好一周+buffer） | 正常——节奏稳定 |
| 🔵 蓝 | buffer_days > 5 | count ≥ 6 | count ≥ 2（超过两周） | 积压——存货过多 |

### 各颜色触发动作（自动化 + 人工决策点）

#### 🔴 红色——断更警戒

| 触发点 | 自动动作 | 人工决策点 |
|--------|----------|------------|
| SessionStart | 报告首行高亮 `🔴 断更警戒：buffer=0，今天必须拍` | 用户决定：拍 / 接受断更 |
| `/yang-recommend` | **只推 top 1 稳分**，不推实验性选题 | 用户选择推荐选题或自选 |
| `/yang-shoot` | 正常执行 buffer+1，但报告仍为 🟠 | — |
| `/yang-status` | 输出 `❌ 事实断更状态` + 最后发布日期 | — |

**红色警戒期间禁止**：
- `/yang-recommend` 不推实验性选题
- 不建议"等更好的选题"——拍 composite 7.5 的稳分比断更安全
- 不启动新的 `/yang-learn-from` 深度拆解（耗时操作会延误拍摄）

#### 🟠 橙色——偏低

| 触发点 | 自动动作 | 人工决策点 |
|--------|----------|------------|
| SessionStart | 报告显示 `🟠 buffer 偏低：N 天存量` | 用户决定是否补拍 |
| `/yang-recommend` | 1 稳 + 1 实验，建议优先拍稳分 | 用户选择 |
| `/yang-shoot` | 正常执行 | — |

#### 🟢 绿色——正常

| 触发点 | 自动动作 | 人工决策点 |
|--------|----------|------------|
| SessionStart | 报告显示 `🟢 buffer 正常：N 天存量` | 用户自由决定拍/休 |
| `/yang-recommend` | 标准 1 稳 + 1 实验 | 用户自由选择 |
| `/yang-shoot` | 正常执行 | — |

#### 🔵 蓝色——积压

| 触发点 | 自动动作 | 人工决策点 |
|--------|----------|------------|
| SessionStart | 报告显示 `🔵 积压：N 条未发，先消化存货` | 用户决定发/复盘 |
| `/yang-recommend` | **拒绝推荐新选题**："你 buffer 已 N 条，先发掉 ≤3 条再来" | — |
| `/yang-shoot` | **警告但允许**（用户可能正在拍系列内容） | 用户确认是否继续拍 |
| `/yang-publish` | 优先推荐发布积压中时效性最弱的内容 | 用户选择发布顺序 |

**蓝色积压期间建议**：
- 优先发布积压内容中时效性最弱的（避免进一步衰减）
- 优先复盘已到期 T+3d 的内容
- 暂停新选题推荐，除非用户主动要求

### Buffer 阈值边界情况

| 边界情况 | 处理 |
|----------|------|
| `target_publish_cadence_days = null`（灵活节奏） | buffer 监控关闭，SessionStart 只显示"已拍未发：N 条"，不显示颜色 |
| buffer_count = 0 但用户刚发布（buffer 刚从 1 变 0） | 不算断更——发布当天 buffer=0 是正常的。只在**连续 ≥ cadence 天** buffer=0 才标红 |
| 用户 cadence 频繁变动 | 以 `.yang-state.json` 中最新 `target_publish_cadence_days` 为准，每次 `/yang-init` 可修改 |

---

## 节奏恢复策略

当节奏被打断（连续断更或连续积压）时，以下策略帮助恢复到稳定节奏。

### 连续断更恢复策略

**判定条件**：连续 ≥ `target_publish_cadence_days × 2` 天无新发布。

| 阶段 | 断更天数 | 策略 | 具体动作 |
|------|----------|------|----------|
| 轻度断更 | cadence × 2 ~ cadence × 3 | **快速补位** | 1. 从候选池选 composite 最高的稳分选题<br>2. 用已有脚本或快速写稿（跳过深度润色）<br>3. 拍→发，优先恢复发布节奏 |
| 中度断更 | cadence × 3 ~ cadence × 5 | **降速重启** | 1. 降低发布频率预期（日更→隔日，周更→双周）<br>2. 先发 1 条稳分重建节奏<br>3. 连续 2 周稳定后再恢复原 cadence |
| 重度断更 | > cadence × 5 | **冷启动模式** | 1. 切换到 cold-start 心态：重新评估选题方向<br>2. `/yang-trends` 刷新热点感知<br>3. `/yang-learn-from` 重新拆对标（断更期间市场可能已变）<br>4. 先发 1 条"回归"内容，不必追求高分<br>5. 连续 3 周稳定后再恢复原 cadence |

**断更恢复的节奏元规则**：
- 不要试图一次性补发多条——断更后恢复的关键是**稳定**，不是**量**
- 第一条恢复内容选稳分，不冒险
- 恢复期间不推实验性选题
- 每次发布后检查 buffer 是否回到 🟢

### 连续积压恢复策略

**判定条件**：buffer_days > 5（蓝色）持续 ≥ 7 天。

| 阶段 | 积压程度 | 策略 | 具体动作 |
|------|----------|------|----------|
| 轻度积压 | buffer_days 5-10，持续 < 7 天 | **加速消化** | 1. 每个发布周期发 2 条（而非 1 条）<br>2. 按时效性排序：最弱的先发<br>3. 暂停拍摄直到 buffer 回到 🟢 |
| 中度积压 | buffer_days 10-20，或持续 7-14 天 | **选择性清仓** | 1. 评估积压内容：时效性已过的标记 `expired`<br>2. 仍有时效性的按优先级发布<br>3. `expired` 内容不强制发布，可拆解为选题素材回收<br>4. 暂停拍摄 + 暂停新选题推荐 |
| 重度积压 | buffer_days > 20，或持续 > 14 天 | **硬重启** | 1. 停止所有新内容生产<br>2. 对积压内容做"发布 or 归档"二选一<br>3. 归档内容：脚本保留到 `scripts/`，预测文件标记 `archived`<br>4. 清仓到 buffer ≤ 2 后再恢复拍摄<br>5. 恢复后按"轻度断更"策略重启 |

**积压恢复的节奏元规则**：
- 积压内容有时效性衰减——超过 `target_publish_cadence_days × 3` 未发的，评估是否仍值得发
- 不要为了清仓而降低内容质量——发不出去的内容比不发更伤频道
- 归档不是浪费——脚本和预测数据仍可用于校准
- 清仓期间优先复盘已到期内容，不让复盘信号继续堆积

### 节奏恢复的自动提醒

SessionStart hook 在检测到断更/积压时，自动输出恢复建议：

**断更提醒格式**：
```
🔴 你已 N 天没发新内容（最后一次发布：YYYY-MM-DD）
   建议动作：[快速补位/降速重启/冷启动模式]
   → 推荐选题：<top 1 稳分选题>
```

**积压提醒格式**：
```
🔵 你有 N 条积压未发（最早一条已等 N 天）
   建议动作：[加速消化/选择性清仓/硬重启]
   → 最应先发：<时效性最弱的内容标题>
   → 可归档：<超过 X 天未发的内容数> 条
```

### 恢复后的节奏巩固

恢复到 🟢 后，进入 **2 周巩固期**：

1. 巩固期内不推实验性选题（只推稳分）
2. 巩固期内 buffer 维持在 2-4 天存量（不追求高 buffer）
3. 巩固期结束且连续 2 周节奏稳定 → 恢复正常 1 稳 + 1 实验推荐策略
4. 巩固期内再次断更/积压 → 重置巩固期计时
