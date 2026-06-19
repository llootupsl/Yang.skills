# 气口/语速标注协议

> 作者: 阿洋 | 版本: 1.0 | 借鉴 cuerecord 理念，基于 forced alignment 技术

## 协议概述

本协议定义文稿气口标注和语速分析的标准格式、标注规则和与其他 Skill 的协同方式。
pacing_analyzer.py 是本协议的参考实现。

## 1. 气口标注标准

### 1.1 气口类型

| 类型 | 标识 | 触发条件 | 预估停顿时长 | 优先级 |
|------|------|---------|-------------|--------|
| 自然停顿 | `natural` | 标点符号处（逗号、句号、问号等） | 0.3-0.6s | 1（最低） |
| 换气停顿 | `breathing` | 长句（>35字）中间的换气点 | 0.25s | 2 |
| 强调停顿 | `emphasis` | 重要信息（数据/结论/转折词）前后 | 0.3-0.4s | 3 |
| 情绪停顿 | `emotion` | 情绪转折词后 | 0.5s | 4（最高） |

### 1.2 去重规则

同一位置若出现多个气口，只保留优先级最高的。
优先级：emotion > emphasis > breathing > natural

### 1.3 标点停顿时长估算

| 标点 | 停顿时长 | 说明 |
|------|---------|------|
| 。！？ | 0.6s | 句末，较长停顿 |
| ，、； | 0.3s | 句中，较短停顿 |
| —— …… | 0.8s | 特殊停顿（强调/余韵） |

## 2. 语速标注标准

### 2.1 语速等级

| 等级 | 标识 | 字/分钟 | 说明 |
|------|------|---------|------|
| 极快 | `very_fast` | >280 | 语速过快，听众难以跟上 |
| 快 | `fast` | 250-280 | 语速偏快，适合信息密集段落 |
| 正常 | `normal` | 200-250 | 理想语速范围 |
| 慢 | `slow` | 160-200 | 语速偏慢，适合重点强调段落 |
| 极慢 | `very_slow` | <160 | 语速过慢，可能导致流失 |

### 2.2 语速变化

| 变化 | 标识 | 判定条件 | 说明 |
|------|------|---------|------|
| 加速 | `accelerating` | 与上段差值 > +30 字/分钟 | 语速从慢变快 |
| 减速 | `decelerating` | 与上段差值 < -30 字/分钟 | 语速从快变慢 |
| 平稳 | `steady` | 差值在 ±30 字/分钟内 | 语速保持稳定 |

### 2.3 文本模式估算规则

无音频时间戳时，基于文本特征估算语速：

- 基准语速：220 字/分钟
- 短句（<15字）：+20 字/分钟
- 长句（>40字）：-20 字/分钟
- 标点密度 >10%：-15 字/分钟
- 情绪词出现：+15 字/分钟
- 问句：-10 字/分钟（思考停顿）
- 感叹句：+10 字/分钟（情绪激动）

## 3. 节奏健康度评分

满分 100 分，基于 5 个维度加权计算：

| 维度 | 权重 | 理想值 | 评分规则 |
|------|------|--------|---------|
| 气口密度 | 30% | 5-15个/100字 | 理想=30, 次理想=20, 其他=10 |
| 语速合理性 | 25% | 200-250 字/分钟 | 理想=25, 次理想=18, 其他=8 |
| 语速波动度 | 20% | 标准差 20-60 | 理想=20, 次理想=14, 其他=6 |
| 气口类型多样性 | 15% | ≥4种类型 | 4种=15, 3种=12, 2种=8, 1种=4 |
| 长句控制 | 10% | 长句有换气点 | 覆盖率×10 |

评分等级：
- ≥80：🟢 优秀（可直接使用）
- 50-79：🟡 待优化
- <50：🔴 需重构

## 4. 数据结构

### 4.1 BreathPoint

```python
@dataclass
class BreathPoint:
    position: int                 # 在原文中的字符位置
    breath_type: str              # natural/emphasis/emotion/breathing
    duration_estimate: float      # 预估停顿时长（秒）
    context_before: str = ""      # 气口前的文本
    context_after: str = ""       # 气口后的文本
    reason: str = ""              # 气口原因
    confidence: float = 1.0       # 置信度（0-1）
```

### 4.2 SpeedSegment

```python
@dataclass
class SpeedSegment:
    text: str                     # 段落文本
    char_count: int               # 字数
    start_time: float = 0.0       # 起始时间（秒）
    end_time: float = 0.0         # 结束时间（秒）
    wpm: float = 0.0              # 语速（字/分钟）
    speed_level: str = "normal"   # 语速等级
    speed_change: str = None      # accelerating/decelerating/steady
```

### 4.3 PacingResult

```python
@dataclass
class PacingResult:
    script_text: str = ""
    breath_points: list = []      # list[BreathPoint]
    speed_analysis: SpeedAnalysis = None
    total_duration_estimate: float = 0.0
    pacing_score: float = 0.0     # 0-100
    pacing_issues: list = []      # 节奏问题列表
    recommendations: list = []    # 优化建议列表
    mode: str = "text"            # text/audio
```

## 5. 分析模式

### 5.1 文本模式（默认）

仅传入文稿文本，基于文本特征（标点、句长、语义）估算气口和语速。

```python
result = analyze_pacing("你的文稿内容...")
```

### 5.2 音频模式

传入文稿文本 + word-level timestamps（来自 whisper-timestamped/WhisperX），
使用真实时间戳计算语速。

```python
# segments 来自 whisper-timestamped 或 WhisperX 的 forced alignment
segments = [
    {"start": 0.0, "end": 0.5, "text": "你好"},
    {"start": 0.5, "end": 1.2, "text": "世界"},
]
result = analyze_pacing("你好世界", segments=segments)
```

## 6. 与其他 Skill 的协同

### 6.1 与 yang-polish 的协同

| 维度 | pacing_analyzer | yang-polish |
|------|----------------|-------------|
| 关注点 | 物理节奏（气口/语速） | 语言肌理（去AI味/口语化） |
| 输入 | 文稿文本（+可选音频时间戳） | 文稿文本 + 诊断报告 + 人设档案 |
| 输出 | 气口标注 + 语速分析 + 节奏建议 | 润色后文稿 + 改动清单 |
| 冲突点 | 无 | 无 |

**协同流程**：
1. 先运行 pacing_analyzer 获取节奏分析
2. 节奏问题（如长句无换气、语速过快）作为 yang-polish 的润色参考
3. yang-polish 润色时可参考气口位置调整句式长度
4. 两者不冲突：pacing 关注"念起来顺不顺"，polish 关注"读起来像不像真人"

### 6.2 与 yang-emotion-curve 的协同

| 维度 | pacing_analyzer | yang-emotion-curve |
|------|----------------|-------------------|
| 关注点 | 物理节奏（停顿/语速） | 情绪节奏（情绪曲线） |
| 时间维度 | 词级/句级时间戳 | 段级（10段）情绪值 |
| 输出 | 气口 + 语速 + 节奏评分 | ER-Curve + 节奏分析 + 健康度 |
| 冲突点 | 无 | 无 |

**协同流程**：
1. 物理节奏服务于情绪节奏
2. 情绪高潮处应有对应的语速变化（加速或减速）和气口（强调停顿）
3. 情绪平缓处语速应平稳，气口以自然停顿为主
4. 两者结合形成完整的"节奏分析"：物理节奏是骨架，情绪节奏是血肉

### 6.3 协同无冲突保证

- pacing_analyzer 是只读分析工具，不修改文稿
- 输出为独立的 PacingResult 对象和 Markdown 报告
- 不依赖 .yang-state.json、.yang-persona.md 等状态文件
- 不触发 session 锁机制
- 可在任何阶段独立运行，不影响其他 Skill 的状态

## 7. 技术背景：Forced Alignment

### 7.1 WhisperX

WhisperX 通过 VAD（语音活动检测）+ 音素模型强制对齐，产出词级时间戳：
1. VAD Cut & Merge：将音频切分为约 30 秒的片段
2. Whisper 转录：并行转录各片段
3. 强制对齐：用音素识别模型对齐词级时间戳

### 7.2 whisper-timestamped

whisper-timestamped 基于交叉注意力权重的 DTW（动态时间规整）对齐：
1. 提取 Whisper 解码器的交叉注意力权重
2. 对注意力权重做中值滤波平滑
3. 用 DTW 算法对齐 token 序列与音频帧
4. 将 token 边界聚合为词级时间戳

### 7.3 IndexTTS 2.0

IndexTTS 2.0 的时长控制机制（正向参考）：
1. 时长编码：将目标时长编码为 embedding，注入每层解码器
2. 固定长度模式：精确控制生成 token 数，误差 ≤0.02%
3. 标点控制停顿：通过标点符号控制语音停顿
4. 情理解耦：GRL 实现音色与情绪的独立控制

本模块借鉴 IndexTTS 2.0 的"标点控制停顿"理念，在文本模式下基于标点估算停顿时长。

## 8. 失败模式编码

| 编码 | 名称 | 描述 | 处理 |
|------|------|------|------|
| PACE-E01 | SCRIPT_EMPTY | 文稿为空 | 返回空 PacingResult |
| PACE-E02 | SCRIPT_TOO_SHORT | 文稿过短（<10字） | 仍输出分析，标注"样本不足" |
| PACE-E03 | SEGMENTS_MISMATCH | 音频时间戳与文稿不匹配 | 回退到文本模式 |
| PACE-E04 | ANALYSIS_ERROR | 分析过程异常 | 返回部分结果 + 错误信息 |

## 9. 稳定性等级

★★★★ — 分析逻辑基于文本特征和数学计算，无外部依赖，不会突然失效。
音频模式依赖外部 ASR 工具产出的时间戳，但回退到文本模式后仍可独立运行。
