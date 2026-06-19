#!/usr/bin/env python3
# 作者: 阿洋
"""
sentiment_analyzer.py — 情感分析器
作者: 阿洋

基于 cnsenti（中文情感分析库）和 SnowNLP（中文自然语言处理库）理念实现。

==========================================================================
开源项目许可证声明
==========================================================================

1. cnsenti (thunderhit/hidadeng)
   - 项目地址: https://github.com/thunderhit/cnsenti
   - 许可证: MIT License (代码) + 大连理工大学情感本体库学术许可 (情绪词典)
   - 核心理念: 基于知网Hownet情感词典 + 大连理工大学情感本体库，
     支持7种情绪分类（好/乐/哀/怒/惧/恶/惊）+ 正负面情感分析。
   - 引用声明: 徐琳宏,林鸿飞,潘宇,等.情感词汇本体的构造[J]. 情报学报, 2008, 27(2): 180-185.

2. SnowNLP (isnowfy)
   - 项目地址: https://github.com/isnowfy/snownlp
   - 许可证: MIT License
   - 核心理念: 中文自然语言处理库，提供情感分析(0-1正面概率)、分词、
     关键词提取、文本摘要等功能。情感分析基于朴素贝叶斯分类器。

本实现将上述两个项目的核心理念融合，适配为脚本情感分析工具，
所有核心逻辑直接实现（非 pip install），防止实现层面与原逻辑出现偏差。

==========================================================================
5维度情感分析体系
==========================================================================

1. 情感极性分析（正面/负面/中性）— 基于 cnsenti Hownet 词典 + SnowNLP 贝叶斯
2. 情绪分类（喜悦/愤怒/悲伤/恐惧/惊讶/厌恶）— 基于 cnsenti 大连理工情感本体库
3. 情感强度评估（1-10分）— 基于 cnsenti 情感词强度 + 上下文修饰
4. 情感转折检测（情绪变化点）— 基于段落级情感差异分析
5. 情感曲线生成（基于段落级情感分析）— 与 yang-emotion-curve ER-Curve 集成

==========================================================================
cnsenti 7种情绪分类体系（直接引入）
==========================================================================

来源: 大连理工大学信息检索研究室《中文情感词汇本体库》
注意: 该情感词汇本体由大连理工大学信息检索研究室独立整理标注完成，
      可供国内外大学、科研院所及个人用于学术研究目的。
      如任何单位和个人需将其用于商业目的，请发送邮件至 irlab@dlut.edu.cn 进行协商。

| 编号 | 情感大类 | 情感类 | 例词 |
|------|---------|--------|------|
| 1    | 乐      | 快乐(PA)/安心(PE) | 喜悦、欢喜、欢天喜地 |
| 2    | 好      | 尊敬(PD)/赞扬(PH)/相信(PG)/喜爱(PB)/祝愿(PK) | 英俊、优秀、爱不释手 |
| 3    | 怒      | 愤怒(NA) | 气愤、恼火、七窍生烟 |
| 4    | 哀      | 悲伤(NB)/失望(NJ)/疚(NH)/思(PF) | 忧伤、绝望、心如刀割 |
| 5    | 惧      | 慌(NI)/恐惧(NC)/羞(NG) | 慌张、害怕、胆颤心惊 |
| 6    | 恶      | 烦闷(NE)/憎恶(ND)/贬责(NN)/妒忌(NK)/怀疑(NL) | 憋闷、反感、深恶痛绝 |
| 7    | 惊      | 惊奇(PC) | 奇怪、大吃一惊、瞠目结舌 |

情感强度分为1,3,5,7,9五档，9表示强度最大，1为强度最小。

Usage:
    python tools/sentiment_analyzer.py --script path/to/script.md
    python tools/sentiment_analyzer.py --script path/to/script.md --format json
    python tools/sentiment_analyzer.py --text "文本内容"
    python tools/sentiment_analyzer.py --info

Dependencies: 无强制依赖（纯Python实现，可选 jieba 用于中文分词增强）
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ==========================================================================
# 可选依赖检测
# ==========================================================================
JIEBA_AVAILABLE = False
try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    pass

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent

# ==========================================================================
# cnsenti 情感词典（直接引入核心词表，MIT License + 大连理工学术许可）
# 来源: https://github.com/thunderhit/cnsenti
# 注意: 情绪词典基于大连理工大学情感本体库，仅限学术研究使用
# ==========================================================================

# --- 知网 Hownet 正面情感词（核心子集）---
POSITIVE_WORDS = {
    # 好
    "好": 5, "优秀": 7, "杰出": 7, "卓越": 9, "完美": 9, "精彩": 7, "出色": 7,
    "棒": 5, "赞": 5, "牛": 5, "厉害": 7, "强大": 7, "靠谱": 5,
    "喜欢": 5, "爱": 7, "喜爱": 7, "热爱": 9, "钟爱": 7, "倾慕": 7,
    "信任": 5, "相信": 5, "信赖": 7, "放心": 5, "安心": 5, "踏实": 5,
    "尊敬": 7, "敬爱": 7, "恭敬": 7, "赞扬": 7, "称赞": 7, "夸奖": 5,
    "希望": 3, "期待": 5, "渴望": 7, "盼望": 5, "祝愿": 5,
    # 乐
    "开心": 7, "快乐": 7, "高兴": 7, "喜悦": 7, "欢喜": 7, "欢乐": 7,
    "兴奋": 7, "激动": 7, "振奋": 7, "愉悦": 7, "愉快": 5, "舒心": 5,
    "幸福": 9, "满足": 7, "欣慰": 7, "畅快": 7, "酣畅": 7,
    "笑": 3, "笑眯眯": 5, "欢天喜地": 9, "喜笑颜开": 9,
    # 惊（正面）
    "惊奇": 5, "惊喜": 7, "惊艳": 7, "震撼": 9, "震惊": 9,
}

# --- 知网 Hownet 负面情感词（核心子集）---
NEGATIVE_WORDS = {
    # 怒
    "愤怒": 9, "生气": 7, "恼火": 7, "气愤": 7, "暴怒": 9, "怒火": 9,
    "恼怒": 7, "发火": 7, "大发雷霆": 9, "七窍生烟": 9, "火大": 7,
    # 哀
    "悲伤": 9, "难过": 7, "伤心": 7, "痛苦": 9, "悲哀": 9, "悲痛": 9,
    "忧伤": 7, "忧愁": 7, "郁闷": 5, "沮丧": 7, "失落": 7, "失望": 7,
    "绝望": 9, "崩溃": 9, "心如刀割": 9, "悲痛欲绝": 9,
    "遗憾": 5, "后悔": 7, "内疚": 7, "愧疚": 7, "忏悔": 7,
    "思念": 5, "想念": 5, "牵挂": 5, "相思": 5,
    # 惧
    "害怕": 7, "恐惧": 9, "担心": 5, "忧虑": 7, "焦虑": 7, "紧张": 5,
    "慌张": 7, "惊慌": 7, "胆怯": 7, "畏惧": 9, "胆颤心惊": 9,
    "不安": 5, "心慌": 7, "不知所措": 7, "手忙脚乱": 7,
    "害羞": 5, "害臊": 5, "尴尬": 5, "难堪": 7,
    # 恶
    "讨厌": 7, "厌恶": 9, "反感": 7, "憎恶": 9, "痛恨": 9, "恨": 9,
    "烦": 5, "烦躁": 7, "烦闷": 7, "憋闷": 7, "心烦": 7, "心烦意乱": 9,
    "鄙视": 7, "蔑视": 7, "看不起": 7, "嫌弃": 7,
    "怀疑": 3, "猜疑": 5, "多心": 5, "疑神疑鬼": 7,
    "嫉妒": 7, "妒忌": 7, "眼红": 5, "吃醋": 5,
    # 其他负面
    "差": 5, "烂": 7, "糟糕": 7, "坑": 5, "坑爹": 7, "离谱": 7,
    "无语": 5, "无奈": 5, "崩溃": 9, "懵": 5, "懵了": 5,
    "垃圾": 7, "废物": 7, "脑残": 9, "弱智": 9,
}

# --- 大连理工情感本体库 7种情绪分类词表（核心子集）---
# 来源: 大连理工大学信息检索研究室
# 引用: 徐琳宏,林鸿飞,潘宇,等.情感词汇本体的构造[J]. 情报学报, 2008, 27(2): 180-185.
EMOTION_LEXICON = {
    "乐": {
        "description": "快乐/安心",
        "words": {
            "开心": 7, "快乐": 7, "高兴": 7, "喜悦": 7, "欢喜": 7, "欢乐": 7,
            "兴奋": 7, "激动": 7, "振奋": 7, "愉悦": 7, "愉快": 5, "舒心": 5,
            "幸福": 9, "满足": 7, "欣慰": 7, "畅快": 7, "笑": 3, "笑眯眯": 5,
            "欢天喜地": 9, "喜笑颜开": 9, "安心": 5, "踏实": 5, "宽心": 5,
            "定心丸": 5, "问心无愧": 7, "爽": 7, "太爽了": 9, "上头": 7,
        },
    },
    "好": {
        "description": "尊敬/赞扬/相信/喜爱/祝愿",
        "words": {
            "好": 5, "优秀": 7, "杰出": 7, "卓越": 9, "完美": 9, "精彩": 7,
            "出色": 7, "棒": 5, "赞": 5, "牛": 5, "厉害": 7, "强大": 7,
            "喜欢": 5, "爱": 7, "喜爱": 7, "热爱": 9, "钟爱": 7, "倾慕": 7,
            "信任": 5, "相信": 5, "信赖": 7, "尊敬": 7, "敬爱": 7,
            "赞扬": 7, "称赞": 7, "夸奖": 5, "希望": 3, "期待": 5,
            "渴望": 7, "盼望": 5, "祝愿": 5, "靠谱": 5, "666": 5, "牛逼": 7,
        },
    },
    "怒": {
        "description": "愤怒",
        "words": {
            "愤怒": 9, "生气": 7, "恼火": 7, "气愤": 7, "暴怒": 9, "怒火": 9,
            "恼怒": 7, "发火": 7, "大发雷霆": 9, "七窍生烟": 9, "火大": 7,
            "气死": 9, "炸了": 9, "暴跳如雷": 9,
        },
    },
    "哀": {
        "description": "悲伤/失望/疚/思",
        "words": {
            "悲伤": 9, "难过": 7, "伤心": 7, "痛苦": 9, "悲哀": 9, "悲痛": 9,
            "忧伤": 7, "忧愁": 7, "郁闷": 5, "沮丧": 7, "失落": 7, "失望": 7,
            "绝望": 9, "崩溃": 9, "心如刀割": 9, "悲痛欲绝": 9,
            "遗憾": 5, "后悔": 7, "内疚": 7, "愧疚": 7, "忏悔": 7,
            "思念": 5, "想念": 5, "牵挂": 5, "相思": 5, "心碎": 9,
            "破防": 9, "泪目": 7, "哭了": 7, "感动": 7,
        },
    },
    "惧": {
        "description": "慌/恐惧/羞",
        "words": {
            "害怕": 7, "恐惧": 9, "担心": 5, "忧虑": 7, "焦虑": 7, "紧张": 5,
            "慌张": 7, "惊慌": 7, "胆怯": 7, "畏惧": 9, "胆颤心惊": 9,
            "不安": 5, "心慌": 7, "不知所措": 7, "手忙脚乱": 7,
            "害羞": 5, "害臊": 5, "尴尬": 5, "难堪": 7, "慌": 5, "懵": 5,
        },
    },
    "恶": {
        "description": "烦闷/憎恶/贬责/妒忌/怀疑",
        "words": {
            "讨厌": 7, "厌恶": 9, "反感": 7, "憎恶": 9, "痛恨": 9, "恨": 9,
            "烦": 5, "烦躁": 7, "烦闷": 7, "憋闷": 7, "心烦": 7, "心烦意乱": 9,
            "鄙视": 7, "蔑视": 7, "看不起": 7, "嫌弃": 7,
            "怀疑": 3, "猜疑": 5, "多心": 5, "疑神疑鬼": 7,
            "嫉妒": 7, "妒忌": 7, "眼红": 5, "吃醋": 5,
            "差": 5, "烂": 7, "糟糕": 7, "离谱": 7, "无语": 5, "无奈": 5,
        },
    },
    "惊": {
        "description": "惊奇",
        "words": {
            "惊奇": 5, "惊喜": 7, "惊艳": 7, "震撼": 9, "震惊": 9,
            "奇怪": 3, "奇迹": 7, "大吃一惊": 9, "瞠目结舌": 9,
            "卧槽": 9, "我去": 7, "天哪": 7, "我的天": 7, "不敢相信": 7,
            "炸裂": 9, "离谱": 7, "没想到": 5, "出乎意料": 7,
        },
    },
}

# --- 否定词（cnsenti sentiment_calculate 使用的否定词表）---
NEGATION_WORDS = {"不", "没", "无", "非", "莫", "勿", "未", "否", "别", "毫无", "并不", "并非", "没有"}

# --- 程度副词（cnsenti sentiment_calculate 使用的强度副词表）---
DEGREE_ADVERBS = {
    "极其": 2.0, "非常": 1.8, "特别": 1.8, "十分": 1.8, "格外": 1.6,
    "很": 1.5, "挺": 1.4, "相当": 1.5, "太": 1.7, "真的": 1.5,
    "超": 1.6, "极度": 2.0, "过分": 1.6, "稍微": 0.6, "略微": 0.6,
    "有点": 0.8, "一些": 0.7, "比较": 1.2, "较": 1.1, "更": 1.3,
    "最": 2.0, "极为": 2.0, "尤为": 1.8, "甚": 1.8, "甚为": 1.8,
}

# --- 转折词（用于情感转折检测）---
TRANSITION_WORDS = {
    "但是", "然而", "不过", "可是", "虽然", "尽管", "只是", "可惜",
    "遗憾的是", "没想到", "出乎意料", "反转", "突然", "忽然", "结果",
}


@dataclass
class SentimentResult:
    """情感极性分析结果"""
    polarity: str           # positive / negative / neutral
    positive_score: float   # 正面得分
    negative_score: float   # 负面得分
    confidence: float       # 置信度 0.0-1.0
    positive_words: list[str] = field(default_factory=list)
    negative_words: list[str] = field(default_factory=list)


@dataclass
class EmotionResult:
    """情绪分类结果（7种情绪）"""
    emotions: dict[str, int]  # {乐: count, 好: count, ...}
    dominant_emotion: str      # 主导情绪
    emotion_distribution: dict[str, float] = field(default_factory=dict)  # 归一化分布
    emotion_words_found: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class IntensityResult:
    """情感强度评估结果"""
    intensity_score: int       # 1-10
    level: str                 # 极弱/弱/中/强/极强
    factors: dict[str, float] = field(default_factory=dict)


@dataclass
class TurningPoint:
    """情感转折点"""
    position: int              # 段落位置
    before_polarity: str       # 转折前极性
    after_polarity: str        # 转折后极性
    transition_word: str       # 触发转折的词
    description: str


@dataclass
class EmotionCurvePoint:
    """情感曲线数据点"""
    segment_index: int
    segment_text: str
    polarity: str
    intensity: int
    emotion: str
    arousal: float             # 唤醒值 -3 to +3（与 ER-Curve 兼容）


@dataclass
class SentimentReport:
    """情感分析报告"""
    script_path: str
    script_length: int
    evaluated_at: str
    sentiment_result: Optional[SentimentResult] = None
    emotion_result: Optional[EmotionResult] = None
    intensity_result: Optional[IntensityResult] = None
    turning_points: list[TurningPoint] = field(default_factory=list)
    emotion_curve: list[EmotionCurvePoint] = field(default_factory=list)
    summary: str = ""
    er_curve_integration: str = ""  # 与 yang-emotion-curve ER-Curve 的集成说明

    def to_dict(self) -> dict:
        return {
            "script_path": self.script_path,
            "script_length": self.script_length,
            "evaluated_at": self.evaluated_at,
            "sentiment_result": asdict(self.sentiment_result) if self.sentiment_result else None,
            "emotion_result": asdict(self.emotion_result) if self.emotion_result else None,
            "intensity_result": asdict(self.intensity_result) if self.intensity_result else None,
            "turning_points": [asdict(tp) for tp in self.turning_points],
            "emotion_curve": [asdict(p) for p in self.emotion_curve],
            "summary": self.summary,
            "er_curve_integration": self.er_curve_integration,
        }


# ==========================================================================
# 核心分析引擎
# ==========================================================================

class SentimentAnalyzer:
    """
    情感分析器
    融合 cnsenti 词典规则 + SnowNLP 概率分析
    """

    def __init__(self, use_jieba: bool = True):
        self.use_jieba = use_jieba and JIEBA_AVAILABLE
        if self.use_jieba:
            jieba.initialize()

    # ------------------------------------------------------------------
    # 文本预处理
    # ------------------------------------------------------------------

    def _segment_text(self, text: str) -> list[str]:
        """中文分词"""
        if self.use_jieba:
            return list(jieba.cut(text))
        # 降级：按字符切分
        return list(text)

    def _split_sentences(self, text: str) -> list[str]:
        """句子切分"""
        sentences = re.split(r'[。！？!?\n]+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]

    def _split_paragraphs(self, text: str) -> list[str]:
        """段落切分"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]

    def _split_segments(self, text: str, n: int = 10) -> list[str]:
        """将文本切分为 n 个时间段（与 ER-Curve 10段对齐）"""
        sentences = self._split_sentences(text)
        if len(sentences) <= n:
            return sentences

        segments = []
        segment_size = len(sentences) // n
        remainder = len(sentences) % n

        idx = 0
        for i in range(n):
            size = segment_size + (1 if i < remainder else 0)
            segment = "。".join(sentences[idx:idx + size])
            segments.append(segment)
            idx += size

        return segments

    # ------------------------------------------------------------------
    # 1. 情感极性分析（基于 cnsenti Hownet 词典 + SnowNLP 概率）
    # ------------------------------------------------------------------

    def _analyze_sentiment(self, text: str, words: list[str]) -> SentimentResult:
        """
        情感极性分析
        融合 cnsenti 词典计数 + SnowNLP 式概率计算
        """
        pos_count = 0
        neg_count = 0
        pos_words_found = []
        neg_words_found = []
        pos_weighted = 0.0
        neg_weighted = 0.0

        # cnsenti sentiment_calculate: 考虑否定词和程度副词
        for i, word in enumerate(words):
            if word in POSITIVE_WORDS:
                # 检查前2个词是否有否定词
                negated = False
                degree = 1.0
                for j in range(max(0, i - 2), i):
                    if words[j] in NEGATION_WORDS:
                        negated = True
                    if words[j] in DEGREE_ADVERBS:
                        degree = DEGREE_ADVERBS[words[j]]

                if negated:
                    # 否定正面词 → 负面
                    neg_count += 1
                    neg_weighted += POSITIVE_WORDS[word] * degree * 0.5
                    neg_words_found.append(f"不{word}")
                else:
                    pos_count += 1
                    pos_weighted += POSITIVE_WORDS[word] * degree
                    pos_words_found.append(word)

            elif word in NEGATIVE_WORDS:
                # 检查前2个词是否有否定词
                negated = False
                degree = 1.0
                for j in range(max(0, i - 2), i):
                    if words[j] in NEGATION_WORDS:
                        negated = True
                    if words[j] in DEGREE_ADVERBS:
                        degree = DEGREE_ADVERBS[words[j]]

                if negated:
                    # 否定负面词 → 正面（双重否定）
                    pos_count += 1
                    pos_weighted += NEGATIVE_WORDS[word] * degree * 0.5
                    pos_words_found.append(f"不{word}")
                else:
                    neg_count += 1
                    neg_weighted += NEGATIVE_WORDS[word] * degree
                    neg_words_found.append(word)

        # SnowNLP 式概率计算（朴素贝叶斯近似）
        total = pos_count + neg_count
        if total == 0:
            polarity = "neutral"
            positive_score = 0.5
            negative_score = 0.5
            confidence = 0.3
        else:
            # 加权概率（参考 SnowNLP 的贝叶斯概率输出）
            positive_score = pos_weighted / (pos_weighted + neg_weighted + 1)
            negative_score = neg_weighted / (pos_weighted + neg_weighted + 1)

            if positive_score > negative_score + 0.1:
                polarity = "positive"
            elif negative_score > positive_score + 0.1:
                polarity = "negative"
            else:
                polarity = "neutral"

            confidence = min(abs(positive_score - negative_score) * 2, 1.0)

        return SentimentResult(
            polarity=polarity,
            positive_score=round(positive_score, 3),
            negative_score=round(negative_score, 3),
            confidence=round(confidence, 3),
            positive_words=pos_words_found[:20],
            negative_words=neg_words_found[:20],
        )

    # ------------------------------------------------------------------
    # 2. 情绪分类（基于 cnsenti 大连理工情感本体库 7种情绪）
    # ------------------------------------------------------------------

    def _classify_emotions(self, text: str, words: list[str]) -> EmotionResult:
        """
        7种情绪分类
        基于 cnsenti Emotion.emotion_count 方法
        """
        emotion_counts = {e: 0 for e in EMOTION_LEXICON.keys()}
        emotion_words_found = {e: [] for e in EMOTION_LEXICON.keys()}

        for word in words:
            for emotion, lexicon in EMOTION_LEXICON.items():
                if word in lexicon["words"]:
                    emotion_counts[emotion] += 1
                    if word not in emotion_words_found[emotion]:
                        emotion_words_found[emotion].append(word)

        # 找出主导情绪
        total_emotion_words = sum(emotion_counts.values())
        if total_emotion_words == 0:
            dominant = "中性"
            distribution = {e: 0.0 for e in emotion_counts}
        else:
            dominant = max(emotion_counts, key=emotion_counts.get)
            distribution = {
                e: round(count / total_emotion_words, 3)
                for e, count in emotion_counts.items()
            }

        return EmotionResult(
            emotions=emotion_counts,
            dominant_emotion=dominant,
            emotion_distribution=distribution,
            emotion_words_found={k: v[:10] for k, v in emotion_words_found.items() if v},
        )

    # ------------------------------------------------------------------
    # 3. 情感强度评估（1-10分）
    # ------------------------------------------------------------------

    def _evaluate_intensity(
        self, sentiment: SentimentResult, emotion: EmotionResult, text: str
    ) -> IntensityResult:
        """
        情感强度评估
        综合 cnsenti 情感词强度 + 上下文修饰
        """
        factors = {}

        # 因子1: 情感词数量密度
        total_words = len(text)
        emotion_word_count = sum(emotion.emotions.values())
        density = emotion_word_count / max(total_words / 100, 1)
        factors["情感词密度"] = min(density / 5, 1.0)

        # 因子2: 强度词占比
        strong_words = sum(1 for e in EMOTION_LEXICON.values() for w, s in e["words"].items() if s >= 7)
        strong_found = sum(
            1 for e in EMOTION_LEXICON.values()
            for w, s in e["words"].items()
            if s >= 7 and w in text
        )
        factors["强情感词占比"] = min(strong_found / max(strong_words, 1), 1.0)

        # 因子3: 极性置信度
        factors["极性置信度"] = sentiment.confidence

        # 因子4: 程度副词使用
        degree_count = sum(1 for w in DEGREE_ADVERBS if w in text)
        factors["程度副词增强"] = min(degree_count / 5, 1.0)

        # 因子5: 感叹号密度
        exclamation_density = (text.count("！") + text.count("!")) / max(len(text) / 100, 1)
        factors["感叹号密度"] = min(exclamation_density / 3, 1.0)

        # 综合强度评分（1-10）
        weights = {
            "情感词密度": 0.3,
            "强情感词占比": 0.25,
            "极性置信度": 0.2,
            "程度副词增强": 0.15,
            "感叹号密度": 0.1,
        }
        weighted_score = sum(factors[k] * weights[k] for k in weights)
        intensity_score = max(1, min(10, round(weighted_score * 10)))

        # 强度等级
        if intensity_score >= 8:
            level = "极强"
        elif intensity_score >= 6:
            level = "强"
        elif intensity_score >= 4:
            level = "中"
        elif intensity_score >= 2:
            level = "弱"
        else:
            level = "极弱"

        return IntensityResult(
            intensity_score=intensity_score,
            level=level,
            factors={k: round(v, 3) for k, v in factors.items()},
        )

    # ------------------------------------------------------------------
    # 4. 情感转折检测
    # ------------------------------------------------------------------

    def _detect_turning_points(
        self, text: str, paragraphs: list[str]
    ) -> list[TurningPoint]:
        """
        情感转折检测
        基于段落级情感差异 + 转折词检测
        """
        turning_points = []

        if len(paragraphs) < 2:
            return turning_points

        # 分析每段的情感极性
        paragraph_polarities = []
        for para in paragraphs:
            words = self._segment_text(para)
            result = self._analyze_sentiment(para, words)
            paragraph_polarities.append(result.polarity)

        # 检测极性变化
        for i in range(1, len(paragraphs)):
            before = paragraph_polarities[i - 1]
            after = paragraph_polarities[i]

            # 检测转折词
            transition_found = ""
            for tw in TRANSITION_WORDS:
                if tw in paragraphs[i]:
                    transition_found = tw
                    break

            # 极性变化 或 有转折词且极性不同
            if before != after and before != "neutral" and after != "neutral":
                turning_points.append(TurningPoint(
                    position=i,
                    before_polarity=before,
                    after_polarity=after,
                    transition_word=transition_found or "(无转折词)",
                    description=f"段{i-1}({before}) → 段{i}({after})"
                                + (f"，转折词「{transition_found}」" if transition_found else ""),
                ))
            elif transition_found and before != after:
                turning_points.append(TurningPoint(
                    position=i,
                    before_polarity=before,
                    after_polarity=after,
                    transition_word=transition_found,
                    description=f"转折词「{transition_found}」触发极性变化({before}→{after})",
                ))

        return turning_points

    # ------------------------------------------------------------------
    # 5. 情感曲线生成（与 ER-Curve 集成）
    # ------------------------------------------------------------------

    def _generate_emotion_curve(
        self, text: str, segments: list[str]
    ) -> list[EmotionCurvePoint]:
        """
        情感曲线生成
        基于段落级情感分析，输出与 ER-Curve 兼容的唤醒值
        """
        curve = []

        for i, segment in enumerate(segments):
            words = self._segment_text(segment)
            sentiment = self._analyze_sentiment(segment, words)
            emotion = self._classify_emotions(segment, words)
            intensity = self._evaluate_intensity(sentiment, emotion, segment)

            # 映射到 ER-Curve 唤醒值 (-3 to +3)
            # 参考 yang-emotion-curve 的情绪标注表
            emotion_to_arousal = {
                "乐": 3,   # 高唤醒（兴奋）
                "好": 1,   # 轻度唤醒（兴趣）
                "怒": 3,   # 高唤醒（愤怒）
                "哀": -2,  # 深度共鸣（悲伤）
                "惧": -1,  # 轻度放松（恐惧→紧张）
                "恶": -1,  # 轻度放松（厌恶）
                "惊": 3,   # 高唤醒（震惊）
            }

            # 根据极性调整
            if sentiment.polarity == "positive":
                base_arousal = emotion_to_arousal.get(emotion.dominant_emotion, 1)
            elif sentiment.polarity == "negative":
                base_arousal = emotion_to_arousal.get(emotion.dominant_emotion, -1)
            else:
                base_arousal = 0

            # 根据强度调整
            intensity_factor = (intensity.intensity_score - 5) / 5  # -1 to 1
            arousal = max(-3, min(3, base_arousal + intensity_factor))

            curve.append(EmotionCurvePoint(
                segment_index=i,
                segment_text=segment[:50] + "..." if len(segment) > 50 else segment,
                polarity=sentiment.polarity,
                intensity=intensity.intensity_score,
                emotion=emotion.dominant_emotion,
                arousal=round(arousal, 1),
            ))

        return curve

    # ------------------------------------------------------------------
    # 主分析入口
    # ------------------------------------------------------------------

    def analyze(self, text: str, script_path: str = "<inline>") -> SentimentReport:
        """执行完整的情感分析"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if len(text) < 50:
            return SentimentReport(
                script_path=script_path,
                script_length=len(text),
                evaluated_at=now,
                summary="⚠️ 内容过短（<50字符），分析结果可信度低",
            )

        words = self._segment_text(text)
        paragraphs = self._split_paragraphs(text)
        segments = self._split_segments(text, n=10)

        # 5维度分析
        sentiment = self._analyze_sentiment(text, words)
        emotion = self._classify_emotions(text, words)
        intensity = self._evaluate_intensity(sentiment, emotion, text)
        turning_points = self._detect_turning_points(text, paragraphs)
        curve = self._generate_emotion_curve(text, segments)

        # 生成摘要
        emotion_str = " | ".join(f"{e}:{c}" for e, c in emotion.emotions.items() if c > 0)
        summary = (
            f"极性: {sentiment.polarity}(置信度{sentiment.confidence:.0%}) | "
            f"主导情绪: {emotion.dominant_emotion} | "
            f"强度: {intensity.intensity_score}/10({intensity.level}) | "
            f"转折点: {len(turning_points)}个 | "
            f"情绪分布: {emotion_str or '无'}"
        )

        # ER-Curve 集成说明
        curve_values = [p.arousal for p in curve]
        if curve_values:
            curve_str = " → ".join(f"{v:+.1f}" for v in curve_values)
            er_integration = (
                f"ER-Curve 唤醒值序列（10段）: {curve_str}\n"
                f"可直接接入 yang-emotion-curve Step 4（绘制 ER-Curve）使用。\n"
                f"曲线特征: 峰值{max(curve_values):+.1f}, 谷值{min(curve_values):+.1f}, "
                f"动态范围{max(curve_values)-min(curve_values):.1f}"
            )
        else:
            er_integration = "段落不足，无法生成 ER-Curve 数据"

        return SentimentReport(
            script_path=script_path,
            script_length=len(text),
            evaluated_at=now,
            sentiment_result=sentiment,
            emotion_result=emotion,
            intensity_result=intensity,
            turning_points=turning_points,
            emotion_curve=curve,
            summary=summary,
            er_curve_integration=er_integration,
        )


# ==========================================================================
# 报告格式化输出
# ==========================================================================

def format_report_markdown(report: SentimentReport) -> str:
    """Markdown 格式化报告"""
    lines = []
    lines.append("### 🎭 情感分析报告（cnsenti + SnowNLP）")
    lines.append("")
    lines.append(f"- **脚本路径**: {report.script_path}")
    lines.append(f"- **脚本长度**: {report.script_length} 字符")
    lines.append(f"- **分析时间**: {report.evaluated_at}")
    lines.append(f"- **摘要**: {report.summary}")
    lines.append("")

    # 1. 情感极性
    if report.sentiment_result:
        s = report.sentiment_result
        lines.append("#### 1. 情感极性分析")
        lines.append("")
        lines.append(f"- **极性**: {s.polarity}")
        lines.append(f"- **正面得分**: {s.positive_score:.3f}")
        lines.append(f"- **负面得分**: {s.negative_score:.3f}")
        lines.append(f"- **置信度**: {s.confidence:.1%}")
        if s.positive_words:
            lines.append(f"- **正面词**: {', '.join(s.positive_words[:10])}")
        if s.negative_words:
            lines.append(f"- **负面词**: {', '.join(s.negative_words[:10])}")
        lines.append("")

    # 2. 情绪分类
    if report.emotion_result:
        e = report.emotion_result
        lines.append("#### 2. 情绪分类（7种情绪 · 大连理工情感本体库）")
        lines.append("")
        lines.append("| 情绪 | 词数 | 占比 | 匹配词 |")
        lines.append("|------|------|------|--------|")
        for emotion, count in e.emotions.items():
            dist = e.emotion_distribution.get(emotion, 0)
            words = e.emotion_words_found.get(emotion, [])
            lines.append(f"| {emotion} | {count} | {dist:.1%} | {', '.join(words[:5])} |")
        lines.append(f"\n**主导情绪**: {e.dominant_emotion}")
        lines.append("")

    # 3. 情感强度
    if report.intensity_result:
        i = report.intensity_result
        lines.append("#### 3. 情感强度评估")
        lines.append("")
        lines.append(f"- **强度评分**: {i.intensity_score}/10 ({i.level})")
        lines.append("- **因子分解**:")
        for factor, value in i.factors.items():
            lines.append(f"  - {factor}: {value:.3f}")
        lines.append("")

    # 4. 情感转折
    if report.turning_points:
        lines.append("#### 4. 情感转折检测")
        lines.append("")
        lines.append("| 位置 | 转折前 | 转折后 | 转折词 | 描述 |")
        lines.append("|------|--------|--------|--------|------|")
        for tp in report.turning_points:
            lines.append(f"| 段{tp.position} | {tp.before_polarity} | {tp.after_polarity} | {tp.transition_word} | {tp.description} |")
        lines.append("")
    else:
        lines.append("#### 4. 情感转折检测")
        lines.append("")
        lines.append("未检测到明显情感转折点")
        lines.append("")

    # 5. 情感曲线
    if report.emotion_curve:
        lines.append("#### 5. 情感曲线（ER-Curve 兼容）")
        lines.append("")
        lines.append("| 段号 | 极性 | 强度 | 情绪 | 唤醒值 | 文本片段 |")
        lines.append("|------|------|------|------|--------|---------|")
        for p in report.emotion_curve:
            lines.append(f"| {p.segment_index} | {p.polarity} | {p.intensity} | {p.emotion} | {p.arousal:+.1f} | {p.segment_text} |")
        lines.append("")

    # ER-Curve 集成
    if report.er_curve_integration:
        lines.append("#### ER-Curve 集成说明")
        lines.append("")
        lines.append(f"```\n{report.er_curve_integration}\n```")
        lines.append("")

    lines.append("---")
    lines.append("*分析引擎: cnsenti (MIT License + 大连理工学术许可) + SnowNLP (MIT License) | 作者: 阿洋*")
    lines.append("*情感本体库引用: 徐琳宏,林鸿飞,潘宇,等.情感词汇本体的构造[J]. 情报学报, 2008, 27(2): 180-185.*")
    return "\n".join(lines)


def format_report_json(report: SentimentReport) -> str:
    """JSON 格式化报告"""
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)


# ==========================================================================
# CLI 入口
# ==========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="情感分析器（基于 cnsenti + SnowNLP 理念）作者: 阿洋"
    )
    parser.add_argument("--script", type=str, help="脚本文件路径")
    parser.add_argument("--text", type=str, help="直接传入文本内容")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="输出格式")
    parser.add_argument("--no-jieba", action="store_true", help="禁用 jieba 分词（降级为字符切分）")
    parser.add_argument("--info", action="store_true", help="显示分析器信息")
    args = parser.parse_args()

    if args.info:
        print("=" * 60)
        print("情感分析器 (Sentiment Analyzer)")
        print("作者: 阿洋")
        print("=" * 60)
        print("基于开源项目:")
        print("  1. cnsenti (thunderhit/hidadeng, MIT License)")
        print("     - 中文情感分析库")
        print("     - 7种情绪分类(好/乐/哀/怒/惧/恶/惊) + 正负面情感")
        print("     - https://github.com/thunderhit/cnsenti")
        print("  2. SnowNLP (isnowfy, MIT License)")
        print("     - 中文自然语言处理库")
        print("     - 情感分析(0-1正面概率) + 分词 + 关键词")
        print("     - https://github.com/isnowfy/snownlp")
        print("=" * 60)
        print("5维度分析体系:")
        print("  - 情感极性分析: 正面/负面/中性")
        print("  - 情绪分类: 喜悦/愤怒/悲伤/恐惧/惊讶/厌恶/好")
        print("  - 情感强度评估: 1-10分")
        print("  - 情感转折检测: 情绪变化点")
        print("  - 情感曲线生成: ER-Curve 兼容(10段)")
        print("=" * 60)
        print("情感本体库引用:")
        print("  徐琳宏,林鸿飞,潘宇,等.情感词汇本体的构造[J].")
        print("  情报学报, 2008, 27(2): 180-185.")
        print("=" * 60)
        print(f"jieba 分词: {'已启用' if JIEBA_AVAILABLE and not args.no_jieba else '未启用(降级模式)'}")
        return

    # 获取文本
    text = ""
    script_path = "<inline>"
    if args.script:
        script_file = Path(args.script)
        if not script_file.exists():
            print(f"错误: 脚本文件不存在: {args.script}", file=sys.stderr)
            sys.exit(1)
        text = script_file.read_text(encoding="utf-8")
        script_path = str(script_file)
    elif args.text:
        text = args.text
    else:
        print("错误: 请提供 --script 或 --text 参数", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # 执行分析
    analyzer = SentimentAnalyzer(use_jieba=not args.no_jieba)
    report = analyzer.analyze(text, script_path)

    # 输出
    if args.format == "json":
        print(format_report_json(report))
    else:
        print(format_report_markdown(report))


if __name__ == "__main__":
    main()
