<!-- 作者: 阿洋 -->
# 本地降级方案（Local Fallback）

本文档记录 Yang.skills 所有外部 API 依赖的本地降级方案。当网络受限、API 不可用或需要离线运行时，可使用对应的本地适配器替代。

---

## 双架构统一（借鉴 LocoAgent）

所有适配器遵循统一接口（`adapters/adapter_base.py`），调用方无需知道底层实现：

```python
from adapters.registry import AdapterRegistry

# 统一调用入口
result = AdapterRegistry.collect("trends", sources=["weibo"], limit=30)

# 检查可用性
status = AdapterRegistry.list_available()
```

**降级策略**：local_first → browser_enhanced → api_fallback
- 本地优先：从本地文件读取数据（零网络）
- 浏览器增强：Playwright抓取（需安装）
- API降级：公开端点请求（需网络）

---

## 依赖总览

| # | 模块 | 外部依赖 | 严重度 | 本地替代 | 状态 |
|---|------|---------|--------|---------|------|
| 1 | `adapters/trend-sources/fetch_trends.py` | requests → 微博/知乎/B站/百度/抖音/头条/IT之家/36氪 公开端点 | 高 | `local_trends.py` | ✅ 已实现 |
| 2 | `adapters/competitor-search/search.py` | requests → B站API + Playwright → 抖音/小红书/快手/Google | 高 | `local_search.py` | ✅ 已实现 |
| 3 | `adapters/benchmark-analysis/pipeline.py` | yt-dlp 下载 + faster-whisper 转录 + Playwright 评论 | 高 | `local_pipeline.py` | ✅ 已实现 |
| 4 | `adapters/perf-data/douyin-session/` | Playwright → 抖音创作者中心 + 前台评论 | 中 | `local_session.py` | ✅ 已实现 |
| 5 | `adapters/competitor-data/collector.py` | requests → B站API + Playwright → 巨量算数 | 中 | 使用 `local_search.py` 覆盖 | ✅ 已实现 |
| 6 | `adapters/competitor-monitor/monitor.py` | requests → RSSHub + Playwright 轮询 | 中 | 本地 RSS 文件 / 手动更新 | ⚠️ 需手动 |
| 7 | `tools/dspy_scoring.py` | DSPy → Anthropic/OpenAI/Ollama LLM API | 低 | v3-rules 规则评分（已有内置降级） | ✅ 已内置 |
| 8 | `tools/graphrag_index.py` | GraphRAG → OpenAI Chat/Embedding API | 低 | 轻量关键词索引（已有内置降级） | ✅ 已内置 |
| 9 | `adapters/script-extraction/whisper/` | whisper-cpp / openai-whisper / faster-whisper | 中 | 从本地 .txt/.md 读取转录稿 | ⚠️ 需手动 |
| 10 | `adapters/benchmark-analysis/download.py` | yt-dlp → 各平台视频下载 | 中 | 手动下载视频到本地目录 | ⚠️ 需手动 |

---

## 1. 热点数据源 — `local_trends.py`

**原始依赖**: `fetch_trends.py` 通过 `requests.get()` 调用 8 个平台的公开 API

**本地替代**: `adapters/trend-sources/local_trends.py`

**工作原理**:
- 从本地 `.md` 文件读取热点数据（`aihot.md`、`weibo-hot.md`、`zhihu-hot.md` 等）
- 解析 Markdown 表格/列表格式，输出与 `fetch_trends.py` 完全一致的 JSON 结构
- 零网络请求，零外部依赖

**使用方法**:
```bash
# 在线模式（原始）
python adapters/trend-sources/fetch_trends.py --sources weibo,zhihu --out trends.json

# 离线模式（本地替代）
python adapters/trend-sources/local_trends.py --sources weibo,zhihu --out trends.json

# 指定本地数据目录
python adapters/trend-sources/local_trends.py --data-dir ./local-data/trends --out trends.json
```

**本地数据文件格式**:
每个 `.md` 文件可包含以下任一格式：
- Markdown 表格：`| 排名 | 标题 | 热度 | URL |`
- Markdown 列表：`1. 标题 (热度: 12345)`
- JSON 行：每行一个 `{"title": "...", "hotness": 123, "url": "..."}`

**自动降级触发**: 当 `requests` 未安装或所有在线源均失败时，`fetch_trends.py` 的 stderr 已提示"可让 Agent 改用自身 WebFetch 抓取平台热搜页作为兜底"。`local_trends.py` 是该兜底的结构化实现。

---

## 2. 竞品搜索 — `local_search.py`

**原始依赖**: `search.py` 三层架构（B站 API → Playwright → 兜底）

**本地替代**: `adapters/competitor-search/local_search.py`

**工作原理**:
- 从本地 JSON/CSV 数据库搜索竞品信息
- 支持关键词匹配和平台过滤
- 输出与 `search.py` 完全一致的 JSON 结构

**使用方法**:
```bash
# 在线模式（原始）
python adapters/competitor-search/search.py "考研" --platforms douyin,bilibili

# 离线模式（本地替代）
python adapters/competitor-search/local_search.py "考研" --platforms douyin,bilibili

# 指定本地数据库路径
python adapters/competitor-search/local_search.py "考研" --db ./local-data/competitors.json
```

**本地数据库格式** (JSON):
```json
[
  {
    "platform": "douyin",
    "account_name": "xxx",
    "account_id": "xxx",
    "account_url": "https://www.douyin.com/user/xxx",
    "follower_count": 100000,
    "category_tags": ["考研", "教育"],
    "bio": "..."
  }
]
```

---

## 3. 对标分析管线 — `local_pipeline.py`

**原始依赖**: `pipeline.py` 串联 yt-dlp + faster-whisper + Playwright

**本地替代**: `adapters/benchmark-analysis/local_pipeline.py`

**工作原理**:
- 跳过下载步骤，直接使用本地已有的视频文件
- 跳过转录步骤，直接读取本地已有的 transcript.json/transcript.md
- 跳过评论抓取，直接读取本地已有的 comments.json
- 只运行本地可执行的步骤（帧提取等，如 opencv 可用）

**使用方法**:
```bash
# 在线模式（原始）
python adapters/benchmark-analysis/pipeline.py "https://..." --video-id abc123

# 离线模式（本地替代）
python adapters/benchmark-analysis/local_pipeline.py --video-dir ./videos/benchmark/abc123
```

**目录结构要求**:
```
videos/benchmark/{video_id}/
├── original.mp4        # 本地视频文件（可选）
├── transcript.json     # 本地转录文件（可选）
├── transcript.md       # 本地转录 Markdown（可选）
├── comments.json       # 本地评论文件（可选）
└── meta.json           # 元数据（可选）
```

---

## 4. 抖音数据会话 — `local_session.py`

**原始依赖**: `douyin-session/crawler.py` 通过 Playwright 抓取抖音创作者中心

**本地替代**: `adapters/perf-data/local_session.py`

**工作原理**:
- 从本地 CSV/JSON 文件读取抖音视频数据
- 输出与 `crawler.py` 的 `fetch_all()` 完全一致的数据结构
- 支持从抖音创作者中心导出的 CSV 格式

**使用方法**:
```bash
# 在线模式（原始）
python adapters/perf-data/douyin-session/run.sh fetch-all <aweme_id>

# 离线模式（本地替代）
python adapters/perf-data/local_session.py --data-dir ./local-data/douyin --aweme-id xxx

# 从 CSV 文件读取
python adapters/perf-data/local_session.py --csv ./local-data/douyin/videos.csv
```

**本地数据格式**:
- CSV: 抖音创作者中心导出格式（标题,播放量,点赞数,评论数,分享数,发布时间）
- JSON: 与 `fetch_all()` 输出格式一致

---

## 5. DSPy 评分 — 内置降级

**原始依赖**: `dspy_scoring.py` 需要 Anthropic/OpenAI API Key 或 Ollama

**内置降级**: 已实现
- 样本数 < 5 时自动使用 v3-rules 规则评分
- DSPy 未安装时回退到规则评分
- LLM 配置失败时回退到规则评分
- **无需额外本地替代文件**

**降级触发条件**:
1. `dspy-ai` 包未安装
2. `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` 均未设置且 Ollama 未运行
3. 校准样本不足（< 5 条）

---

## 6. GraphRAG 索引 — 内置降级

**原始依赖**: `graphrag_index.py` 需要 OpenAI API Key（`GRAPHRAG_API_KEY`）

**内置降级**: 已实现
- `graphrag` 包未安装时自动使用轻量关键词索引
- 索引构建失败时回退到轻量索引
- 查询时 GraphRAG 不可用则回退到关键词搜索
- **无需额外本地替代文件**

**降级触发条件**:
1. `graphrag` 包未安装
2. `GRAPHRAG_API_KEY` 未设置
3. GraphRAG 索引构建失败

---

## 7. 竞品监控 — 手动降级

**原始依赖**: `monitor.py` 需要 RSSHub 服务 + Playwright

**降级方案**:
- 手动将竞品最新视频信息写入本地 JSON 文件
- 使用 `local_search.py` 查询本地数据库替代在线监控
- 定期手动更新本地数据

---

## 8. Whisper 转录 — 手动降级

**原始依赖**: `whisper/run.sh` / `transcribe.py` 需要 whisper-cpp / openai-whisper / faster-whisper

**降级方案**:
- 手动粘贴文稿到 `transcript.md`（yang-learn-from 的 Way a）
- 使用其他本地 ASR 工具（SenseVoice/FunASR/FireRedASR/GLM-ASR，见 benchmark-auto/run.sh）
- 从字幕文件 (.srt/.vtt) 转换

---

## 9. 视频下载 — 手动降级

**原始依赖**: `download.py` 需要 yt-dlp

**降级方案**:
- 浏览器手动下载视频到 `videos/benchmark/{video_id}/original.mp4`
- 使用其他下载工具（you-get、lux 等）
- 从本地已有视频库复制

---

## 统一环境变量

| 环境变量 | 用途 | 本地降级时的值 |
|---------|------|--------------|
| `YANG_OFFLINE_MODE` | 全局离线模式开关 | `1` 启用离线模式 |
| `YANG_LOCAL_DATA_DIR` | 本地数据根目录 | 默认 `./local-data` |
| `BILIBILI_COOKIE` | B站 Cookie | 离线时忽略 |
| `ANTHROPIC_API_KEY` | Anthropic API | 离线时忽略，走 v3-rules |
| `OPENAI_API_KEY` | OpenAI API | 离线时忽略，走 v3-rules |
| `GRAPHRAG_API_KEY` | GraphRAG 嵌入 API | 离线时忽略，走轻量索引 |
| `DASHSCOPE_API_KEY` | 阿里云通义 API | 离线时忽略 |

**使用示例**:
```bash
# 启用全局离线模式
export YANG_OFFLINE_MODE=1
export YANG_LOCAL_DATA_DIR=./my-local-data

# 所有 adapter 自动降级到本地模式
python adapters/trend-sources/local_trends.py --out trends.json
python adapters/competitor-search/local_search.py "考研" --out competitors.json
```
