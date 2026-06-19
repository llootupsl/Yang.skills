<!-- 作者: 阿洋 -->
# 热点数据源（开箱即用 · 零配置）

本目录提供**可直接运行**的多源热点聚合能力，被 `yang-trends` 与 `yang-seed`（Channel C）调用。

## 一条命令拉全部公开热榜

```bash
python adapters/trend-sources/fetch_trends.py --limit 30 --out candidates/trends_raw.json
```

- **零配置**：只调各平台公开匿名端点 + 浏览器 UA，**不需要 cookie / token / API Key / MCP server**。
- **多源**：默认 微博热搜 · 知乎热榜 · B站热门 · 百度热搜 · 抖音热点 · 头条热榜；另可选 IT之家(科技) · 36氪(创投)。
- **时效锁**：所有条目以"运行此刻"为锚做新鲜度判定（见 `../../shared-protocols/freshness-protocol.md`），带单条发布时间的源用真实时间判定，纯热榜词条以抓取时刻为准并标 `unknown`。
- **优雅降级**：任一源失败（结构变更/限流/网络）只跳过该源，其余照常返回；仅当所有源都失败才非零退出。

## 可选源

| `--sources` 取值 | 覆盖面 | 单条发布时间 |
|---|---|---|
| `weibo` | 全民/娱乐/社会热点 | 无（热榜词条） |
| `zhihu` | 深度讨论/知识类 | 无 |
| `bilibili` | 视频综合热门 | 有（pubdate） |
| `baidu` | 实时搜索热点 | 无 |
| `douyin` | 抖音热点词 | 无 |
| `toutiao` | 资讯热榜 | 无 |
| `ithome` | 科技/数码（RSS） | 有（pubDate） |
| `36kr` | 创投/商业 | 无 |

```bash
# 选子集 + 垂直关键词预筛
python adapters/trend-sources/fetch_trends.py --sources weibo,zhihu,bilibili --keyword 考研 --out candidates/trends_raw.json
```

## 输出形态

```json
{
  "meta": { "anchor": "...", "sources_succeeded": ["weibo","zhihu",...], "total": 142, "errors": [...] },
  "trends": [
    { "id": "...", "title": "...", "source": "trend:weibo-hot", "url": "...",
      "hotness": 1234567, "rank": 1, "publish_date": null,
      "_freshness": "unknown", "_checked_at": "..." }
  ]
}
```

字段对齐 `../../shared-protocols/candidate-schema.md` 的核心列；打分由调用方（yang-score）后续处理，本层只负责"抓 + 标时效"。

## 可选增强（非必需）

- **TrendRadar MCP**（`trendradar-mcp.md`）：若用户自行注册该 MCP，可叠加结构化热度曲线。
- **AI HOT**（`aihot.md`）：AI 垂直资讯，按需单独查询。
- **平台专源说明**：`weibo-hot.md` / `zhihu-hot.md` 保留各平台端点与字段映射细节，供需要单独微调解析时参考。

## 数据源可靠性评级

| 评级 | 标准 | 数据源 |
|---|---|---|
| **A级** | 官方开放API或稳定RSS，结构化输出，限流宽松，长期可用性高 | `ithome`(RSS)、`36kr`(RSS) |
| **B级** | 公开匿名端点但非官方API，页面结构偶有变更，需定期维护选择器 | `bilibili`(有pubdate)、`weibo`、`zhihu`、`baidu`、`toutiao` |
| **C级** | 非公开接口或强反爬机制，解析不稳定，可能随时失效 | `douyin`(热点词接口变动频繁) |

**评级影响**：
- A级源失败时自动重试1次，间隔2秒；B级源失败直接跳过；C级源失败不重试。
- 聚合结果按 A→B→C 优先级排序去重（同主题条目优先保留高评级源）。

## 单源失败自动降级行为

1. **单源失败**：该源条目置空，`meta.errors` 记录 `{source, error, timestamp}`，其余源照常返回。
2. **多源级联失败**：按 A→B→C 顺序尝试；若某评级全部失败，降级到下一评级继续。
3. **全源失败**：脚本以退出码 2 退出，`stderr` 输出所有失败源及原因；不写入输出文件。
4. **部分成功**：`meta.sources_succeeded` 列出成功源，`meta.total` 为实际获取条数；调用方应检查 `total < 预期` 的情况。

## 新增数据源接入规范

接入新数据源需满足以下要求：

1. **实现 `fetch_<source_name>(limit: int) -> list[dict]` 函数**：
   - 返回条目必须包含 `title`（必填）、`url`（必填）、`hotness`（可选，int）、`rank`（可选，int）、`publish_date`（可选，ISO 8601 或 null）。
   - 异常时返回空列表 `[]`，不得抛出未捕获异常。
2. **注册到 `FETCHERS` 字典**：键为 `--sources` 取值，值为上述函数引用。
3. **评定可靠性等级**：按上方评级标准自评，写入本 README 的评级表。
4. **添加 `--sources` 选项说明**：在本 README 的"可选源"表格中补充行。
5. **零配置原则**：不得要求用户提供 cookie / token / API Key 才能获取基本数据；如需增强能力，走"可选增强"路径。
6. **编写单源测试**：在 `tests/` 下添加 `test_fetch_<source_name>.py`，至少覆盖正常返回与空返回两个用例。

## 离线模式（本地数据源）

当网络受限或所有在线源均不可用时，可使用 `local_trends.py` 从本地文件读取热点数据：

```bash
# 离线模式：从本地文件读取热点
python adapters/trend-sources/local_trends.py --out candidates/trends_raw.json

# 指定数据目录和源
python adapters/trend-sources/local_trends.py --data-dir ./local-data/trends --sources weibo,zhihu --keyword 考研 --out trends.json
```

- **零网络**：不发起任何 HTTP 请求，不依赖 `requests` 等外部库。
- **输出兼容**：输出 JSON 结构与 `fetch_trends.py` 完全一致，上层调用方无需修改。
- **多格式支持**：自动识别 Markdown 表格/列表、JSON、JSONL、CSV 四种格式。

### 本地数据文件

将热点数据文件放入 `adapters/trend-sources/local-data/` 目录（或通过 `--data-dir` 指定）：

| 文件名 | 对应在线源 | 格式示例 |
|---|---|---|
| `weibo-hot.md` | 微博热搜 | Markdown 表格或列表 |
| `zhihu-hot.md` | 知乎热榜 | Markdown 表格或列表 |
| `bilibili.json` | B站热门 | JSON 数组 |
| `baidu-hot.md` | 百度热搜 | Markdown 列表 |
| `douyin-hot.md` | 抖音热点 | Markdown 列表 |
| `toutiao-hot.csv` | 头条热榜 | CSV |
| `aihot.md` | AI 垂直资讯 | Markdown 列表 |

### Markdown 格式示例

**表格格式**：
```markdown
| 排名 | 标题 | 热度 |
|------|------|------|
| 1 | 高考作文题 | 2876543 |
| 2 | AI 大模型 | 1923456 |
```

**列表格式**：
```markdown
1. 高考作文题 (热度: 2876543)
2. AI 大模型 (热度: 1923456)
3. 考研报名
```

### 环境变量

| 变量 | 说明 |
|---|---|
| `YANG_OFFLINE_MODE=1` | 全局离线模式开关 |
| `YANG_LOCAL_DATA_DIR` | 本地数据根目录（默认 `./local-data`，热点数据在 `$DIR/trends/` 下） |

> 完整的本地降级方案见 `../../shared-protocols/local-fallback.md`。

## 维护说明

公开端点的页面结构/字段可能随平台更新而变化。若某源持续解析失败，`fetch_trends.py` 会在 stderr 标明该源名，按文件内对应 `fetch_<源>()` 函数微调选择器即可；其余源不受影响。
