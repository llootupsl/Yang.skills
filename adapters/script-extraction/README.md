# Adapter: script-extraction（文稿提取与节奏分析）

> 作者: 阿洋

被 `/yang-learn-from`、`/yang-polish`、`/yang-emotion-curve` 等技能调用，提供视频转录和文稿节奏分析能力。

## 这个 adapter 是干嘛的

本目录包含两个核心能力：

1. **视频/音频转录**（`whisper/`）：把 mp4 / mov / mp3 等媒体文件转成文字 transcript
2. **气口/语速分析**（`pacing_analyzer.py`）：对文稿进行气口标注和语速分析，借鉴 cuerecord 理念，基于 forced alignment 技术

---

## 文件清单

```
adapters/script-extraction/
├── README.md                # 本文件
├── pacing_analyzer.py       # 气口/语速分析器主模块
├── pacing_protocol.md       # 气口/语速标注协议
└── whisper/
    ├── README.md            # whisper 转录说明
    └── run.sh               # whisper 转录 wrapper
```

---

## 一、视频/音频转录（whisper/）

### 用途

把 mp4 / mov / mp3 等媒体文件转成文字 transcript，让 Claude 能读对标账号的稿子。

抖音 / B站 / YouTube 大多数视频**没有官方字幕**——拿稿子绕不开 ASR（语音转录）。

### 安装与用法

详见 [whisper/README.md](whisper/README.md)。

推荐使用 whisper-cpp（快、轻、纯 C++），或 faster-whisper（Python 版，`adapters/benchmark-analysis/transcribe.py`）。

### 输出格式

`transcript.md`：纯文本转录，按段落分（不是字幕格式）。

---

## 二、气口/语速分析（pacing_analyzer.py）

### 用途

借鉴 cuerecord 理念（对文稿标出气口快慢语速），基于 forced alignment 技术实现：

1. **气口标注**：标出文稿中的停顿点
   - 自然停顿：逗号、句号等标点处
   - 强调停顿：重要信息前后的停顿
   - 情绪停顿：情绪转折处的停顿
   - 换气停顿：长句中间的换气点

2. **语速分析**：标注文稿的快慢语速
   - 快（>250 字/分钟）/ 正常（200-250）/ 慢（<200）
   - 加速（从慢变快）/ 减速（从快变慢）

3. **节奏建议**：基于气口和语速分析提供节奏优化建议

### 技术背景

基于 forced alignment（强制对齐）技术：
- **WhisperX**：VAD + 音素模型强制对齐，产出词级时间戳
- **whisper-timestamped**：基于交叉注意力权重的 DTW 对齐，无需额外模型
- **IndexTTS 2.0**：标点控制停顿理念（正向参考）

支持两种模式：
- **文本模式**（默认）：仅有纯文本，基于文本特征估算气口和语速
- **音频模式**：有 word-level timestamps（来自 whisper-timestamped/WhisperX），使用真实时间戳

### 用法

```python
from adapters.script_extraction.pacing_analyzer import analyze_pacing, generate_pacing_report

# 纯文本模式
result = analyze_pacing("你的文稿内容...")
print(generate_pacing_report(result))

# 音频模式（有 word-level timestamps）
segments = [
    {"start": 0.0, "end": 0.5, "text": "你好"},
    {"start": 0.5, "end": 1.2, "text": "世界"},
]
result = analyze_pacing("你好世界", segments=segments)
print(generate_pacing_report(result))
```

### 命令行

```bash
# 纯文本模式
python pacing_analyzer.py script.txt --output report.md

# 音频模式
python pacing_analyzer.py script.txt --segments timestamps.json --output report.md
```

### 输出

Markdown 格式的节奏分析报告，包含：
- 基本信息（字数、气口数、预估时长、节奏健康度评分）
- 气口分析（类型分布、密度评估）
- 语速分析（整体语速、分布、段落明细）
- 节奏问题诊断
- 节奏优化建议

详细的标注协议见 [pacing_protocol.md](pacing_protocol.md)。

---

## 与其他 adapter 的关系

- 同 `adapters/benchmark-analysis/`、`adapters/perf-data/douyin-session/` 一样，是 Yang.skills 的可选 adapter
- `whisper/` 在 `/yang-learn-from --way b` 时调用（Way a 粘文本不需要）
- `pacing_analyzer.py` 可被 `/yang-polish`、`/yang-emotion-curve` 调用，提供物理节奏分析

## 与其他 Skill 的协同

| Skill | 协同关系 |
|-------|---------|
| yang-polish | pacing 提供物理节奏分析，polish 关注语言肌理，两者互补不冲突 |
| yang-emotion-curve | pacing 是"物理节奏"，emotion-curve 是"情绪节奏"，完整节奏分析需结合两者 |
| yang-learn-from | whisper 转录产出的 segments 可作为 pacing_analyzer 音频模式的输入 |

## 稳定性等级

★★★★ — whisper 是开源标准 ASR；pacing_analyzer 基于文本特征和数学计算，无外部依赖，不会突然失效。

## 风险提示

- **TOS**：转录自己下载的对标账号视频用于个人学习参考是合理使用
- **隐私**：whisper 全部本地运行，不传任何数据到云端
- **pacing_analyzer** 是只读分析工具，不修改文稿，不触发 session 锁
