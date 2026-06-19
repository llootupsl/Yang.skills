#!/usr/bin/env python3
# 作者: 阿洋
"""
content_quality_evaluator.py — 内容质量评测器
作者: 阿洋

基于 KuaiMod（快手开源短视频内容质量评测）和 VideoScore-v1.1（TIGER-Lab 5维度视频质量评估）理念实现。

==========================================================================
开源项目许可证声明
==========================================================================

1. KuaiMod (快手开源)
   - 项目地址: https://github.com/KuaiMod/KuaiMod.github.io
   - 论文: VLM as Policy: Common-Law Content Moderation Framework for Short Video Platform
   - 许可证: CC BY-SA 4.0 (基准测试数据集)
   - 核心理念: 基于多模态大模型(VLM)和链式推理(CoT)的短视频内容质量判别框架，
     包含4类主要劣质内容和15类细粒度劣质内容类型分类体系。

2. VideoScore-v1.1 (TIGER-Lab)
   - 项目地址: https://github.com/TIGER-AI-Lab/VideoScore
   - 论文: VideoScore: Building Automatic Metrics to Simulate Fine-grained Human Feedback
   - 许可证: MIT License
   - 核心理念: 5维度视频质量评估（视觉质量/时序一致性/动态程度/文本-视频对齐/事实一致性），
     评分范围1.0-4.0，基于Idefics2-8B架构的回归任务设计。

本实现将上述两个项目的核心理念融合，适配为脚本内容质量评测工具，
所有核心逻辑直接实现（非 pip install），防止实现层面与原逻辑出现偏差。

==========================================================================
5维度内容质量评测体系
==========================================================================

1. 视觉质量（Visual Quality）    — 画面清晰度、构图、光线（脚本中描述的视觉元素）
2. 内容价值（Content Value）      — 信息密度、知识性、娱乐性
3. 情感共鸣（Emotional Resonance）— 情绪感染力、代入感
4. 技术质量（Technical Quality）  — 剪辑节奏、音画同步、转场（脚本结构的技术性）
5. 传播潜力（Viral Potential）    — 话题性、分享动机、互动引导

评分范围: 1.0-4.0（与 VideoScore-v1.1 一致）
综合评分: 5维度几何平均（参考 Redpen WQI 方法论）

==========================================================================
KuaiMod 劣质内容检测维度（融合）
==========================================================================

KuaiMod 定义了4类主要劣质内容，本评测器将其作为扣分项融入5维度评分：
1. 低质搬运类 — 内容原创性不足、信息密度极低
2. 虚假误导类 — 标题党、内容与承诺不符、事实错误
3. 引战低俗类 — 恶意引战、低俗擦边、价值观偏差
4. 体验不佳类 — 节奏拖沓、信息混乱、无重点

Usage:
    python tools/content_quality_evaluator.py --script path/to/script.md
    python tools/content_quality_evaluator.py --script path/to/script.md --format json
    python tools/content_quality_evaluator.py --text "脚本内容文本"
    python tools/content_quality_evaluator.py --info

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
# 可选依赖检测（与 dspy_scoring.py 风格一致）
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
# KuaiMod 劣质内容分类体系（直接引入，CC BY-SA 4.0）
# 来源: KuaiMod 论文 - VLM as Policy: Common-Law Content Moderation Framework
# ==========================================================================
KUAIMOD_LOW_QUALITY_CATEGORIES = {
    "低质搬运类": {
        "description": "内容原创性不足，存在搬运、抄袭、洗稿痕迹",
        "subcategories": [
            "纯搬运无加工", "搬运+少量配音", "多源拼接无逻辑",
            "翻译搬运未标注", "截图搬运无解读",
        ],
        "penalty_weight": 0.8,
    },
    "虚假误导类": {
        "description": "标题党、内容与承诺不符、事实错误",
        "subcategories": [
            "标题与内容严重不符", "编造数据/案例", "虚假承诺",
            "断章取义误导", "过期信息未标注",
        ],
        "penalty_weight": 0.9,
    },
    "引战低俗类": {
        "description": "恶意引战、低俗擦边、价值观偏差",
        "subcategories": [
            "恶意对比引战", "低俗擦边内容", "极端价值观输出",
            "人身攻击", "地域/性别歧视",
        ],
        "penalty_weight": 0.85,
    },
    "体验不佳类": {
        "description": "节奏拖沓、信息混乱、无重点",
        "subcategories": [
            "开头拖沓超10秒无重点", "信息密度极低", "逻辑混乱跳跃",
            "结尾无收束", "全程无情绪起伏",
        ],
        "penalty_weight": 0.6,
    },
}

# ==========================================================================
# VideoScore-v1.1 五维度评估锚点（直接引入，MIT License）
# 来源: TIGER-Lab/VideoScore-v1.1 - https://huggingface.co/TIGER-Lab/VideoScore-v1.1
# ==========================================================================
VIDEOSCORE_DIMENSIONS = {
    "visual_quality": {
        "name_cn": "视觉质量",
        "description": "画面清晰度、构图、光线（脚本中描述的视觉元素质量）",
        "score_range": (1.0, 4.0),
        "anchors": {
            1.0: "无视觉描述，脚本完全不涉及画面设计",
            2.0: "有少量视觉描述但模糊，画面感弱",
            3.0: "视觉描述清晰，有构图和场景感，画面可想象",
            4.0: "视觉描述精准生动，构图/光线/色彩有明确设计，画面感极强",
        },
    },
    "content_value": {
        "name_cn": "内容价值",
        "description": "信息密度、知识性、娱乐性",
        "score_range": (1.0, 4.0),
        "anchors": {
            1.0: "信息密度极低，无知识增量，无娱乐价值",
            2.0: "有少量信息但稀释严重，知识性或娱乐性偏弱",
            3.0: "信息密度合理，有明确知识输出或娱乐价值",
            4.0: "信息密度高且精准，知识性与娱乐性兼具，有 actionable 建议",
        },
    },
    "emotional_resonance": {
        "name_cn": "情感共鸣",
        "description": "情绪感染力、代入感",
        "score_range": (1.0, 4.0),
        "anchors": {
            1.0: "全程平淡，无情绪波动，无代入感",
            2.0: "偶有情绪点但植入生硬，代入感弱",
            3.0: "情绪曲线有起伏，有代入感，能引发共鸣",
            4.0: "情绪感染力极强，代入感深，能引发强烈共鸣或行动",
        },
    },
    "technical_quality": {
        "name_cn": "技术质量",
        "description": "剪辑节奏、音画同步、转场（脚本结构的技术性）",
        "score_range": (1.0, 4.0),
        "anchors": {
            1.0: "结构混乱，无叙事骨架，节奏完全失控",
            2.0: "有基本结构但转折生硬，节奏有拖沓",
            3.0: "结构清晰，节奏合理，转场自然",
            4.0: "结构精密，节奏精准，转场流畅，每句都有推进作用",
        },
    },
    "viral_potential": {
        "name_cn": "传播潜力",
        "description": "话题性、分享动机、互动引导",
        "score_range": (1.0, 4.0),
        "anchors": {
            1.0: "无传播因子，纯自嗨，无分享动机",
            2.0: "传播因子弱，分享动机不明确",
            3.0: "有明确传播因子和分享动机，有互动引导",
            4.0: "传播因子极强，具备社交货币属性，互动引导精准",
        },
    },
}

# ==========================================================================
# 评测规则词典（基于 KuaiMod 劣质内容检测 + VideoScore 评估锚点）
# ==========================================================================

# AI味高频踩雷词（与 yang-polish L1 规则对齐）
AI_FLAVOR_WORDS = {
    "说白了", "意味着什么", "这意味着", "本质上", "换句话说", "不可否认",
    "综上所述", "值得注意的是", "不难发现", "让我们来看看", "接下来让我们",
    "首先", "其次", "最后", "总而言之", "由此可见",
}

# 套话模式（正则）
CLICHE_PATTERNS = [
    r"在当今.{0,10}时代",
    r"随着.{0,10}的不断进步",
    r"随着.{0,10}的快速发展",
    r"众所周知",
    r"不言而喻",
    r"毋庸置疑",
]

# 情绪强度词（用于情感共鸣维度评估）
EMOTION_INTENSITY_WORDS = {
    "强": {"震惊", "震撼", "崩溃", "暴怒", "狂喜", "绝望", "卧槽", "离谱", "炸裂", "破防"},
    "中": {"开心", "生气", "难过", "害怕", "惊讶", "感动", "兴奋", "紧张", "期待", "失望"},
    "弱": {"还行", "不错", "可以", "一般", "还好", "凑合"},
}

# 传播因子关键词（用于传播潜力维度评估）
VIRAL_FACTOR_KEYWORDS = {
    "共鸣力": ["感同身受", "我也是", "谁懂", "真实", "戳中"],
    "冲突性": ["但是", "然而", "没想到", "反转", "打脸", "争议"],
    "稀缺感": ["独家", "首次", "罕见", "秘密", "只有", "唯一"],
    "社交货币": ["分享", "转发", "收藏", "必看", "干货", "建议收藏"],
}

# 信息密度指示词（用于内容价值维度评估）
INFO_DENSITY_INDICATORS = {
    "数据锚定": [r"\d+%", r"\d+万", r"\d+亿", r"\d+个", r"\d+小时", r"\d+分钟"],
    "具体案例": ["比如", "例如", "案例", "亲身经历", "实测", "体验"],
    "可执行建议": ["建议", "方法", "步骤", "第一步", "试试", "你可以"],
    "知识输出": ["原理", "因为", "原因是", "本质是", "底层逻辑", "机制"],
}


@dataclass
class DimensionScore:
    """单维度评分结果"""
    dimension_key: str
    dimension_name: str
    score: float
    anchor_reference: str
    evidence: str
    confidence: str  # high / medium / low


@dataclass
class LowQualityFlag:
    """KuaiMod 劣质内容标记"""
    category: str
    subcategory: str
    description: str
    evidence: str
    penalty_applied: float


@dataclass
class ContentQualityReport:
    """内容质量评测报告"""
    script_path: str
    script_length: int
    evaluated_at: str
    dimension_scores: list[DimensionScore] = field(default_factory=list)
    low_quality_flags: list[LowQualityFlag] = field(default_factory=list)
    composite_score: float = 0.0
    grade: str = ""
    summary: str = ""
    improvement_suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "script_path": self.script_path,
            "script_length": self.script_length,
            "evaluated_at": self.evaluated_at,
            "dimension_scores": [asdict(d) for d in self.dimension_scores],
            "low_quality_flags": [asdict(f) for f in self.low_quality_flags],
            "composite_score": round(self.composite_score, 2),
            "grade": self.grade,
            "summary": self.summary,
            "improvement_suggestions": self.improvement_suggestions,
        }


# ==========================================================================
# 核心评测引擎
# ==========================================================================

class ContentQualityEvaluator:
    """
    内容质量评测器
    融合 KuaiMod 劣质内容检测 + VideoScore-v1.1 五维度评估
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
        # 按中文标点切分
        sentences = re.split(r'[。！？!?\n]+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]

    def _split_paragraphs(self, text: str) -> list[str]:
        """段落切分"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]

    # ------------------------------------------------------------------
    # 维度1: 视觉质量评估
    # ------------------------------------------------------------------

    def _evaluate_visual_quality(self, text: str, sentences: list[str]) -> DimensionScore:
        """评估视觉质量：脚本中描述的视觉元素质量"""
        visual_keywords = [
            "画面", "镜头", "特写", "全景", "近景", "远景", "俯拍", "仰拍",
            "光线", "色彩", "构图", "背景", "前景", "字幕", "贴纸", "特效",
            "转场", "动画", "图片", "截图", "封面",
        ]
        visual_count = sum(1 for kw in visual_keywords if kw in text)
        visual_density = visual_count / max(len(sentences), 1)

        if visual_density >= 0.3:
            score = 4.0
            anchor = VIDEOSCORE_DIMENSIONS["visual_quality"]["anchors"][4.0]
            evidence = f"视觉描述密度 {visual_density:.2f}，包含 {visual_count} 个视觉关键词"
        elif visual_density >= 0.15:
            score = 3.0
            anchor = VIDEOSCORE_DIMENSIONS["visual_quality"]["anchors"][3.0]
            evidence = f"视觉描述密度 {visual_density:.2f}，包含 {visual_count} 个视觉关键词"
        elif visual_density >= 0.05:
            score = 2.0
            anchor = VIDEOSCORE_DIMENSIONS["visual_quality"]["anchors"][2.0]
            evidence = f"视觉描述密度 {visual_density:.2f}，视觉元素较少"
        else:
            score = 1.0
            anchor = VIDEOSCORE_DIMENSIONS["visual_quality"]["anchors"][1.0]
            evidence = f"视觉描述密度 {visual_density:.2f}，几乎无视觉元素描述"

        confidence = "high" if visual_count >= 5 else "medium" if visual_count >= 2 else "low"
        return DimensionScore(
            dimension_key="visual_quality",
            dimension_name="视觉质量",
            score=score,
            anchor_reference=anchor,
            evidence=evidence,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # 维度2: 内容价值评估
    # ------------------------------------------------------------------

    def _evaluate_content_value(self, text: str, sentences: list[str]) -> DimensionScore:
        """评估内容价值：信息密度、知识性、娱乐性"""
        info_score = 0
        evidence_parts = []

        # 检测数据锚定
        data_count = 0
        for pattern in INFO_DENSITY_INDICATORS["数据锚定"]:
            data_count += len(re.findall(pattern, text))
        if data_count >= 3:
            info_score += 2
            evidence_parts.append(f"数据锚定 {data_count} 处")
        elif data_count >= 1:
            info_score += 1
            evidence_parts.append(f"数据锚定 {data_count} 处")

        # 检测具体案例
        case_count = sum(1 for kw in INFO_DENSITY_INDICATORS["具体案例"] if kw in text)
        if case_count >= 2:
            info_score += 2
            evidence_parts.append(f"具体案例引用 {case_count} 处")
        elif case_count >= 1:
            info_score += 1
            evidence_parts.append(f"具体案例引用 {case_count} 处")

        # 检测可执行建议
        action_count = sum(1 for kw in INFO_DENSITY_INDICATORS["可执行建议"] if kw in text)
        if action_count >= 3:
            info_score += 2
            evidence_parts.append(f"可执行建议 {action_count} 处")
        elif action_count >= 1:
            info_score += 1
            evidence_parts.append(f"可执行建议 {action_count} 处")

        # 检测知识输出
        knowledge_count = sum(1 for kw in INFO_DENSITY_INDICATORS["知识输出"] if kw in text)
        if knowledge_count >= 2:
            info_score += 1
            evidence_parts.append(f"知识输出 {knowledge_count} 处")

        # 映射到1.0-4.0
        if info_score >= 6:
            score = 4.0
            anchor = VIDEOSCORE_DIMENSIONS["content_value"]["anchors"][4.0]
        elif info_score >= 4:
            score = 3.0
            anchor = VIDEOSCORE_DIMENSIONS["content_value"]["anchors"][3.0]
        elif info_score >= 2:
            score = 2.0
            anchor = VIDEOSCORE_DIMENSIONS["content_value"]["anchors"][2.0]
        else:
            score = 1.0
            anchor = VIDEOSCORE_DIMENSIONS["content_value"]["anchors"][1.0]

        evidence = "；".join(evidence_parts) if evidence_parts else "信息密度指标未检测到"
        confidence = "high" if info_score >= 4 else "medium" if info_score >= 2 else "low"
        return DimensionScore(
            dimension_key="content_value",
            dimension_name="内容价值",
            score=score,
            anchor_reference=anchor,
            evidence=evidence,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # 维度3: 情感共鸣评估
    # ------------------------------------------------------------------

    def _evaluate_emotional_resonance(self, text: str, sentences: list[str]) -> DimensionScore:
        """评估情感共鸣：情绪感染力、代入感"""
        strong_count = sum(1 for w in EMOTION_INTENSITY_WORDS["强"] if w in text)
        medium_count = sum(1 for w in EMOTION_INTENSITY_WORDS["中"] if w in text)
        weak_count = sum(1 for w in EMOTION_INTENSITY_WORDS["弱"] if w in text)

        # 情绪加权得分
        emotion_weighted = strong_count * 3 + medium_count * 2 + weak_count * 1
        emotion_density = emotion_weighted / max(len(sentences), 1)

        # 检测第一人称代入
        first_person_count = text.count("我") + text.count("自己") + text.count("亲身")
        immersion_score = min(first_person_count / max(len(sentences), 1), 1.0)

        combined = emotion_density * 0.6 + immersion_score * 2.0

        if combined >= 1.5:
            score = 4.0
            anchor = VIDEOSCORE_DIMENSIONS["emotional_resonance"]["anchors"][4.0]
            evidence = f"强情绪词{strong_count}个，中情绪词{medium_count}个，第一人称{first_person_count}处"
        elif combined >= 0.8:
            score = 3.0
            anchor = VIDEOSCORE_DIMENSIONS["emotional_resonance"]["anchors"][3.0]
            evidence = f"强情绪词{strong_count}个，中情绪词{medium_count}个，第一人称{first_person_count}处"
        elif combined >= 0.3:
            score = 2.0
            anchor = VIDEOSCORE_DIMENSIONS["emotional_resonance"]["anchors"][2.0]
            evidence = f"强情绪词{strong_count}个，中情绪词{medium_count}个，第一人称{first_person_count}处"
        else:
            score = 1.0
            anchor = VIDEOSCORE_DIMENSIONS["emotional_resonance"]["anchors"][1.0]
            evidence = f"情绪词极少，第一人称{first_person_count}处，代入感弱"

        confidence = "high" if strong_count >= 2 else "medium" if medium_count >= 2 else "low"
        return DimensionScore(
            dimension_key="emotional_resonance",
            dimension_name="情感共鸣",
            score=score,
            anchor_reference=anchor,
            evidence=evidence,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # 维度4: 技术质量评估
    # ------------------------------------------------------------------

    def _evaluate_technical_quality(self, text: str, sentences: list[str], paragraphs: list[str]) -> DimensionScore:
        """评估技术质量：剪辑节奏、音画同步、转场（脚本结构的技术性）"""
        # 句子长度变化（节奏感）
        sentence_lengths = [len(s) for s in sentences]
        if len(sentence_lengths) >= 3:
            avg_len = sum(sentence_lengths) / len(sentence_lengths)
            length_variance = sum((l - avg_len) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            length_std = math.sqrt(length_variance)
            rhythm_score = min(length_std / 20.0, 1.0)  # 标准差越大节奏感越强
        else:
            rhythm_score = 0.0

        # 转场词检测
        transition_words = [
            "说到这个", "回到", "顺着", "接下来", "然后", "不过",
            "但是", "然而", "其实", "说实话", "讲真", "你想想",
        ]
        transition_count = sum(1 for w in transition_words if w in text)
        transition_density = transition_count / max(len(paragraphs), 1)

        # 段落均匀度
        if len(paragraphs) >= 3:
            para_lengths = [len(p) for p in paragraphs]
            avg_para = sum(para_lengths) / len(para_lengths)
            para_cv = sum(abs(l - avg_para) for l in para_lengths) / (avg_para * len(para_lengths))
            uniformity_score = max(0, 1 - para_cv)  # 变异系数越小越均匀
        else:
            uniformity_score = 0.5

        combined = rhythm_score * 0.4 + min(transition_density, 1.0) * 0.3 + uniformity_score * 0.3

        if combined >= 0.7:
            score = 4.0
            anchor = VIDEOSCORE_DIMENSIONS["technical_quality"]["anchors"][4.0]
            evidence = f"节奏感{rhythm_score:.2f}，转场{transition_count}处，段落均匀度{uniformity_score:.2f}"
        elif combined >= 0.5:
            score = 3.0
            anchor = VIDEOSCORE_DIMENSIONS["technical_quality"]["anchors"][3.0]
            evidence = f"节奏感{rhythm_score:.2f}，转场{transition_count}处，段落均匀度{uniformity_score:.2f}"
        elif combined >= 0.3:
            score = 2.0
            anchor = VIDEOSCORE_DIMENSIONS["technical_quality"]["anchors"][2.0]
            evidence = f"节奏感{rhythm_score:.2f}，转场{transition_count}处，段落均匀度{uniformity_score:.2f}"
        else:
            score = 1.0
            anchor = VIDEOSCORE_DIMENSIONS["technical_quality"]["anchors"][1.0]
            evidence = f"节奏感{rhythm_score:.2f}，转场{transition_count}处，结构混乱"

        confidence = "high" if len(sentences) >= 10 else "medium"
        return DimensionScore(
            dimension_key="technical_quality",
            dimension_name="技术质量",
            score=score,
            anchor_reference=anchor,
            evidence=evidence,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # 维度5: 传播潜力评估
    # ------------------------------------------------------------------

    def _evaluate_viral_potential(self, text: str, sentences: list[str]) -> DimensionScore:
        """评估传播潜力：话题性、分享动机、互动引导"""
        viral_factors_found = {}
        for factor, keywords in VIRAL_FACTOR_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text)
            if count > 0:
                viral_factors_found[factor] = count

        factor_count = len(viral_factors_found)
        total_keyword_hits = sum(viral_factors_found.values())

        # 互动引导检测
        interaction_patterns = [r"评论", r"留言", r"点赞", r"关注", r"转发", r"收藏", r"你怎么看", r"同意吗"]
        interaction_count = sum(len(re.findall(p, text)) for p in interaction_patterns)

        combined = factor_count * 0.5 + min(total_keyword_hits, 5) * 0.1 + min(interaction_count, 3) * 0.3

        if combined >= 2.5:
            score = 4.0
            anchor = VIDEOSCORE_DIMENSIONS["viral_potential"]["anchors"][4.0]
            evidence = f"传播因子{factor_count}类({list(viral_factors_found.keys())})，互动引导{interaction_count}处"
        elif combined >= 1.5:
            score = 3.0
            anchor = VIDEOSCORE_DIMENSIONS["viral_potential"]["anchors"][3.0]
            evidence = f"传播因子{factor_count}类({list(viral_factors_found.keys())})，互动引导{interaction_count}处"
        elif combined >= 0.5:
            score = 2.0
            anchor = VIDEOSCORE_DIMENSIONS["viral_potential"]["anchors"][2.0]
            evidence = f"传播因子{factor_count}类，互动引导{interaction_count}处"
        else:
            score = 1.0
            anchor = VIDEOSCORE_DIMENSIONS["viral_potential"]["anchors"][1.0]
            evidence = f"传播因子{factor_count}类，互动引导{interaction_count}处，传播潜力弱"

        confidence = "high" if factor_count >= 3 else "medium" if factor_count >= 1 else "low"
        return DimensionScore(
            dimension_key="viral_potential",
            dimension_name="传播潜力",
            score=score,
            anchor_reference=anchor,
            evidence=evidence,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # KuaiMod 劣质内容检测
    # ------------------------------------------------------------------

    def _detect_low_quality_content(self, text: str, sentences: list[str]) -> list[LowQualityFlag]:
        """KuaiMod 劣质内容检测（4类主要劣质内容）"""
        flags = []

        # 1. 低质搬运类检测
        if len(sentences) > 0:
            avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
            if avg_sentence_len < 8 and len(text) > 500:
                flags.append(LowQualityFlag(
                    category="低质搬运类",
                    subcategory="纯搬运无加工",
                    description="句子平均长度过短，可能为拼接搬运内容",
                    evidence=f"平均句长 {avg_sentence_len:.1f} 字符",
                    penalty_applied=KUAIMOD_LOW_QUALITY_CATEGORIES["低质搬运类"]["penalty_weight"],
                ))

        # 2. 虚假误导类检测
        title_bait_patterns = [r"震惊", r"惊呆", r"99%的人", r"看完惊了", r"绝对"]
        title_bait_count = sum(len(re.findall(p, text)) for p in title_bait_patterns)
        if title_bait_count >= 2:
            flags.append(LowQualityFlag(
                category="虚假误导类",
                subcategory="标题与内容严重不符",
                description="检测到标题党高频词，可能存在虚假误导",
                evidence=f"标题党词命中 {title_bait_count} 处",
                penalty_applied=KUAIMOD_LOW_QUALITY_CATEGORIES["虚假误导类"]["penalty_weight"],
            ))

        # 3. 引战低俗类检测
        conflict_patterns = [r"吊打", r"秒杀", r"完爆", r"垃圾", r"弱智", r"脑残"]
        conflict_count = sum(len(re.findall(p, text)) for p in conflict_patterns)
        if conflict_count >= 2:
            flags.append(LowQualityFlag(
                category="引战低俗类",
                subcategory="恶意对比引战",
                description="检测到引战词汇，可能存在恶意对比",
                evidence=f"引战词命中 {conflict_count} 处",
                penalty_applied=KUAIMOD_LOW_QUALITY_CATEGORIES["引战低俗类"]["penalty_weight"],
            ))

        # 4. 体验不佳类检测
        if len(sentences) > 0:
            first_3_sentences = sentences[:3]
            first_3_length = sum(len(s) for s in first_3_sentences)
            if first_3_length > 200 and len(sentences) > 5:
                flags.append(LowQualityFlag(
                    category="体验不佳类",
                    subcategory="开头拖沓超10秒无重点",
                    description="开头前3句过长，可能存在开头拖沓",
                    evidence=f"前3句总长 {first_3_length} 字符",
                    penalty_applied=KUAIMOD_LOW_QUALITY_CATEGORIES["体验不佳类"]["penalty_weight"],
                ))

        # AI味检测（套话）
        cliche_count = 0
        for pattern in CLICHE_PATTERNS:
            cliche_count += len(re.findall(pattern, text))
        ai_word_count = sum(1 for w in AI_FLAVOR_WORDS if w in text)
        if cliche_count + ai_word_count >= 3:
            flags.append(LowQualityFlag(
                category="体验不佳类",
                subcategory="信息密度极低",
                description=f"检测到套话/AI味词汇 {cliche_count + ai_word_count} 处，信息密度受影响",
                evidence=f"套话模式 {cliche_count} 处，AI味词 {ai_word_count} 处",
                penalty_applied=KUAIMOD_LOW_QUALITY_CATEGORIES["体验不佳类"]["penalty_weight"] * 0.8,
            ))

        return flags

    # ------------------------------------------------------------------
    # 综合评分计算（几何平均，参考 Redpen WQI 方法论）
    # ------------------------------------------------------------------

    def _calculate_composite_score(
        self, dimension_scores: list[DimensionScore], flags: list[LowQualityFlag]
    ) -> float:
        """计算综合评分：5维度几何平均 - 劣质内容扣分"""
        scores = [d.score for d in dimension_scores]
        if not scores:
            return 1.0

        # 几何平均（确保低分维度显著拉低总分）
        product = 1.0
        for s in scores:
            product *= max(s, 0.1)  # 防止0值
        geometric_mean = product ** (1.0 / len(scores))

        # 劣质内容扣分
        total_penalty = 0.0
        for flag in flags:
            total_penalty += flag.penalty_applied * 0.3  # 每个flag扣0.3*weight

        final_score = max(1.0, geometric_mean - total_penalty)
        return round(min(final_score, 4.0), 2)

    def _determine_grade(self, score: float) -> str:
        """确定评分等级"""
        if score >= 3.5:
            return "🟢 优秀"
        elif score >= 2.8:
            return "🟡 良好"
        elif score >= 2.0:
            return "🟠 一般"
        elif score >= 1.5:
            return "🔴 较差"
        else:
            return "⚫ 极差"

    def _generate_improvement_suggestions(
        self, dimension_scores: list[DimensionScore], flags: list[LowQualityFlag]
    ) -> list[str]:
        """生成改进建议（针对最低分维度 + 劣质内容标记）"""
        suggestions = []

        # 按分数排序，取最低2个维度
        sorted_dims = sorted(dimension_scores, key=lambda d: d.score)
        for dim in sorted_dims[:2]:
            suggestions.append(
                f"[{dim.dimension_name}] 当前 {dim.score:.1f} 分 — {dim.evidence}。"
                f"目标提升至 {min(dim.score + 1.0, 4.0):.1f} 分"
            )

        # 劣质内容修复建议
        for flag in flags[:2]:
            suggestions.append(
                f"[KuaiMod-{flag.category}] {flag.description}。"
                f"证据: {flag.evidence}。建议修正以避免内容质量降级"
            )

        return suggestions

    # ------------------------------------------------------------------
    # 主评测入口
    # ------------------------------------------------------------------

    def evaluate(self, text: str, script_path: str = "<inline>") -> ContentQualityReport:
        """执行完整的内容质量评测"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if len(text) < 50:
            return ContentQualityReport(
                script_path=script_path,
                script_length=len(text),
                evaluated_at=now,
                summary="⚠️ 内容过短（<50字符），评测结果可信度低",
            )

        sentences = self._split_sentences(text)
        paragraphs = self._split_paragraphs(text)

        # 5维度评分
        dim_scores = [
            self._evaluate_visual_quality(text, sentences),
            self._evaluate_content_value(text, sentences),
            self._evaluate_emotional_resonance(text, sentences),
            self._evaluate_technical_quality(text, sentences, paragraphs),
            self._evaluate_viral_potential(text, sentences),
        ]

        # KuaiMod 劣质内容检测
        flags = self._detect_low_quality_content(text, sentences)

        # 综合评分
        composite = self._calculate_composite_score(dim_scores, flags)
        grade = self._determine_grade(composite)
        suggestions = self._generate_improvement_suggestions(dim_scores, flags)

        # 生成摘要
        dim_summary = " | ".join(f"{d.dimension_name}:{d.score:.1f}" for d in dim_scores)
        flag_summary = f" | ⚠️ {len(flags)}个劣质标记" if flags else ""
        summary = f"综合评分 {composite:.2f}/4.0 ({grade}) | {dim_summary}{flag_summary}"

        return ContentQualityReport(
            script_path=script_path,
            script_length=len(text),
            evaluated_at=now,
            dimension_scores=dim_scores,
            low_quality_flags=flags,
            composite_score=composite,
            grade=grade,
            summary=summary,
            improvement_suggestions=suggestions,
        )


# ==========================================================================
# 报告格式化输出
# ==========================================================================

def format_report_markdown(report: ContentQualityReport) -> str:
    """Markdown 格式化报告"""
    lines = []
    lines.append("### 📊 内容质量评测报告（KuaiMod + VideoScore-v1.1）")
    lines.append("")
    lines.append(f"- **脚本路径**: {report.script_path}")
    lines.append(f"- **脚本长度**: {report.script_length} 字符")
    lines.append(f"- **评测时间**: {report.evaluated_at}")
    lines.append(f"- **综合评分**: {report.composite_score:.2f}/4.0 {report.grade}")
    lines.append("")
    lines.append("#### 5维度评分明细")
    lines.append("")
    lines.append("| 维度 | 得分 | 锚点参考 | 证据 | 置信度 |")
    lines.append("|------|------|---------|------|--------|")
    for d in report.dimension_scores:
        lines.append(
            f"| {d.dimension_name} | {d.score:.1f} | {d.anchor_reference[:30]}... | {d.evidence} | {d.confidence} |"
        )
    lines.append("")

    if report.low_quality_flags:
        lines.append("#### ⚠️ KuaiMod 劣质内容检测")
        lines.append("")
        lines.append("| 类别 | 子类 | 描述 | 证据 | 扣分权重 |")
        lines.append("|------|------|------|------|---------|")
        for f in report.low_quality_flags:
            lines.append(
                f"| {f.category} | {f.subcategory} | {f.description} | {f.evidence} | {f.penalty_applied:.2f} |"
            )
        lines.append("")

    if report.improvement_suggestions:
        lines.append("#### 改进建议")
        lines.append("")
        for i, s in enumerate(report.improvement_suggestions, 1):
            lines.append(f"{i}. {s}")
        lines.append("")

    lines.append("---")
    lines.append("*评测引擎: KuaiMod (CC BY-SA 4.0) + VideoScore-v1.1 (MIT License) | 作者: 阿洋*")
    return "\n".join(lines)


def format_report_json(report: ContentQualityReport) -> str:
    """JSON 格式化报告"""
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)


# ==========================================================================
# CLI 入口
# ==========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="内容质量评测器（基于 KuaiMod + VideoScore-v1.1 理念）作者: 阿洋"
    )
    parser.add_argument("--script", type=str, help="脚本文件路径")
    parser.add_argument("--text", type=str, help="直接传入脚本文本内容")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="输出格式")
    parser.add_argument("--no-jieba", action="store_true", help="禁用 jieba 分词（降级为字符切分）")
    parser.add_argument("--info", action="store_true", help="显示评测器信息")
    args = parser.parse_args()

    if args.info:
        print("=" * 60)
        print("内容质量评测器 (Content Quality Evaluator)")
        print("作者: 阿洋")
        print("=" * 60)
        print("基于开源项目:")
        print("  1. KuaiMod (快手开源, CC BY-SA 4.0)")
        print("     - 短视频内容质量判别框架")
        print("     - 4类劣质内容 + 15类细粒度分类")
        print("     - https://github.com/KuaiMod/KuaiMod.github.io")
        print("  2. VideoScore-v1.1 (TIGER-Lab, MIT License)")
        print("     - 5维度视频质量评估")
        print("     - 评分范围 1.0-4.0")
        print("     - https://github.com/TIGER-AI-Lab/VideoScore")
        print("=" * 60)
        print("5维度评测体系:")
        for key, dim in VIDEOSCORE_DIMENSIONS.items():
            print(f"  - {dim['name_cn']} ({key}): {dim['description']}")
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

    # 执行评测
    evaluator = ContentQualityEvaluator(use_jieba=not args.no_jieba)
    report = evaluator.evaluate(text, script_path)

    # 输出
    if args.format == "json":
        print(format_report_json(report))
    else:
        print(format_report_markdown(report))


if __name__ == "__main__":
    main()
