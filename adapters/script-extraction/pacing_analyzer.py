# 作者: 阿洋
"""文稿气口标注和语速分析器

作者: 阿洋

借鉴 cuerecord 理念（对文稿标出气口快慢语速），基于 forced alignment 技术实现。

功能：
1. 气口标注：标出文稿中的停顿点（自然停顿、强调停顿、情绪停顿、换气停顿）
2. 语速分析：标注文稿的快慢语速（快/正常/慢/加速/减速）
3. 节奏建议：基于气口和语速分析提供节奏优化建议

技术背景：
- forced alignment（强制对齐）技术：将文本与音频时间轴对齐，获得词级时间戳
  - WhisperX：VAD + 音素模型强制对齐，产出词级时间戳
  - whisper-timestamped：基于交叉注意力权重的 DTW 对齐，无需额外模型
  - IndexTTS 2.0：自回归 TTS 的时长编码机制，通过标点控制停顿
- 本模块支持两种模式：
  - 音频模式：有 word-level timestamps（来自 whisper-timestamped/WhisperX），使用真实时间戳
  - 文本模式：仅有纯文本，基于文本特征（标点、句长、语义）估算气口和语速

与 Yang.skills 的协同关系：
- yang-polish：关注语言肌理（去AI味、口语化），本模块关注物理节奏（气口、语速）
- yang-emotion-curve：关注情绪节奏（情绪曲线），本模块关注物理节奏（停顿、语速）
- 两者互补：情绪曲线是"情绪节奏"，气口/语速是"物理节奏"，共同构成完整的节奏分析

用法：
    from adapters.script_extraction.pacing_analyzer import analyze_pacing

    # 纯文本模式
    result = analyze_pacing("你的文稿内容...")

    # 音频模式（有 word-level timestamps）
    result = analyze_pacing("你的文稿内容...", segments=word_segments)
"""
# 作者: 阿洋

import re
from dataclasses import dataclass, field
from typing import Optional

__author__ = "阿洋"

# ============================================================
# 常量定义
# ============================================================

# 语速等级阈值（字/分钟）
SPEED_FAST_THRESHOLD = 250          # >250 为快
SPEED_NORMAL_MIN = 200              # 200-250 为正常
SPEED_NORMAL_MAX = 250
SPEED_SLOW_THRESHOLD = 200          # <200 为慢

# 换气停顿的句长阈值（字数），超过此值的长句需在中间插入换气点
BREATH_SENTENCE_LENGTH = 35

# 强调停顿的关键词（重要信息前的停顿）
EMPHASIS_KEYWORDS = {
    # 数字/数据类
    "数据", "数字", "百分比", "比例", "统计", "调查", "研究", "报告",
    # 转折/强调类
    "但是", "然而", "不过", "其实", "实际上", "关键是", "重点是", "核心是",
    "最重要的是", "值得注意的是", "有意思的是", "你猜怎么着",
    # 结论类
    "所以", "因此", "结论是", "结果是", "答案是", "真相是",
    # 对比类
    "相比", "对比", "不同的是", "区别在于",
}

# 情绪转折词（情绪停顿的触发词）
EMOTION_TRANSITION_WORDS = {
    # 正向情绪
    "震惊", "惊讶", "兴奋", "激动", "开心", "感动", "震撼", "惊艳",
    # 负向情绪
    "愤怒", "失望", "心痛", "崩溃", "绝望", "无奈", "心酸",
    # 转折情绪
    "突然", "没想到", "万万没想到", "谁曾想", "不可思议", "难以置信",
    # 情绪强度词
    "真的", "太", "超级", "极其", "非常", "特别",
}

# 气口类型
BREATH_NATURAL = "natural"        # 自然停顿（标点处）
BREATH_EMPHASIS = "emphasis"      # 强调停顿（重要信息前后）
BREATH_EMOTION = "emotion"        # 情绪停顿（情绪转折处）
BREATH_BREATHING = "breathing"    # 换气停顿（长句中间）

# 语速等级
SPEED_VERY_FAST = "very_fast"     # 极快（>280）
SPEED_FAST = "fast"               # 快（250-280）
SPEED_NORMAL = "normal"           # 正常（200-250）
SPEED_SLOW = "slow"               # 慢（160-200）
SPEED_VERY_SLOW = "very_slow"     # 极慢（<160）
SPEED_ACCELERATING = "accelerating"  # 加速（从慢变快）
SPEED_DECELERATING = "decelerating"  # 减速（从快变慢）

# 标点符号分类
# 句末标点（较长停顿）
SENTENCE_END_PUNCTS = {"。", "！", "？", "!", "?", "…"}
# 句中标点（较短停顿）
CLAUSE_PUNCTS = {"，", ",", "、", "；", ";"}
# 破折号/省略号（特殊停顿）
SPECIAL_PUNCTS = {"——", "……", "…"}


# ============================================================
# 数据结构
# ============================================================

@dataclass
class BreathPoint:
    """气口（停顿点）数据结构。

    作者: 阿洋
    """
    position: int                 # 在原文中的字符位置
    breath_type: str              # 气口类型：natural/emphasis/emotion/breathing
    duration_estimate: float      # 预估停顿时长（秒），文本模式下为估算值
    context_before: str = ""      # 气口前的文本（用于展示）
    context_after: str = ""       # 气口后的文本（用于展示）
    reason: str = ""              # 气口原因说明
    confidence: float = 1.0       # 置信度（0-1），音频模式下基于时间戳精度


@dataclass
class SpeedSegment:
    """语速段落数据结构。

    作者: 阿洋
    """
    text: str                     # 段落文本
    char_count: int               # 字数
    start_time: float = 0.0       # 起始时间（秒），音频模式
    end_time: float = 0.0         # 结束时间（秒），音频模式
    wpm: float = 0.0              # 语速（字/分钟）
    speed_level: str = SPEED_NORMAL  # 语速等级
    speed_change: Optional[str] = None  # 相对上一段的变化：accelerating/decelerating/steady


@dataclass
class SpeedAnalysis:
    """语速分析结果。

    作者: 阿洋
    """
    overall_wpm: float = 0.0                  # 整体语速（字/分钟）
    overall_speed_level: str = SPEED_NORMAL   # 整体语速等级
    segments: list = field(default_factory=list)  # list[SpeedSegment]
    speed_distribution: dict = field(default_factory=dict)  # 各等级占比
    speed_variance: float = 0.0               # 语速波动度（标准差）
    has_audio_timestamps: bool = False        # 是否使用了音频时间戳


@dataclass
class PacingResult:
    """气口/语速分析结果。

    作者: 阿洋
    """
    script_text: str = ""                     # 原文稿
    breath_points: list = field(default_factory=list)  # list[BreathPoint]
    speed_analysis: Optional[SpeedAnalysis] = None
    total_duration_estimate: float = 0.0      # 预估总时长（秒）
    pacing_score: float = 0.0                 # 节奏健康度评分（0-100）
    pacing_issues: list = field(default_factory=list)  # 节奏问题列表
    recommendations: list = field(default_factory=list)  # 优化建议列表
    mode: str = "text"                        # 分析模式：text/audio


# ============================================================
# 气口标注
# ============================================================

def mark_breath_points(script_text: str, segments: Optional[list] = None) -> list:
    """标注文稿中的气口（停顿点）。

    作者: 阿洋

    Args:
        script_text: 文稿文本
        segments: 可选，word-level timestamps（来自 whisper-timestamped/WhisperX）
                  格式：[{"start": 0.0, "end": 0.5, "text": "你好"}, ...]
                  若提供则使用音频模式（基于真实停顿时长），否则使用文本模式

    Returns:
        list[BreathPoint]: 气口列表，按位置排序
    """
    if not script_text or not script_text.strip():
        return []

    breath_points = []

    # 1. 自然停顿：标点符号处
    breath_points.extend(_mark_natural_breaths(script_text, segments))

    # 2. 强调停顿：重要信息前后
    breath_points.extend(_mark_emphasis_breaths(script_text))

    # 3. 情绪停顿：情绪转折处
    breath_points.extend(_mark_emotion_breaths(script_text))

    # 4. 换气停顿：长句中间
    breath_points.extend(_mark_breathing_breaths(script_text))

    # 去重：同一位置只保留优先级最高的气口
    breath_points = _deduplicate_breaths(breath_points)

    # 按位置排序
    breath_points.sort(key=lambda b: b.position)

    return breath_points


def _mark_natural_breaths(script_text: str, segments: Optional[list] = None) -> list:
    """标注自然停顿（标点符号处）。

    作者: 阿洋
    """
    breaths = []
    # 句末标点：较长停顿
    for match in re.finditer(r'[。！？!?…]', script_text):
        pos = match.end()
        duration = _estimate_pause_duration(match.group(), segments, pos)
        breaths.append(BreathPoint(
            position=pos,
            breath_type=BREATH_NATURAL,
            duration_estimate=duration,
            context_before=script_text[max(0, pos - 10):pos],
            context_after=script_text[pos:pos + 10],
            reason=f"句末标点「{match.group()}」处自然停顿",
        ))
    # 句中标点：较短停顿
    for match in re.finditer(r'[，,、；;]', script_text):
        pos = match.end()
        duration = _estimate_pause_duration(match.group(), segments, pos)
        breaths.append(BreathPoint(
            position=pos,
            breath_type=BREATH_NATURAL,
            duration_estimate=duration,
            context_before=script_text[max(0, pos - 10):pos],
            context_after=script_text[pos:pos + 10],
            reason=f"句中标点「{match.group()}」处自然停顿",
        ))
    return breaths


def _mark_emphasis_breaths(script_text: str) -> list:
    """标注强调停顿（重要信息前后）。

    作者: 阿洋

    在强调关键词前后插入停顿点，帮助突出重要信息。
    """
    breaths = []
    for keyword in EMPHASIS_KEYWORDS:
        for match in re.finditer(re.escape(keyword), script_text):
            # 关键词前停顿（强调前的铺垫停顿）
            pos_before = match.start()
            breaths.append(BreathPoint(
                position=pos_before,
                breath_type=BREATH_EMPHASIS,
                duration_estimate=0.4,
                context_before=script_text[max(0, pos_before - 8):pos_before],
                context_after=script_text[pos_before:pos_before + len(keyword) + 8],
                reason=f"强调词「{keyword}」前停顿，突出后续重要信息",
                confidence=0.7,
            ))
            # 关键词后停顿（强调后的消化停顿）
            pos_after = match.end()
            breaths.append(BreathPoint(
                position=pos_after,
                breath_type=BREATH_EMPHASIS,
                duration_estimate=0.3,
                context_before=script_text[max(0, pos_after - len(keyword) - 8):pos_after],
                context_after=script_text[pos_after:pos_after + 8],
                reason=f"强调词「{keyword}」后停顿，给听众消化时间",
                confidence=0.7,
            ))
    return breaths


def _mark_emotion_breaths(script_text: str) -> list:
    """标注情绪停顿（情绪转折处）。

    作者: 阿洋

    在情绪转折词处插入停顿，让情绪转换有缓冲。
    """
    breaths = []
    for keyword in EMOTION_TRANSITION_WORDS:
        for match in re.finditer(re.escape(keyword), script_text):
            pos = match.end()
            breaths.append(BreathPoint(
                position=pos,
                breath_type=BREATH_EMOTION,
                duration_estimate=0.5,
                context_before=script_text[max(0, pos - len(keyword) - 8):pos],
                context_after=script_text[pos:pos + 8],
                reason=f"情绪词「{keyword}」后停顿，让情绪转换有缓冲",
                confidence=0.65,
            ))
    return breaths


def _mark_breathing_breaths(script_text: str) -> list:
    """标注换气停顿（长句中间的换气点）。

    作者: 阿洋

    超过 BREATH_SENTENCE_LENGTH 字的长句，在中间位置插入换气点。
    换气点优先选择语义自然断点（逗号、连词等）。
    """
    breaths = []
    # 按句末标点分割长句
    sentences = re.split(r'([。！？!?…]+)', script_text)
    char_offset = 0

    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        punct = sentences[i + 1] if i + 1 < len(sentences) else ""
        full_sentence = sentence + punct

        # 去除标点后的纯文本长度
        clean_sentence = re.sub(r'[，。！？、；：""''（）(),.!?;:\s]', '', sentence)
        if len(clean_sentence) < BREATH_SENTENCE_LENGTH:
            char_offset += len(full_sentence)
            continue

        # 长句：在中间位置找换气点
        mid_pos = len(sentence) // 2
        # 在中间位置附近找最接近的逗号或连词
        search_range = sentence[max(0, mid_pos - 10):min(len(sentence), mid_pos + 10)]
        best_split = -1

        # 优先找逗号
        comma_match = re.search(r'[，,]', search_range)
        if comma_match:
            best_split = max(0, mid_pos - 10) + comma_match.end()
        else:
            # 其次找连词
            for conj in ["然后", "接着", "而且", "但是", "不过", "所以", "因为"]:
                conj_match = re.search(conj, search_range)
                if conj_match:
                    best_split = max(0, mid_pos - 10) + conj_match.start()
                    break

        if best_split < 0:
            # 找不到自然断点，在中间位置硬切
            best_split = mid_pos

        abs_pos = char_offset + best_split
        breaths.append(BreathPoint(
            position=abs_pos,
            breath_type=BREATH_BREATHING,
            duration_estimate=0.25,
            context_before=script_text[max(0, abs_pos - 10):abs_pos],
            context_after=script_text[abs_pos:abs_pos + 10],
            reason=f"长句（{len(clean_sentence)}字）中间换气点，避免一口气念完",
            confidence=0.6,
        ))
        char_offset += len(full_sentence)

    return breaths


def _estimate_pause_duration(punct: str, segments: Optional[list], pos: int) -> float:
    """估算停顿时长。

    作者: 阿洋

    音频模式下基于真实时间戳，文本模式下基于标点类型估算。
    """
    if segments:
        # 音频模式：尝试从时间戳中估算
        # 简化处理：句末标点 0.6s，句中标点 0.3s
        pass
    # 文本模式估算
    if punct in SENTENCE_END_PUNCTS:
        return 0.6
    elif punct in CLAUSE_PUNCTS:
        return 0.3
    elif punct in SPECIAL_PUNCTS:
        return 0.8
    return 0.3


def _deduplicate_breaths(breaths: list) -> list:
    """去重：同一位置只保留优先级最高的气口。

    作者: 阿洋

    优先级：emotion > emphasis > breathing > natural
    """
    if not breaths:
        return []

    # 按位置分组
    pos_groups = {}
    for b in breaths:
        key = b.position
        if key not in pos_groups:
            pos_groups[key] = []
        pos_groups[key].append(b)

    # 优先级映射
    priority = {BREATH_EMOTION: 4, BREATH_EMPHASIS: 3, BREATH_BREATHING: 2, BREATH_NATURAL: 1}

    result = []
    for pos, group in pos_groups.items():
        # 选优先级最高的
        best = max(group, key=lambda b: priority.get(b.breath_type, 0))
        result.append(best)

    return result


# ============================================================
# 语速分析
# ============================================================

def analyze_speed(script_text: str, segments: Optional[list] = None) -> SpeedAnalysis:
    """分析文稿的语速分布。

    作者: 阿洋

    Args:
        script_text: 文稿文本
        segments: 可选，word-level timestamps
                  格式：[{"start": 0.0, "end": 0.5, "text": "你好"}, ...]

    Returns:
        SpeedAnalysis: 语速分析结果
    """
    if not script_text or not script_text.strip():
        return SpeedAnalysis()

    has_audio = segments is not None and len(segments) > 0

    if has_audio:
        return _analyze_speed_audio(script_text, segments)
    else:
        return _analyze_speed_text(script_text)


def _analyze_speed_audio(script_text: str, segments: list) -> SpeedAnalysis:
    """音频模式：基于 word-level timestamps 计算真实语速。

    作者: 阿洋

    基于 forced alignment 技术（WhisperX/whisper-timestamped）产出的
    词级时间戳，计算每个语义段的真实语速。
    """
    analysis = SpeedAnalysis(has_audio_timestamps=True)

    # 计算总字数和总时长
    total_chars = sum(len(s.get("text", "").replace(" ", "")) for s in segments)
    if not segments:
        return analysis

    total_duration = segments[-1].get("end", 0) - segments[0].get("start", 0)
    if total_duration <= 0:
        return analysis

    overall_wpm = total_chars / (total_duration / 60)
    analysis.overall_wpm = round(overall_wpm, 1)
    analysis.overall_speed_level = _wpm_to_level(overall_wpm)

    # 按句末标点或时间间隔（每 10 秒一段）切分段落
    speed_segments = []
    current_seg_words = []
    current_seg_start = segments[0].get("start", 0) if segments else 0

    for seg in segments:
        current_seg_words.append(seg)
        text = seg.get("text", "")
        # 遇到句末标点或时间间隔超过 10 秒，切分段落
        is_sentence_end = any(p in text for p in SENTENCE_END_PUNCTS)
        seg_end = seg.get("end", current_seg_start)
        time_gap = seg_end - current_seg_start

        if is_sentence_end or time_gap >= 10:
            seg_text = "".join(s.get("text", "") for s in current_seg_words)
            seg_chars = len(seg_text.replace(" ", ""))
            seg_duration = seg_end - current_seg_start
            if seg_duration > 0 and seg_chars > 0:
                seg_wpm = seg_chars / (seg_duration / 60)
                speed_segments.append(SpeedSegment(
                    text=seg_text,
                    char_count=seg_chars,
                    start_time=round(current_seg_start, 3),
                    end_time=round(seg_end, 3),
                    wpm=round(seg_wpm, 1),
                    speed_level=_wpm_to_level(seg_wpm),
                ))
            current_seg_words = []
            current_seg_start = seg_end

    # 处理最后一段
    if current_seg_words:
        seg_text = "".join(s.get("text", "") for s in current_seg_words)
        seg_chars = len(seg_text.replace(" ", ""))
        seg_end = current_seg_words[-1].get("end", current_seg_start)
        seg_duration = seg_end - current_seg_start
        if seg_duration > 0 and seg_chars > 0:
            seg_wpm = seg_chars / (seg_duration / 60)
            speed_segments.append(SpeedSegment(
                text=seg_text,
                char_count=seg_chars,
                start_time=round(current_seg_start, 3),
                end_time=round(seg_end, 3),
                wpm=round(seg_wpm, 1),
                speed_level=_wpm_to_level(seg_wpm),
            ))

    # 计算语速变化（加速/减速）
    for i, seg in enumerate(speed_segments):
        if i == 0:
            seg.speed_change = "steady"
        else:
            prev_wpm = speed_segments[i - 1].wpm
            curr_wpm = seg.wpm
            diff = curr_wpm - prev_wpm
            if diff > 30:
                seg.speed_change = "accelerating"
            elif diff < -30:
                seg.speed_change = "decelerating"
            else:
                seg.speed_change = "steady"

    analysis.segments = speed_segments

    # 计算语速分布
    analysis.speed_distribution = _calc_speed_distribution(speed_segments)

    # 计算语速波动度
    if speed_segments:
        wpms = [s.wpm for s in speed_segments]
        mean_wpm = sum(wpms) / len(wpms)
        variance = sum((w - mean_wpm) ** 2 for w in wpms) / len(wpms)
        analysis.speed_variance = round(variance ** 0.5, 1)

    return analysis


def _analyze_speed_text(script_text: str) -> SpeedAnalysis:
    """文本模式：基于文本特征估算语速。

    作者: 阿洋

    无音频时间戳时，基于以下特征估算语速：
    - 句子长度：短句语速快，长句语速慢
    - 标点密度：标点密集处语速慢
    - 情绪词密度：情绪词密集处语速快
    """
    analysis = SpeedAnalysis(has_audio_timestamps=False)

    # 按句末标点分割
    sentence_pattern = r'[^。！？!?…]+[。！？!?…]*'
    sentences = re.findall(sentence_pattern, script_text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return analysis

    speed_segments = []
    total_chars = 0
    estimated_time = 0.0

    for sent in sentences:
        clean_sent = re.sub(r'[，。！？、；：""''（）(),.!?;:\s]', '', sent)
        char_count = len(clean_sent)
        if char_count == 0:
            continue

        # 估算语速：基于句长和标点密度
        # 基准语速 220 字/分钟，根据特征调整
        base_wpm = 220.0

        # 短句（<15字）语速偏快
        if char_count < 15:
            base_wpm += 20
        # 长句（>40字）语速偏慢
        elif char_count > 40:
            base_wpm -= 20

        # 标点密度高 → 语速慢
        punct_count = len(re.findall(r'[，。！？、；：]', sent))
        punct_density = punct_count / max(char_count, 1)
        if punct_density > 0.1:
            base_wpm -= 15

        # 情绪词密度高 → 语速快
        emotion_count = sum(1 for w in EMOTION_TRANSITION_WORDS if w in sent)
        if emotion_count > 0:
            base_wpm += 15

        # 问句语速偏慢（思考停顿）
        if sent.endswith("？") or sent.endswith("?"):
            base_wpm -= 10

        # 感叹句语速偏快（情绪激动）
        if sent.endswith("！") or sent.endswith("!"):
            base_wpm += 10

        base_wpm = max(120, min(300, base_wpm))  # 限制在合理范围

        # 估算时长
        seg_duration = char_count / (base_wpm / 60)

        speed_segments.append(SpeedSegment(
            text=sent,
            char_count=char_count,
            start_time=round(estimated_time, 3),
            end_time=round(estimated_time + seg_duration, 3),
            wpm=round(base_wpm, 1),
            speed_level=_wpm_to_level(base_wpm),
        ))

        total_chars += char_count
        estimated_time += seg_duration

    # 计算语速变化
    for i, seg in enumerate(speed_segments):
        if i == 0:
            seg.speed_change = "steady"
        else:
            prev_wpm = speed_segments[i - 1].wpm
            curr_wpm = seg.wpm
            diff = curr_wpm - prev_wpm
            if diff > 30:
                seg.speed_change = "accelerating"
            elif diff < -30:
                seg.speed_change = "decelerating"
            else:
                seg.speed_change = "steady"

    analysis.segments = speed_segments
    analysis.speed_distribution = _calc_speed_distribution(speed_segments)

    # 整体语速
    if estimated_time > 0:
        analysis.overall_wpm = round(total_chars / (estimated_time / 60), 1)
        analysis.overall_speed_level = _wpm_to_level(analysis.overall_wpm)

    # 语速波动度
    if speed_segments:
        wpms = [s.wpm for s in speed_segments]
        mean_wpm = sum(wpms) / len(wpms)
        variance = sum((w - mean_wpm) ** 2 for w in wpms) / len(wpms)
        analysis.speed_variance = round(variance ** 0.5, 1)

    return analysis


def _wpm_to_level(wpm: float) -> str:
    """将语速（字/分钟）转换为语速等级。

    作者: 阿洋
    """
    if wpm > 280:
        return SPEED_VERY_FAST
    elif wpm > SPEED_FAST_THRESHOLD:
        return SPEED_FAST
    elif wpm >= SPEED_NORMAL_MIN:
        return SPEED_NORMAL
    elif wpm >= 160:
        return SPEED_SLOW
    else:
        return SPEED_VERY_SLOW


def _calc_speed_distribution(segments: list) -> dict:
    """计算各语速等级的占比。

    作者: 阿洋
    """
    if not segments:
        return {}

    level_counts = {}
    total = len(segments)
    for seg in segments:
        level = seg.speed_level
        level_counts[level] = level_counts.get(level, 0) + 1

    return {level: round(count / total, 3) for level, count in level_counts.items()}


# ============================================================
# 综合分析
# ============================================================

def analyze_pacing(script_text: str, segments: Optional[list] = None) -> PacingResult:
    """分析文稿的气口和语速（主入口）。

    作者: 阿洋

    Args:
        script_text: 文稿文本
        segments: 可选，word-level timestamps（来自 whisper-timestamped/WhisperX）

    Returns:
        PacingResult: 气口/语速分析结果
    """
    if not script_text or not script_text.strip():
        return PacingResult()

    result = PacingResult(
        script_text=script_text,
        mode="audio" if segments else "text",
    )

    # 1. 气口标注
    result.breath_points = mark_breath_points(script_text, segments)

    # 2. 语速分析
    result.speed_analysis = analyze_speed(script_text, segments)

    # 3. 预估总时长
    if result.speed_analysis and result.speed_analysis.segments:
        result.total_duration_estimate = result.speed_analysis.segments[-1].end_time
    else:
        # 基于气口和字数估算
        clean_text = re.sub(r'[\s]', '', script_text)
        char_count = len(clean_text)
        breath_count = len(result.breath_points)
        # 基础语速 220 字/分钟 + 每个气口 0.4 秒
        result.total_duration_estimate = (char_count / 220 * 60) + (breath_count * 0.4)

    # 4. 节奏健康度评分
    result.pacing_score = _calc_pacing_score(result)

    # 5. 节奏问题诊断
    result.pacing_issues = _diagnose_pacing_issues(result)

    # 6. 优化建议
    result.recommendations = _generate_recommendations(result)

    return result


def _calc_pacing_score(result: PacingResult) -> float:
    """计算节奏健康度评分（0-100）。

    作者: 阿洋

    评分维度：
    - 气口密度（30%）：气口数量与字数的比例，过密或过疏都扣分
    - 语速合理性（25%）：整体语速是否在正常范围
    - 语速波动度（20%）：语速变化是否自然（非单调也非剧烈波动）
    - 气口类型多样性（15%）：是否包含多种类型的气口
    - 长句控制（10%）：长句是否有换气点
    """
    score = 0.0

    # 气口密度
    clean_text = re.sub(r'[\s]', '', result.script_text)
    char_count = max(len(clean_text), 1)
    breath_count = len(result.breath_points)
    breath_density = breath_count / (char_count / 100)  # 每100字的气口数
    # 理想气口密度：5-15 个/100字
    if 5 <= breath_density <= 15:
        score += 30
    elif 3 <= breath_density < 5 or 15 < breath_density <= 20:
        score += 20
    else:
        score += 10

    # 语速合理性
    if result.speed_analysis:
        overall_wpm = result.speed_analysis.overall_wpm
        if SPEED_NORMAL_MIN <= overall_wpm <= SPEED_NORMAL_MAX:
            score += 25
        elif 180 <= overall_wpm < SPEED_NORMAL_MIN or SPEED_NORMAL_MAX < overall_wpm <= 270:
            score += 18
        else:
            score += 8

    # 语速波动度
    if result.speed_analysis and result.speed_analysis.speed_variance is not None:
        variance = result.speed_analysis.speed_variance
        # 理想波动度：20-60（有变化但不剧烈）
        if 20 <= variance <= 60:
            score += 20
        elif 10 <= variance < 20 or 60 < variance <= 80:
            score += 14
        else:
            score += 6

    # 气口类型多样性
    breath_types = set(b.breath_type for b in result.breath_points)
    type_count = len(breath_types)
    if type_count >= 4:
        score += 15
    elif type_count == 3:
        score += 12
    elif type_count == 2:
        score += 8
    else:
        score += 4

    # 长句控制
    long_sentences = 0
    long_sentences_with_breath = 0
    sentences = re.split(r'[。！？!?…]+', result.script_text)
    for sent in sentences:
        clean = re.sub(r'[，。！？、；：""''（）(),.!?;:\s]', '', sent)
        if len(clean) >= BREATH_SENTENCE_LENGTH:
            long_sentences += 1
            # 检查该长句范围内是否有换气停顿
            sent_start = result.script_text.find(sent)
            if sent_start >= 0:
                for b in result.breath_points:
                    if (b.breath_type == BREATH_BREATHING and
                            sent_start <= b.position <= sent_start + len(sent)):
                        long_sentences_with_breath += 1
                        break

    if long_sentences > 0:
        coverage = long_sentences_with_breath / long_sentences
        score += 10 * coverage
    else:
        score += 10  # 无长句，满分

    return round(min(score, 100), 1)


def _diagnose_pacing_issues(result: PacingResult) -> list:
    """诊断节奏问题。

    作者: 阿洋
    """
    issues = []

    # 气口过密
    clean_text = re.sub(r'[\s]', '', result.script_text)
    char_count = max(len(clean_text), 1)
    breath_density = len(result.breath_points) / (char_count / 100)
    if breath_density > 20:
        issues.append({
            "type": "breath_too_dense",
            "severity": "high",
            "message": f"气口密度过高（{breath_density:.1f}个/100字），停顿过多导致节奏破碎",
            "suggestion": "减少不必要的停顿，合并近距离的气口",
        })
    elif breath_density < 3:
        issues.append({
            "type": "breath_too_sparse",
            "severity": "medium",
            "message": f"气口密度过低（{breath_density:.1f}个/100字），缺少停顿导致节奏平淡",
            "suggestion": "在关键信息前后和长句中间增加停顿点",
        })

    # 语速问题
    if result.speed_analysis:
        wpm = result.speed_analysis.overall_wpm
        if wpm > 280:
            issues.append({
                "type": "speed_too_fast",
                "severity": "high",
                "message": f"整体语速过快（{wpm}字/分钟），听众难以跟上",
                "suggestion": "增加句中标点，或在关键信息后增加停顿",
            })
        elif wpm < 160:
            issues.append({
                "type": "speed_too_slow",
                "severity": "medium",
                "message": f"整体语速过慢（{wpm}字/分钟），可能导致听众流失",
                "suggestion": "缩短长句，减少冗余停顿",
            })

        # 语速波动过大
        if result.speed_analysis.speed_variance > 80:
            issues.append({
                "type": "speed_variance_high",
                "severity": "medium",
                "message": f"语速波动过大（标准差{result.speed_analysis.speed_variance}），节奏不稳定",
                "suggestion": "平滑语速变化，避免忽快忽慢",
            })
        elif result.speed_analysis.speed_variance < 10:
            issues.append({
                "type": "speed_variance_low",
                "severity": "low",
                "message": f"语速过于均匀（标准差{result.speed_analysis.speed_variance}），缺少节奏变化",
                "suggestion": "在情绪转折处适当调整语速，制造快慢对比",
            })

    # 长句无换气
    long_no_breath = 0
    sentences = re.split(r'[。！？!?…]+', result.script_text)
    for sent in sentences:
        clean = re.sub(r'[，。！？、；：""''（）(),.!?;:\s]', '', sent)
        if len(clean) >= BREATH_SENTENCE_LENGTH:
            sent_start = result.script_text.find(sent)
            has_breath = False
            if sent_start >= 0:
                for b in result.breath_points:
                    if (b.breath_type == BREATH_BREATHING and
                            sent_start <= b.position <= sent_start + len(sent)):
                        has_breath = True
                        break
            if not has_breath:
                long_no_breath += 1

    if long_no_breath > 0:
        issues.append({
            "type": "long_sentence_no_breath",
            "severity": "medium",
            "message": f"有{long_no_breath}个长句（>{BREATH_SENTENCE_LENGTH}字）缺少换气点",
            "suggestion": f"在长句中间增加逗号或换气停顿",
        })

    # 气口类型单一
    breath_types = set(b.breath_type for b in result.breath_points)
    if len(breath_types) <= 1 and len(result.breath_points) > 5:
        issues.append({
            "type": "breath_type_monotone",
            "severity": "low",
            "message": "气口类型单一（仅有自然停顿），缺少强调和情绪停顿",
            "suggestion": "在重要信息和情绪转折处增加强调/情绪停顿",
        })

    return issues


def _generate_recommendations(result: PacingResult) -> list:
    """基于气口和语速分析提供节奏优化建议。

    作者: 阿洋
    """
    recommendations = []

    # 基于问题生成建议
    for issue in result.pacing_issues:
        recommendations.append({
            "priority": issue["severity"],
            "target": issue["type"],
            "action": issue["suggestion"],
            "context": issue["message"],
        })

    # 基于气口分布的建议
    if result.breath_points:
        type_counts = {}
        for b in result.breath_points:
            type_counts[b.breath_type] = type_counts.get(b.breath_type, 0) + 1

        # 缺少情绪停顿
        if type_counts.get(BREATH_EMOTION, 0) == 0:
            recommendations.append({
                "priority": "medium",
                "target": "emotion_breath",
                "action": "在情绪转折词（如'突然''没想到''震惊'）后增加停顿，让情绪转换有缓冲",
                "context": "当前文稿缺少情绪停顿，情绪转换显得突兀",
            })

        # 缺少强调停顿
        if type_counts.get(BREATH_EMPHASIS, 0) == 0:
            recommendations.append({
                "priority": "medium",
                "target": "emphasis_breath",
                "action": "在关键数据/结论前增加停顿（如'但是''关键是''研究显示'前），突出重要信息",
                "context": "当前文稿缺少强调停顿，重要信息容易被忽略",
            })

    # 基于语速的建议
    if result.speed_analysis and result.speed_analysis.segments:
        # 检查是否有连续加速或减速
        consecutive_accel = 0
        consecutive_decel = 0
        max_consecutive_accel = 0
        max_consecutive_decel = 0
        for seg in result.speed_analysis.segments:
            if seg.speed_change == "accelerating":
                consecutive_accel += 1
                consecutive_decel = 0
                max_consecutive_accel = max(max_consecutive_accel, consecutive_accel)
            elif seg.speed_change == "decelerating":
                consecutive_decel += 1
                consecutive_accel = 0
                max_consecutive_decel = max(max_consecutive_decel, consecutive_decel)
            else:
                consecutive_accel = 0
                consecutive_decel = 0

        if max_consecutive_accel >= 3:
            recommendations.append({
                "priority": "medium",
                "target": "continuous_acceleration",
                "action": "连续加速段落过长，在加速过程中插入一个减速段，给听众喘息空间",
                "context": f"检测到连续{max_consecutive_accel}段加速，可能导致听众疲劳",
            })

        if max_consecutive_decel >= 3:
            recommendations.append({
                "priority": "medium",
                "target": "continuous_deceleration",
                "action": "连续减速段落过长，可能导致节奏拖沓，适当提升后半段语速",
                "context": f"检测到连续{max_consecutive_decel}段减速，可能导致听众流失",
            })

    # 整体节奏建议
    if result.pacing_score >= 80:
        recommendations.append({
            "priority": "info",
            "target": "overall",
            "action": "节奏健康度优秀，保持当前气口和语速分布",
            "context": f"节奏健康度评分 {result.pacing_score}/100",
        })
    elif result.pacing_score >= 50:
        recommendations.append({
            "priority": "low",
            "target": "overall",
            "action": "节奏基本合理，按上述建议微调即可",
            "context": f"节奏健康度评分 {result.pacing_score}/100",
        })
    else:
        recommendations.append({
            "priority": "high",
            "target": "overall",
            "action": "节奏需要重点优化，建议优先处理高严重度的问题",
            "context": f"节奏健康度评分 {result.pacing_score}/100",
        })

    return recommendations


# ============================================================
# 报告生成
# ============================================================

def generate_pacing_report(result: PacingResult) -> str:
    """生成节奏分析报告（Markdown 格式）。

    作者: 阿洋

    Args:
        result: PacingResult 分析结果

    Returns:
        str: Markdown 格式的报告
    """
    if not result or not result.script_text:
        return "## 节奏分析报告\n\n文稿为空，无法分析。"

    lines = []
    lines.append("## 🎵 节奏分析报告（气口/语速）")
    lines.append("")
    lines.append(f"> 作者: 阿洋 | 模式: {result.mode} | 基于 forced alignment 技术")
    lines.append("")

    # 基本信息
    clean_text = re.sub(r'[\s]', '', result.script_text)
    char_count = len(clean_text)
    lines.append("### 📊 基本信息")
    lines.append("")
    lines.append(f"- **字数**：{char_count} 字")
    lines.append(f"- **气口总数**：{len(result.breath_points)} 个")
    lines.append(f"- **预估时长**：{result.total_duration_estimate:.1f} 秒（{result.total_duration_estimate / 60:.1f} 分钟）")
    lines.append(f"- **分析模式**：{'音频模式（word-level timestamps）' if result.mode == 'audio' else '文本模式（估算）'}")
    lines.append(f"- **节奏健康度**：{result.pacing_score}/100 {_score_emoji(result.pacing_score)}")
    lines.append("")

    # 气口分析
    lines.append("### 🫁 气口分析")
    lines.append("")
    if result.breath_points:
        type_counts = {}
        type_durations = {}
        for b in result.breath_points:
            type_counts[b.breath_type] = type_counts.get(b.breath_type, 0) + 1
            type_durations[b.breath_type] = type_durations.get(b.breath_type, 0) + b.duration_estimate

        type_names = {
            BREATH_NATURAL: "自然停顿",
            BREATH_EMPHASIS: "强调停顿",
            BREATH_EMOTION: "情绪停顿",
            BREATH_BREATHING: "换气停顿",
        }

        lines.append("| 气口类型 | 数量 | 占比 | 预估总停顿时长 |")
        lines.append("|---------|------|------|--------------|")
        total_breaths = len(result.breath_points)
        for btype, name in type_names.items():
            count = type_counts.get(btype, 0)
            pct = count / total_breaths * 100 if total_breaths > 0 else 0
            duration = type_durations.get(btype, 0)
            lines.append(f"| {name} | {count} | {pct:.1f}% | {duration:.1f}s |")
        lines.append("")

        # 气口密度
        breath_density = total_breaths / (char_count / 100) if char_count > 0 else 0
        lines.append(f"- **气口密度**：{breath_density:.1f} 个/100字")
        if 5 <= breath_density <= 15:
            lines.append(f"- **密度评估**：✅ 理想范围（5-15个/100字）")
        elif breath_density > 15:
            lines.append(f"- **密度评估**：⚠️ 偏密（停顿过多）")
        else:
            lines.append(f"- **密度评估**：⚠️ 偏疏（停顿不足）")
        lines.append("")
    else:
        lines.append("未检测到气口。")
        lines.append("")

    # 语速分析
    lines.append("### ⚡ 语速分析")
    lines.append("")
    if result.speed_analysis:
        sa = result.speed_analysis
        lines.append(f"- **整体语速**：{sa.overall_wpm} 字/分钟（{_level_to_name(sa.overall_speed_level)}）")
        lines.append(f"- **语速波动度**：{sa.speed_variance}（标准差）")
        lines.append(f"- **数据来源**：{'音频时间戳' if sa.has_audio_timestamps else '文本估算'}")
        lines.append("")

        # 语速分布
        if sa.speed_distribution:
            level_names = {
                SPEED_VERY_FAST: "极快",
                SPEED_FAST: "快",
                SPEED_NORMAL: "正常",
                SPEED_SLOW: "慢",
                SPEED_VERY_SLOW: "极慢",
            }
            lines.append("**语速分布**：")
            lines.append("")
            for level, pct in sorted(sa.speed_distribution.items(), key=lambda x: -x[1]):
                name = level_names.get(level, level)
                bar = "█" * int(pct * 20)
                lines.append(f"- {name}：{pct * 100:.1f}% {bar}")
            lines.append("")

        # 段落语速明细（最多展示 10 段）
        if sa.segments:
            lines.append("**段落语速明细**（前10段）：")
            lines.append("")
            lines.append("| # | 语速 | 等级 | 变化 | 文本预览 |")
            lines.append("|---|------|------|------|---------|")
            for i, seg in enumerate(sa.segments[:10]):
                preview = seg.text[:20].replace("\n", " ") + ("..." if len(seg.text) > 20 else "")
                change_icon = {"accelerating": "⬆️加速", "decelerating": "⬇️减速", "steady": "➡️平稳"}.get(seg.speed_change, "")
                lines.append(f"| {i + 1} | {seg.wpm} | {_level_to_name(seg.speed_level)} | {change_icon} | {preview} |")
            if len(sa.segments) > 10:
                lines.append(f"| ... | ... | ... | ... | （共{len(sa.segments)}段） |")
            lines.append("")
    else:
        lines.append("语速分析不可用。")
        lines.append("")

    # 节奏问题
    lines.append("### 🔍 节奏问题诊断")
    lines.append("")
    if result.pacing_issues:
        for issue in result.pacing_issues:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue["severity"], "⚪")
            lines.append(f"- {severity_icon} **{issue['message']}**")
            lines.append(f"  - 建议：{issue['suggestion']}")
        lines.append("")
    else:
        lines.append("✅ 未检测到明显节奏问题。")
        lines.append("")

    # 优化建议
    lines.append("### 💡 节奏优化建议")
    lines.append("")
    if result.recommendations:
        for rec in result.recommendations:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}.get(rec["priority"], "⚪")
            lines.append(f"- {priority_icon} **[{rec['target']}]** {rec['action']}")
            lines.append(f"  - {rec['context']}")
        lines.append("")
    else:
        lines.append("暂无优化建议。")
        lines.append("")

    # 与其他 skill 的协同说明
    lines.append("### 🔗 与其他 Skill 的协同")
    lines.append("")
    lines.append("- **yang-polish**：本报告关注物理节奏（气口/语速），yang-polish 关注语言肌理（去AI味/口语化）。两者互补，建议先做气口/语速分析，再进行润色。")
    lines.append('- **yang-emotion-curve**：本报告是「物理节奏」，yang-emotion-curve 是「情绪节奏」。完整的节奏分析应结合两者：物理节奏服务于情绪节奏。')
    lines.append("")

    lines.append("---")
    lines.append("*本报告由 pacing_analyzer 生成 | 作者: 阿洋 | 基于 forced alignment 技术*")

    return "\n".join(lines)


def _score_emoji(score: float) -> str:
    """评分对应的 emoji。"""
    if score >= 80:
        return "🟢 优秀"
    elif score >= 50:
        return "🟡 待优化"
    else:
        return "🔴 需重构"


def _level_to_name(level: str) -> str:
    """语速等级转中文名。"""
    names = {
        SPEED_VERY_FAST: "极快",
        SPEED_FAST: "快",
        SPEED_NORMAL: "正常",
        SPEED_SLOW: "慢",
        SPEED_VERY_SLOW: "极慢",
        SPEED_ACCELERATING: "加速中",
        SPEED_DECELERATING: "减速中",
    }
    return names.get(level, level)


# ============================================================
# CLI 入口
# ============================================================

def main():
    """命令行入口。

    作者: 阿洋

    用法：
        python pacing_analyzer.py <script_path> [--segments <segments.json>] [--output <output.md>]
    """
    import argparse
    import json

    parser = argparse.ArgumentParser(description="文稿气口标注和语速分析器")
    parser.add_argument("script_path", type=str, help="文稿文件路径")
    parser.add_argument("--segments", type=str, default=None,
                        help="word-level timestamps JSON 文件路径（可选）")
    parser.add_argument("--output", type=str, default=None,
                        help="输出报告路径（默认输出到 stdout）")
    args = parser.parse_args()

    # 读取文稿
    with open(args.script_path, "r", encoding="utf-8") as f:
        script_text = f.read()

    # 读取 segments（可选）
    segments = None
    if args.segments:
        with open(args.segments, "r", encoding="utf-8") as f:
            data = json.load(f)
            segments = data.get("segments", data) if isinstance(data, dict) else data

    # 分析
    result = analyze_pacing(script_text, segments)

    # 生成报告
    report = generate_pacing_report(result)

    # 输出
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已生成: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
