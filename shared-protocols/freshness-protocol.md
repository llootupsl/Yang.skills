<!-- 作者: 阿洋 -->
# Freshness Protocol — 时效锁 / 锁住最新时间

被 yang-benchmark / yang-seed / yang-trends / yang-learn-from / 数据采集 adapters 引用。
规定**一切外部抓取数据**如何以"运行此刻的真实日期"为锚做新鲜度判定，**防止把旧时间内容当成当下有效信号**。

---

## 核心哲学

> **抓回来的不一定是"现在"。判定时效的锚点永远是"运行那一刻"，不是任何写死的日期。**
>
> - 平台会把半年前的爆款继续推到搜索/推荐结果里——抓取顺序 ≠ 时间顺序。
> - 旧时间的爆款规律可能已失效（算法变了、人群迁移了、话题过气了），照搬 = 踩坑。
> - 所以系统在用任何外部数据前，先问一句：**这条是什么时候发的？距今多久？还算"当下"吗？**

设计目的：让"最新时间"随每次运行自动推进，杜绝"拿着去年的热点当今天的风向"。

---

## 三档语义（全系统统一）

| 档位 | 判据（距今天数） | 处理方式 |
|---|---|---|
| `fresh` | ≤ `FRESHNESS_WINDOW_DAYS`（默认 90 天） | 可直接作当下信号使用 |
| `aging` | `FRESHNESS_WINDOW_DAYS` ~ `FRESHNESS_AGING_HARD_LIMIT_DAYS`（90–365 天） | **可用，但必须显式标注"偏旧"**，结论需注明时效 |
| `stale` | > `FRESHNESS_AGING_HARD_LIMIT_DAYS`（默认 365 天） | **默认从分析中剔除**；如确需引用，强制人工确认后降权 |
| `unknown` | 发布时间无法解析 | **从严**：保留但显式提示"无法判定时效，请人工核对" |

数值常量见 `shared-protocols/constants.md` 的「时效锁参数」；代码实现见 `adapters/_common/freshness.py`。

---

## 锚点规则（不可妥协）

1. **唯一锚点 = `freshness.now_anchor()`**，返回运行此刻的 UTC 时间。
2. **任何文件、任何 prompt、任何脚本都不得硬编码"今天是哪天"**。需要"当前日期"时一律取锚点。
3. 相对时间（"3 天前""昨天""上周"）也以锚点为基准换算，保证随运行推进。

> 反例（禁止）：在文档或代码里写"截至 2026 年 6 月，最新热点是……"。
> 正例：抓取时记录每条数据的 `publish_date`，在用之前用锚点算 `days_since` 并打标。

---

## 触发矩阵（何时必须过时效闸）

| 场景 | 必过时效闸？ | 动作 |
|---|---|---|
| yang-benchmark 抓对标视频（单条/批量） | ✅ 必过 | 抓取即记录 `publish_date` → 打标；`stale` 默认不进逐帧/话术分析，`aging` 进但标注 |
| 竞品数据采集（`adapters/competitor-data`） | ✅ 必过 | `recent_videos` 全量打标 + 汇总 `freshness_summary`，最新一条若 aging/stale 即告警 |
| 高赞评论挖掘选题（`mine_comments`） | ✅ 必过 | 只从 `fresh`/`aging` 视频的评论里挖；`stale` 视频的评论默认不作为当下选题来源 |
| yang-trends 热点拉取 | ✅ 必过 | 热点条目按发布/上榜时间排序，优先 `fresh`；展示时标注每条时效 |
| yang-seed Channel（含高赞评论金句 Channel D） | ✅ 必过 | 外部素材入池前打标，`stale` 不默认入池 |
| yang-learn-from 拆解指定账号成长逻辑 | ⚠️ 部分 | **成长轨迹分析**需要历史数据（可含旧时间，属正常）；但**"当下可复用打法"的结论**只能基于近期作品，旧作仅作趋势对照 |
| 个人经历/内省类输入（yang-seed Mode B） | ❌ 不涉及 | 用户自己的故事是长青的，不抓外部、不判时效 |

---

## 标准流程（被采集/分析脚本共用）

```
抓取一条外部数据
  └─ 记录原始 publish_date（各平台格式不一，原样存）
       └─ freshness.annotate(record)             # 写入 _freshness / _days_since / _checked_at
            ├─ fresh   → 正常使用
            ├─ aging   → 使用 + 在产出里标注"偏旧（距今 N 天）"
            ├─ stale   → 默认剔除；如人工坚持引用 → 降权并标注
            └─ unknown → 保留 + 提示"时效未知，请人工核对"
批量数据
  └─ freshness.sort_by_recency(...)              # 最新在前
       └─ freshness.filter_recent(...)（可选）    # 只留新鲜窗口内
            └─ 汇总 freshness_summary：newest_publish_date / 各档计数 / 运行锚点
```

代码层可直接调用（零第三方依赖）：

```python
from adapters._common import freshness
# 或在 adapters/ 目录下：from _common import freshness

freshness.now_anchor()                     # 运行此刻锚点
freshness.freshness_label(publish_date)    # 'fresh'|'aging'|'stale'|'unknown'
freshness.annotate(record)                 # 原地补充时效元数据
freshness.sort_by_recency(records)         # 最新在前
freshness.filter_recent(records)           # 只留新鲜窗口内（默认保留 unknown）
```

---

## 产出标注要求

凡是基于外部抓取数据得出的结论（对标拆解、选题建议、热点榜、评论金句），产出里必须能回答"这是基于什么时候的数据"：

- 单条引用：标注该条的发布时间与时效档（如「该爆款发布于 2026-04-12 · 偏旧」）。
- 批量结论：标注样本的时间范围与最新一条时间（如「样本时间范围 近 38 天，最新一条 3 天前」）。
- 出现 `stale`/`unknown` 占比偏高时：显式提醒用户"对标库可能过期，建议更换更活跃的对标账号或缩小抓取时间窗"。

---

## 与 yang-doctor 的分工

- 本协议按**单条内容的发布时间**判定时效（fresh/aging/stale）。
- `yang-doctor` 诊断项 13 按 `BENCHMARK_STALE_MONTHS`（6 个月）清理**长期不更新的对标账号**（账号级，而非单条）。
- 二者互补：一个管"这条数据新不新"，一个管"这个账号还活不活跃"。

---

## 数据新鲜度量化判定规则

### 量化阈值表

以下为 fresh / aging / stale 三档的具体时间阈值定义，基于数据类型差异化设定：

| 档位 | 通用标准 | 竞品快照 | 热点数据 | 对标报告 | 算法/规则类 |
|------|---------|---------|---------|---------|-----------|
| **fresh** | ≤ 90 天 | ≤ 30 天 | ≤ 7 天 | ≤ 180 天 | ≤ 365 天 |
| **aging** | 91–365 天 | 31–90 天 | 8–30 天 | 181–365 天 | 366–730 天 |
| **stale** | > 365 天 | > 90 天 | > 30 天 | > 365 天 | > 730 天 |

**阈值选择逻辑**：

| 数据类型 | 新鲜度敏感度 | 阈值设计理由 |
|---------|------------|------------|
| **竞品快照** | 极高 | 竞品策略变化快，30 天前的竞品数据已可能不代表当前打法；90 天前的竞品快照参考价值极低 |
| **热点数据** | 最高 | 热点生命周期通常 3-14 天，7 天后基本冷却；30 天前的热点仅具历史参考价值 |
| **对标报告** | 中等 | 对标账号的内容风格和定位变化较慢，180 天内的对标仍有参考意义 |
| **算法/规则类** | 低 | 平台算法和规则虽会调整，但底层逻辑相对稳定；365 天内的规则仍可参考 |
| **通用标准** | 中 | 适用于未明确分类的外部数据，采用 90/365 天的默认窗口 |

### 阈值常量定义

在 `shared-protocols/constants.md` 中新增以下参数：

```
# 通用新鲜度窗口
FRESHNESS_WINDOW_DAYS = 90
FRESHNESS_AGING_HARD_LIMIT_DAYS = 365

# 竞品快照新鲜度窗口
FRESHNESS_COMPETITOR_FRESH_DAYS = 30
FRESHNESS_COMPETITOR_AGING_DAYS = 90

# 热点数据新鲜度窗口
FRESHNESS_TREND_FRESH_DAYS = 7
FRESHNESS_TREND_AGING_DAYS = 30

# 对标报告新鲜度窗口
FRESHNESS_BENCHMARK_FRESH_DAYS = 180
FRESHNESS_BENCHMARK_AGING_DAYS = 365

# 算法/规则类新鲜度窗口
FRESHNESS_ALGORITHM_FRESH_DAYS = 365
FRESHNESS_ALGORITHM_AGING_DAYS = 730
```

### 数据类型识别规则

| 识别信号 | 归类 | 示例 |
|---------|------|------|
| 数据来源为 `adapters/competitor-data` | 竞品快照 | 竞品账号最近视频列表、竞品数据面板 |
| 数据来源为 `yang-trends` 或 `adapters/trend-*` | 热点数据 | 微博热搜、知乎热榜、抖音热点 |
| 数据来源为 `yang-benchmark` 或 `yang-learn-from` | 对标报告 | 对标账号拆解报告、成长轨迹分析 |
| 数据内容涉及"算法""规则""机制""推荐"关键词 | 算法/规则类 | 平台推荐机制分析、审核规则解读 |
| 无法识别 | 通用标准 | 默认使用通用阈值 |

---

## 过期数据自动降级处理规则

### 降级处理矩阵

| 数据状态 | 自动处理动作 | 通知级别 | 存储策略 |
|---------|------------|---------|---------|
| **fresh** | 无需处理，正常使用 | 无 | 保留在活跃数据区 |
| **aging** | 自动标注"偏旧"标签；在分析结论中追加时效警告 | 提示（INFO） | 保留在活跃数据区，标记 `aging` 标签 |
| **stale** | 自动从主分析流程中剔除；移入归档区 | 警告（WARN） | 移入 `.yang-cache/stale-archive/` |
| **unknown** | 保留但强制标注"时效未知" | 警告（WARN） | 保留在活跃数据区，标记 `unknown` 标签 |

### 自动降级执行流程

```
数据入库
  └─ freshness.annotate(record, data_type=auto_detect)
       ├─ data_type 识别 → 选择对应阈值表
       ├─ 计算 days_since → 判定档位
       ├─ fresh   → 正常入库
       ├─ aging   → 入库 + 追加 _freshness_label="aging" + 输出标注
       ├─ stale   → 入库标记 + 从分析池移除 + 归档
       └─ unknown → 入库 + 追加 _freshness_label="unknown" + 强制提示
```

### 降级后的引用规则

| 场景 | stale 数据引用规则 | aging 数据引用规则 |
|------|------------------|------------------|
| yang-seed 选题生成 | 禁止作为主选题来源；仅可作"历史参照"附注 | 可引用但必须标注"距今 N 天，偏旧" |
| yang-score 评分 | 不参与评分计算 | 参与计算但权重降为 0.5 |
| yang-predict 预测 | 不参与预测模型 | 参与预测但 confidence 自动降一级 |
| yang-benchmark 对标 | 不作为对标样本 | 可作为对照样本，不作为主对标 |
| yang-trends 热点 | 不展示在热点列表 | 展示但标注"偏旧热点" |
| yang-learn-from 拆解 | 仅用于成长轨迹历史段 | 可用于打法分析但标注时效 |

### 批量降级告警

当一次抓取中 stale 数据占比超过以下阈值时，触发告警：

| 场景 | stale 占比告警阈值 | 告警动作 |
|------|------------------|---------|
| 竞品数据采集 | > 50% | "对标账号可能不活跃，建议更换更活跃的对标账号" |
| 热点数据拉取 | > 30% | "热点源可能过期，检查数据源配置" |
| 对标报告 | > 70% | "对标库整体偏旧，建议更新对标账号" |
| 通用数据 | > 50% | "数据池整体时效偏低，建议缩小抓取时间窗" |

### 降级数据恢复

stale 数据在以下条件下可恢复为 aging：

1. **同一来源有新的 fresh 数据产生**：该来源的历史 stale 数据自动升为 aging（说明来源仍活跃，历史数据有对照价值）
2. **人工显式确认**：用户手动标记"此条仍有效" → 升为 aging，追加 `_manually_confirmed=true` 标签
3. **算法/规则类数据**：stale 的算法数据经人工确认仍适用 → 升为 aging

stale 数据**不可**直接恢复为 fresh——必须重新抓取才能获得 fresh 状态。
