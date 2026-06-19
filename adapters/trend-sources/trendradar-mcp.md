<!-- 作者: 阿洋 -->
# adapters/trend-sources/trendradar-mcp — 综合社会热点（MCP）

**适合谁**：观点视频 / 时评 / 文化垂类 / 美食 / 职场 / 社会议题——**任何非 AI 垂直**的内容。

---

## 它是什么

TrendRadar 是中文热点聚合监控工具，拉取微博 / 知乎 / 抖音 / B 站 / 头条等多平台热点。它自带 MCP server，暴露 25+ 个 tool。

Yang.skills 把它当作 trend-sources adapter 之一——用户配 MCP server 后，yang-seed / yang-trends 自然能调。

- **多平台覆盖**：微博 / 知乎 / 抖音 / B站 / 头条 / 36kr / 等等
- **AI 增强工具**：`analyze_topic_trend` 给爆火/衰退判定；`compare_periods` 给周环比；`analyze_sentiment` 给情感倾向
- **集成方式**：通过 MCP 协议调用，零耦合

## 装

参考 TrendRadar MCP 配置文档。装好后用户的工具链含 `mcp__trendradar__*` 系列工具。

Yang.skills 不打包 TrendRadar——用户自己装、自己保管 server 资源。

## yang-seed / yang-trends 调用的关键工具

| MCP 工具 | 用途 | 在哪调 |
|---|---|---|
| `mcp__trendradar__get_latest_news` | 拿最新热榜（最直接） | yang-seed Mode C 主调 / yang-trends 主调 |
| `mcp__trendradar__get_trending_topics` | 自动提取话题统计 | yang-seed Mode C 备用 |
| `mcp__trendradar__analyze_topic_trend` | 单话题趋势分析（爆火/衰退） | yang-seed Mode A 灰色场景 enrich（用户提了具体话题且同意拉数据） |
| `mcp__trendradar__compare_periods` | 周环比 / 月环比 | yang-bump 升级 rubric 时作"用户领域是否变化"的弱信号（罕见用） |
| `mcp__trendradar__search_news` | 关键词搜索 | yang-seed Mode A 用户提了关键词时 |

## 输出格式契约

TrendRadar MCP 返回 JSON / markdown。yang-seed 收到后：

1. 解析 items（title / source / hot_score / snapshot_at / url）
2. 按 [candidate-schema.md](../../shared-protocols/candidate-schema.md) 算稳定 id（`sha256(source + normalized_title + url_path)[:12]`）
3. 去重（参考 yang-trends 的去重协议）
4. 用当前 rubric 粗筛
5. 写入 `candidates.md`

## 失败模式

| 症状 | 处理 |
|---|---|
| MCP server 没装 / 没启动 | yang-seed 自动降级到下一个启用的源（如 aihot 或 manual-paste），不抛异常 |
| MCP 调用超时 | 30 秒后超时，提示用户"trendradar 慢，要等还是切别的源" |
| newsnow 上游 API 改了 | TrendRadar 维护者会修；用户跟着升级 |

## 稳定性

★★★★ — 取决于上游项目活跃度 + newsnow 上游稳定性。

---

## 与其他 adapter 的关系

- **vs aihot.md**：互补不重叠。trendradar 是综合社会，aihot 是 AI 垂直。两者都启用时按 `content_form` 路由（详见 [data-source-routing.md](../../shared-protocols/data-source-routing.md)）
- **vs manual-paste**：永远的 fallback。两个 API 都失败时走 manual-paste

---
