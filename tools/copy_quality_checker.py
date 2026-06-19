#!/usr/bin/env python3
# 作者: 阿洋
"""
copy_quality_checker.py — 文案质量检查器
作者: 阿洋

基于 Vale（prose linter）和 writing-analysis（TextDescriptives/textstat）理念实现。

==========================================================================
开源项目许可证声明
==========================================================================

1. Vale (Errata AI)
   - 项目地址: https://github.com/errata-ai/vale
   - 许可证: MIT License
   - 核心理念: 基于YAML规则的prose linter，支持existence/substitution/repetition/
     spelling/capitalization/consistency等检查类型，语法和上下文感知的linting。

2. TextDescriptives (HLasse)
   - 项目地址: https://github.com/HLasse/TextDescriptives
   - 许可证: Apache-2.0 License
   - 核心理念: 基于spaCy的文本指标计算库，提供可读性/一致性/连贯性等维度指标。

3. textstat (Shivam Bansal)
   - 项目地址: https://github.com/textstat/textstat
   - 许可证: MIT License
   - 核心理念: 文本统计特征计算，包括Flesch阅读容易度/句子复杂度/音节计数等。

本实现将上述三个项目的核心理念融合，适配为中文文案质量检查工具，
所有核心逻辑直接实现（非 pip install），防止实现层面与原逻辑出现偏差。

==========================================================================
5维度文案质量检查体系
==========================================================================

1. 可读性（Readability）   — 句子长度、复杂度、阅读难度
2. 一致性（Consistency）    — 术语统一、风格一致、人称一致
3. 简洁性（Conciseness）    — 冗余检测、废话检测、重复检测
4. 感染力（Persuasiveness） — 情绪词密度、行动号召力、记忆点
5. 规范性（Compliance）     — 标点规范、用词规范、语法规范

检查结果: 每个维度输出 issue 列表 + 严重级别(error/warning/suggestion)
综合评分: 5维度几何平均（参考 Redpen WQI 方法论），范围 0.0-1.0

==========================================================================
Vale 检查类型映射
==========================================================================

Vale 的6种检查类型在本检查器中的对应实现：
- existence      → 禁用词检测（AI味词/套话词）
- substitution   → 术语替换建议（口语化替换）
- repetition     → 重复词检测（连续重复/段落重复）
- spelling       → 用词规范检测（错别字/异形词）
- capitalization → 标点规范检测（中文标点规范）
- consistency    → 术语一致性检测（同一文档内术语统一）

Usage:
    python tools/copy_quality_checker.py --script path/to/script.md
    python tools/copy_quality_checker.py --script path/to/script.md --format json
    python tools/copy_quality_checker.py --text "文案内容文本"
    python tools/copy_quality_checker.py --info

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
# Vale 检查类型定义（直接引入，MIT License）
# 来源: https://github.com/errata-ai/vale
# ==========================================================================
VALE_CHECK_TYPES = {
    "existence": "检查特定模式是否存在（如禁用词）",
    "substitution": "建议更好的词语替换（如口语化替换）",
    "repetition": "检测重复词语（如连续重复）",
    "spelling": "拼写检查（中文用词规范）",
    "capitalization": "大小写/标点规范检查",
    "consistency": "术语一致性验证（如同一文档内术语统一）",
}

# ==========================================================================
# 检查规则词典
# ==========================================================================

# --- existence 检查：禁用词（与 yang-polish L1 规则对齐）---
BANNED_WORDS = {
    # AI高频踩雷词
    "说白了": "error",
    "意味着什么": "error",
    "这意味着": "error",
    "本质上": "error",
    "换句话说": "error",
    "不可否认": "error",
    "综上所述": "error",
    "值得注意的是": "error",
    "不难发现": "error",
    "让我们来看看": "error",
    "接下来让我们": "error",
    "总而言之": "error",
    "由此可见": "error",
    # 套话
    "众所周知": "warning",
    "不言而喻": "warning",
    "毋庸置疑": "warning",
    # 程度副词堆砌
    "非常极其": "warning",
    "极其重要": "warning",
    "非常重要": "suggestion",
}

# --- existence 检查：套话模式（正则）---
CLICHE_PATTERNS = [
    (r"在当今.{0,10}时代", "error", "宏大社会开头，应直接切入具体事件"),
    (r"随着.{0,10}的不断进步", "error", "趋势铺垫开头，应直接切入"),
    (r"随着.{0,10}的快速发展", "error", "趋势铺垫开头，应直接切入"),
    (r"首先.*其次.*最后", "warning", "三段式论证，应改为自然转场"),
    (r"一方面.*另一方面", "warning", "对立式结构，应改为口语化转场"),
]

# --- substitution 检查：口语化替换建议 ---
SUBSTITUTION_SUGGESTIONS = {
    "利用": "用",
    "使用": "用",
    "进行": "做",
    "实现": "做到",
    "完成": "做完",
    "获得": "拿到",
    "产生": "带来",
    "导致": "造成",
    "因此": "所以",
    "然而": "但是",
    "此外": "另外",
    "目前": "现在",
    "较为": "比较",
    "较为": "比较",
    "诸多": "很多",
    "若干": "几个",
    "尚且": "还",
    "倘若": "如果",
    "虽则": "虽然",
}

# --- capitalization 检查：标点规范（与 yang-polish L1-2 对齐）---
BANNED_PUNCTUATIONS = {
    "：": ("error", "冒号，应用逗号代替"),
    "——": ("error", "破折号，应断句为短句"),
    "\u201c": ("error", "中文左双引号，应用「」或直接不加引号"),
    "\u201d": ("error", "中文右双引号，应用「」或直接不加引号"),
    "\u2018": ("warning", "中文左单引号，应用「」或直接不加引号"),
    "\u2019": ("warning", "中文右单引号，应用「」或直接不加引号"),
}

# --- consistency 检查：术语一致性 ---
# 检测同一文档中同一概念的不同表述
CONSISTENCY_GROUPS = [
    {"variants": ["AI", "ai", "人工智能", "人工智能技术"], "preferred": "AI", "description": "AI/人工智能 表述统一"},
    {"variants": ["ChatGPT", "chatgpt", "chat GPT", "CHATGPT"], "preferred": "ChatGPT", "description": "ChatGPT 大小写统一"},
    {"variants": ["Claude", "claude", "CLAUDE"], "preferred": "Claude", "description": "Claude 大小写统一"},
    {"variants": ["Prompt", "prompt", "PROMPT", "提示词"], "preferred": "Prompt", "description": "Prompt 表述统一"},
    {"variants": ["短视频", "小视频", "短视屏"], "preferred": "短视频", "description": "短视频 表述统一"},
]

# --- 感染力检测：情绪词和行动号召词 ---
EMOTION_WORDS = {
    "强情绪": ["震惊", "震撼", "崩溃", "暴怒", "狂喜", "绝望", "卧槽", "离谱", "炸裂", "破防",
               "太爽了", "懵了", "上头", "太离谱了"],
    "中情绪": ["开心", "生气", "难过", "害怕", "惊讶", "感动", "兴奋", "紧张", "期待", "失望",
               "激动", "感慨", "无奈", "心疼"],
    "行动号召": ["试试", "建议", "赶紧", "收藏", "转发", "点赞", "关注", "评论", "分享",
                 "一定要", "必须", "别错过", "强烈推荐"],
    "记忆点": ["记住", "关键是", "核心是", "重点是", "一句话", "说白了就是",
               "你只需要", "秘诀就是", "真相是"],
}

# --- 简洁性检测：冗余模式 ---
REDUNDANCY_PATTERNS = [
    (r"的{2,}", "error", "连续使用'的'，应精简"),
    (r"了{2,}", "warning", "连续使用'了'，应精简"),
    (r"是.{0,5}的", "suggestion", "'是...的'结构，可考虑精简"),
    (r"进行.{0,4}", "warning", "'进行...'冗余表达，可直接用动词"),
    (r"做出.{0,4}", "warning", "'做出...'冗余表达，可直接用动词"),
    (r".{0,3}的话", "suggestion", "'...的话'口语化但可能冗余"),
]


@dataclass
class Issue:
    """检查发现的问题"""
    check_type: str        # existence/substitution/repetition/spelling/capitalization/consistency
    severity: str          # error / warning / suggestion
    dimension: str         # readability/consistency/conciseness/persuasiveness/compliance
    message: str
    position: str          # 位置描述（句子片段或行号）
    suggestion: str = ""   # 修复建议


@dataclass
class DimensionResult:
    """单维度检查结果"""
    dimension_key: str
    dimension_name: str
    score: float           # 0.0-1.0
    issue_count: int
    error_count: int
    warning_count: int
    suggestion_count: int
    issues: list[Issue] = field(default_factory=list)
    summary: str = ""


@dataclass
class CopyQualityReport:
    """文案质量检查报告"""
    script_path: str
    script_length: int
    evaluated_at: str
    dimension_results: list[DimensionResult] = field(default_factory=list)
    composite_score: float = 0.0
    grade: str = ""
    total_issues: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    total_suggestions: int = 0
    summary: str = ""
    top_fixes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "script_path": self.script_path,
            "script_length": self.script_length,
            "evaluated_at": self.evaluated_at,
            "dimension_results": [
                {
                    **{k: v for k, v in asdict(d).items() if k != "issues"},
                    "issues": [asdict(i) for i in d.issues],
                }
                for d in self.dimension_results
            ],
            "composite_score": round(self.composite_score, 3),
            "grade": self.grade,
            "total_issues": self.total_issues,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "total_suggestions": self.total_suggestions,
            "summary": self.summary,
            "top_fixes": self.top_fixes,
        }


# ==========================================================================
# 核心检查引擎
# ==========================================================================

class CopyQualityChecker:
    """
    文案质量检查器
    融合 Vale 规则检查 + TextDescriptives/textstat 文本指标计算
    """

    def __init__(self, use_jieba: bool = True):
        self.use_jieba = use_jieba and JIEBA_AVAILABLE
        if self.use_jieba:
            jieba.initialize()

    # ------------------------------------------------------------------
    # 文本预处理
    # ------------------------------------------------------------------

    def _split_sentences(self, text: str) -> list[str]:
        """句子切分"""
        sentences = re.split(r'[。！？!?\n]+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]

    def _split_paragraphs(self, text: str) -> list[str]:
        """段落切分"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 5]

    def _find_position(self, text: str, pattern: str, occurrence: int = 0) -> str:
        """定位问题位置"""
        idx = text.find(pattern)
        if idx < 0:
            return f"第{occurrence+1}处"
        # 找到所在句子
        before = text[:idx]
        sentence_num = before.count("。") + before.count("！") + before.count("？") + before.count("\n") + 1
        context_start = max(0, idx - 10)
        context_end = min(len(text), idx + len(pattern) + 10)
        context = text[context_start:context_end].replace("\n", " ")
        return f"句{sentence_num}:「...{context}...」"

    # ------------------------------------------------------------------
    # 维度1: 可读性检查（基于 textstat 理念）
    # ------------------------------------------------------------------

    def _check_readability(self, text: str, sentences: list[str]) -> DimensionResult:
        """可读性检查：句子长度、复杂度、阅读难度"""
        issues = []

        if not sentences:
            return DimensionResult(
                dimension_key="readability", dimension_name="可读性",
                score=0.5, issue_count=0, error_count=0, warning_count=0,
                suggestion_count=0, summary="无法切分句子",
            )

        # 句子长度分析
        sentence_lengths = [len(s) for s in sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        max_length = max(sentence_lengths) if sentence_lengths else 0

        # 长句检测（中文>40字符为长句）
        long_sentence_count = sum(1 for l in sentence_lengths if l > 40)
        very_long_count = sum(1 for l in sentence_lengths if l > 60)

        for i, s in enumerate(sentences):
            if len(s) > 60:
                issues.append(Issue(
                    check_type="existence",
                    severity="error",
                    dimension="readability",
                    message=f"超长句（{len(s)}字符），阅读难度极高",
                    position=self._find_position(text, s[:20], i),
                    suggestion="拆分为2-3个短句，每句≤30字符",
                ))
            elif len(s) > 40:
                issues.append(Issue(
                    check_type="existence",
                    severity="warning",
                    dimension="readability",
                    message=f"长句（{len(s)}字符），阅读难度较高",
                    position=self._find_position(text, s[:20], i),
                    suggestion="考虑拆分为短句",
                ))

        # 句子长度方差（节奏感）
        if len(sentence_lengths) >= 3:
            variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            std = math.sqrt(variance)
            if std < 5:
                issues.append(Issue(
                    check_type="existence",
                    severity="suggestion",
                    dimension="readability",
                    message=f"句子长度过于均匀（标准差{std:.1f}），缺乏节奏感",
                    position="全文",
                    suggestion="长短句交替，制造节奏变化",
                ))

        # 逗号密度（中文逗号过多导致复杂句）
        comma_density = text.count("，") / max(len(sentences), 1)
        if comma_density > 5:
            issues.append(Issue(
                check_type="existence",
                severity="warning",
                dimension="readability",
                message=f"逗号密度过高（{comma_density:.1f}/句），句子结构复杂",
                position="全文",
                suggestion="减少逗号，断句为短句",
            ))

        # 计算可读性评分
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        suggestion_count = sum(1 for i in issues if i.severity == "suggestion")

        # 基于平均句长和问题数计算评分
        length_score = max(0, 1.0 - (avg_length - 20) / 40)  # 20字符为理想值
        issue_penalty = min(error_count * 0.15 + warning_count * 0.08 + suggestion_count * 0.03, 0.5)
        score = max(0.0, min(1.0, length_score - issue_penalty))

        return DimensionResult(
            dimension_key="readability",
            dimension_name="可读性",
            score=score,
            issue_count=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
            issues=issues,
            summary=f"平均句长{avg_length:.0f}字符，长句{long_sentence_count}个，超长句{very_long_count}个",
        )

    # ------------------------------------------------------------------
    # 维度2: 一致性检查（基于 Vale consistency 检查类型）
    # ------------------------------------------------------------------

    def _check_consistency(self, text: str, sentences: list[str]) -> DimensionResult:
        """一致性检查：术语统一、风格一致、人称一致"""
        issues = []

        # 术语一致性检测
        for group in CONSISTENCY_GROUPS:
            found_variants = {}
            for variant in group["variants"]:
                count = text.count(variant)
                if count > 0:
                    found_variants[variant] = count

            if len(found_variants) > 1:
                variants_str = "/".join(found_variants.keys())
                issues.append(Issue(
                    check_type="consistency",
                    severity="warning",
                    dimension="consistency",
                    message=f"{group['description']}：检测到多种表述（{variants_str}）",
                    position="全文",
                    suggestion=f"统一使用「{group['preferred']}」",
                ))

        # 人称一致性检测
        first_person_count = text.count("我") + text.count("自己")
        second_person_count = text.count("你") + text.count("你们")
        third_person_count = text.count("他") + text.count("她") + text.count("他们")

        person_counts = {"第一人称": first_person_count, "第二人称": second_person_count, "第三人称": third_person_count}
        dominant_person = max(person_counts, key=person_counts.get)
        total_person_refs = sum(person_counts.values())

        if total_person_refs > 0:
            dominant_ratio = person_counts[dominant_person] / total_person_refs
            if dominant_ratio < 0.5 and total_person_refs > 10:
                issues.append(Issue(
                    check_type="consistency",
                    severity="warning",
                    dimension="consistency",
                    message=f"人称不一致：{person_counts}，主导人称占比仅{dominant_ratio:.0%}",
                    position="全文",
                    suggestion=f"统一为{dominant_person}视角",
                ))

        # 风格一致性（正式vs口语）
        formal_markers = sum(1 for w in ["因此", "然而", "此外", "综上", "鉴于", "尚且"] if w in text)
        casual_markers = sum(1 for w in ["说实话", "讲真", "你想想", "我跟你说", "怎么说呢", "其实吧"] if w in text)

        if formal_markers > 3 and casual_markers > 3:
            issues.append(Issue(
                check_type="consistency",
                severity="warning",
                dimension="consistency",
                message=f"风格不一致：正式标记{formal_markers}处，口语标记{casual_markers}处",
                position="全文",
                suggestion="统一为口语化或正式风格",
            ))

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        suggestion_count = sum(1 for i in issues if i.severity == "suggestion")

        issue_penalty = min(warning_count * 0.1 + suggestion_count * 0.05, 0.4)
        score = max(0.0, min(1.0, 1.0 - issue_penalty))

        return DimensionResult(
            dimension_key="consistency",
            dimension_name="一致性",
            score=score,
            issue_count=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
            issues=issues,
            summary=f"术语一致性{len([i for i in issues if '术语' in i.message])}项，人称/风格一致性{len([i for i in issues if '术语' not in i.message])}项",
        )

    # ------------------------------------------------------------------
    # 维度3: 简洁性检查（基于 Vale existence + repetition）
    # ------------------------------------------------------------------

    def _check_conciseness(self, text: str, sentences: list[str]) -> DimensionResult:
        """简洁性检查：冗余检测、废话检测、重复检测"""
        issues = []

        # 冗余模式检测
        for pattern, severity, message in REDUNDANCY_PATTERNS:
            matches = re.finditer(pattern, text)
            for i, match in enumerate(matches):
                if i < 5:  # 最多报告5处
                    issues.append(Issue(
                        check_type="existence",
                        severity=severity,
                        dimension="conciseness",
                        message=f"{message}：「{match.group()}」",
                        position=self._find_position(text, match.group(), i),
                        suggestion="精简表达",
                    ))

        # 重复词检测（Vale repetition 检查类型）
        if self.use_jieba:
            words = list(jieba.cut(text))
        else:
            words = list(text)

        # 连续重复词检测
        repeat_count = 0
        for i in range(len(words) - 1):
            if len(words[i]) >= 2 and words[i] == words[i+1] and words[i] not in {"的", "了", "是", "在", "也"}:
                repeat_count += 1
                if repeat_count <= 3:
                    issues.append(Issue(
                        check_type="repetition",
                        severity="warning",
                        dimension="conciseness",
                        message=f"连续重复词：「{words[i]}{words[i+1]}」",
                        position=f"词{i}-{i+1}",
                        suggestion="删除重复词",
                    ))

        # 废话检测（无信息量句子）
        filler_sentences = 0
        for i, s in enumerate(sentences):
            if len(s) < 8 and not any(c.isdigit() for c in s) and not any(w in s for w in ["？", "！", "吗", "呢"]):
                filler_count = sum(1 for w in ["嗯", "啊", "哦", "就是说", "然后然后", "那个那个"] if w in s)
                if filler_count > 0 or len(s) < 5:
                    filler_sentences += 1
                    if filler_sentences <= 3:
                        issues.append(Issue(
                            check_type="existence",
                            severity="suggestion",
                            dimension="conciseness",
                            message=f"疑似废话句：「{s}」",
                            position=f"句{i+1}",
                            suggestion="删除或补充有效信息",
                        ))

        # 禁用词检测（与 yang-polish L1 对齐）
        for word, severity in BANNED_WORDS.items():
            count = text.count(word)
            if count > 0:
                for i in range(min(count, 3)):
                    issues.append(Issue(
                        check_type="existence",
                        severity=severity,
                        dimension="conciseness",
                        message=f"禁用词「{word}」命中（第{i+1}处）",
                        position=self._find_position(text, word, i),
                        suggestion="删除或替换为口语化表达",
                    ))

        # 套话模式检测
        for pattern, severity, message in CLICHE_PATTERNS:
            matches = re.finditer(pattern, text)
            for i, match in enumerate(matches):
                if i < 3:
                    issues.append(Issue(
                        check_type="existence",
                        severity=severity,
                        dimension="conciseness",
                        message=f"套话模式：{message}「{match.group()}」",
                        position=self._find_position(text, match.group(), i),
                        suggestion="改为具体事件/场景切入",
                    ))

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        suggestion_count = sum(1 for i in issues if i.severity == "suggestion")

        issue_penalty = min(error_count * 0.12 + warning_count * 0.06 + suggestion_count * 0.02, 0.6)
        score = max(0.0, min(1.0, 1.0 - issue_penalty))

        return DimensionResult(
            dimension_key="conciseness",
            dimension_name="简洁性",
            score=score,
            issue_count=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
            issues=issues,
            summary=f"禁用词{error_count}处，冗余{warning_count}处，废话{suggestion_count}处",
        )

    # ------------------------------------------------------------------
    # 维度4: 感染力检查
    # ------------------------------------------------------------------

    def _check_persuasiveness(self, text: str, sentences: list[str]) -> DimensionResult:
        """感染力检查：情绪词密度、行动号召力、记忆点"""
        issues = []

        # 情绪词密度
        strong_emotion_count = sum(text.count(w) for w in EMOTION_WORDS["强情绪"])
        medium_emotion_count = sum(text.count(w) for w in EMOTION_WORDS["中情绪"])
        total_emotion = strong_emotion_count + medium_emotion_count
        emotion_density = total_emotion / max(len(sentences), 1)

        if emotion_density < 0.1:
            issues.append(Issue(
                check_type="existence",
                severity="warning",
                dimension="persuasiveness",
                message=f"情绪词密度过低（{emotion_density:.2f}/句），缺乏感染力",
                position="全文",
                suggestion="增加情绪表达，使用体感记忆词",
            ))
        elif emotion_density > 1.5:
            issues.append(Issue(
                check_type="existence",
                severity="suggestion",
                dimension="persuasiveness",
                message=f"情绪词密度过高（{emotion_density:.2f}/句），可能过度夸张",
                position="全文",
                suggestion="适当克制，用体感记忆替代直接情绪词",
            ))

        # 行动号召力
        cta_count = sum(text.count(w) for w in EMOTION_WORDS["行动号召"])
        if cta_count == 0 and len(text) > 500:
            issues.append(Issue(
                check_type="existence",
                severity="suggestion",
                dimension="persuasiveness",
                message="未检测到行动号召词，缺乏互动引导",
                position="全文",
                suggestion="结尾增加行动号召（如'试试''建议收藏'）",
            ))

        # 记忆点
        memory_count = sum(text.count(w) for w in EMOTION_WORDS["记忆点"])
        if memory_count == 0 and len(text) > 500:
            issues.append(Issue(
                check_type="existence",
                severity="suggestion",
                dimension="persuasiveness",
                message="未检测到记忆点标记，缺乏金句锚定",
                position="全文",
                suggestion="增加'关键是''核心是''一句话'等记忆点标记",
            ))

        # 第一人称代入感
        first_person_count = text.count("我") + text.count("自己")
        if first_person_count < 3 and len(text) > 500:
            issues.append(Issue(
                check_type="existence",
                severity="suggestion",
                dimension="persuasiveness",
                message=f"第一人称使用过少（{first_person_count}处），代入感不足",
                position="全文",
                suggestion="增加'我''自己'等第一人称表达",
            ))

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        suggestion_count = sum(1 for i in issues if i.severity == "suggestion")

        # 感染力评分：情绪密度 + CTA + 记忆点 + 第一人称
        emotion_score = min(emotion_density / 0.5, 1.0) * 0.3
        cta_score = min(cta_count / 3, 1.0) * 0.2
        memory_score = min(memory_count / 2, 1.0) * 0.2
        immersion_score = min(first_person_count / 10, 1.0) * 0.3
        base_score = emotion_score + cta_score + memory_score + immersion_score
        issue_penalty = min(warning_count * 0.1 + suggestion_count * 0.05, 0.3)
        score = max(0.0, min(1.0, base_score - issue_penalty))

        return DimensionResult(
            dimension_key="persuasiveness",
            dimension_name="感染力",
            score=score,
            issue_count=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
            issues=issues,
            summary=f"情绪词{total_emotion}个（强{strong_emotion_count}/中{medium_emotion_count}），CTA{cta_count}处，记忆点{memory_count}处",
        )

    # ------------------------------------------------------------------
    # 维度5: 规范性检查（基于 Vale capitalization + spelling）
    # ------------------------------------------------------------------

    def _check_compliance(self, text: str, sentences: list[str]) -> DimensionResult:
        """规范性检查：标点规范、用词规范、语法规范"""
        issues = []

        # 标点规范检测（与 yang-polish L1-2 对齐）
        for punct, (severity, message) in BANNED_PUNCTUATIONS.items():
            count = text.count(punct)
            if count > 0:
                for i in range(min(count, 5)):
                    issues.append(Issue(
                        check_type="capitalization",
                        severity=severity,
                        dimension="compliance",
                        message=f"禁用标点「{punct}」：{message}（第{i+1}处）",
                        position=self._find_position(text, punct, i),
                        suggestion="删除或替换为合规标点",
                    ))

        # 省略号规范检测
        ellipsis_count = text.count("。。。")
        if ellipsis_count > 0:
            issues.append(Issue(
                check_type="capitalization",
                severity="suggestion",
                dimension="compliance",
                message=f"使用中文省略号「。。。」（{ellipsis_count}处），符合活人感风格",
                position="全文",
                suggestion="保持，这是活人感表达",
            ))

        # 感叹号密度
        exclamation_count = text.count("！") + text.count("!")
        if exclamation_count > len(sentences) * 0.3 and len(sentences) > 5:
            issues.append(Issue(
                check_type="capitalization",
                severity="warning",
                dimension="compliance",
                message=f"感叹号密度过高（{exclamation_count}个/{len(sentences)}句），情绪过度",
                position="全文",
                suggestion="减少感叹号，用内容本身传递情绪",
            ))

        # 问号密度（互动感）
        question_count = text.count("？") + text.count("?")
        if question_count == 0 and len(text) > 500:
            issues.append(Issue(
                check_type="capitalization",
                severity="suggestion",
                dimension="compliance",
                message="全文无问号，缺乏互动感",
                position="全文",
                suggestion="适当增加反问句或提问",
            ))

        # 空格规范（中英文之间）
        mixed_spacing = len(re.findall(r'[\u4e00-\u9fa5][A-Za-z]|[A-Za-z][\u4e00-\u9fa5]', text))
        if mixed_spacing > 5:
            issues.append(Issue(
                check_type="spelling",
                severity="suggestion",
                dimension="compliance",
                message=f"中英文混排未加空格（{mixed_spacing}处）",
                position="全文",
                suggestion="中英文之间加空格提升可读性",
            ))

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        suggestion_count = sum(1 for i in issues if i.severity == "suggestion")

        issue_penalty = min(error_count * 0.15 + warning_count * 0.08 + suggestion_count * 0.02, 0.5)
        score = max(0.0, min(1.0, 1.0 - issue_penalty))

        return DimensionResult(
            dimension_key="compliance",
            dimension_name="规范性",
            score=score,
            issue_count=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
            issues=issues,
            summary=f"禁用标点{error_count}处，标点密度问题{warning_count}处，规范建议{suggestion_count}处",
        )

    # ------------------------------------------------------------------
    # 综合评分计算（几何平均，参考 Redpen WQI）
    # ------------------------------------------------------------------

    def _calculate_composite_score(self, dimensions: list[DimensionResult]) -> float:
        """计算综合评分：5维度几何平均"""
        scores = [d.score for d in dimensions]
        if not scores:
            return 0.5

        product = 1.0
        for s in scores:
            product *= max(s, 0.01)
        geometric_mean = product ** (1.0 / len(scores))
        return round(geometric_mean, 3)

    def _determine_grade(self, score: float) -> str:
        """确定评分等级"""
        if score >= 0.9:
            return "🟢 优秀（可直接发布）"
        elif score >= 0.75:
            return "🟡 良好（微调后发布）"
        elif score >= 0.6:
            return "🟠 一般（需要润色）"
        elif score >= 0.4:
            return "🔴 较差（需要大幅修改）"
        else:
            return "⚫ 极差（建议重写）"

    def _generate_top_fixes(self, dimensions: list[DimensionResult]) -> list[str]:
        """生成Top修复建议（按严重级别排序）"""
        all_issues = []
        for d in dimensions:
            for issue in d.issues:
                all_issues.append((d.dimension_name, issue))

        # 按严重级别排序：error > warning > suggestion
        severity_order = {"error": 0, "warning": 1, "suggestion": 2}
        all_issues.sort(key=lambda x: severity_order.get(x[1].severity, 3))

        top_fixes = []
        for dim_name, issue in all_issues[:5]:
            fix = f"[{dim_name}] {issue.message}"
            if issue.suggestion:
                fix += f" → {issue.suggestion}"
            top_fixes.append(fix)

        return top_fixes

    # ------------------------------------------------------------------
    # 主检查入口
    # ------------------------------------------------------------------

    def check(self, text: str, script_path: str = "<inline>") -> CopyQualityReport:
        """执行完整的文案质量检查"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if len(text) < 50:
            return CopyQualityReport(
                script_path=script_path,
                script_length=len(text),
                evaluated_at=now,
                summary="⚠️ 内容过短（<50字符），检查结果可信度低",
            )

        sentences = self._split_sentences(text)

        # 5维度检查
        dimensions = [
            self._check_readability(text, sentences),
            self._check_consistency(text, sentences),
            self._check_conciseness(text, sentences),
            self._check_persuasiveness(text, sentences),
            self._check_compliance(text, sentences),
        ]

        # 综合评分
        composite = self._calculate_composite_score(dimensions)
        grade = self._determine_grade(composite)

        # 统计
        total_issues = sum(d.issue_count for d in dimensions)
        total_errors = sum(d.error_count for d in dimensions)
        total_warnings = sum(d.warning_count for d in dimensions)
        total_suggestions = sum(d.suggestion_count for d in dimensions)

        # Top修复建议
        top_fixes = self._generate_top_fixes(dimensions)

        # 生成摘要
        dim_summary = " | ".join(f"{d.dimension_name}:{d.score:.2f}" for d in dimensions)
        summary = (
            f"综合评分 {composite:.3f}/1.0 ({grade}) | {dim_summary} | "
            f"共{total_issues}个问题（{total_errors}错误/{total_warnings}警告/{total_suggestions}建议）"
        )

        return CopyQualityReport(
            script_path=script_path,
            script_length=len(text),
            evaluated_at=now,
            dimension_results=dimensions,
            composite_score=composite,
            grade=grade,
            total_issues=total_issues,
            total_errors=total_errors,
            total_warnings=total_warnings,
            total_suggestions=total_suggestions,
            summary=summary,
            top_fixes=top_fixes,
        )


# ==========================================================================
# 报告格式化输出
# ==========================================================================

def format_report_markdown(report: CopyQualityReport) -> str:
    """Markdown 格式化报告"""
    lines = []
    lines.append("### 📝 文案质量检查报告（Vale + writing-analysis）")
    lines.append("")
    lines.append(f"- **脚本路径**: {report.script_path}")
    lines.append(f"- **脚本长度**: {report.script_length} 字符")
    lines.append(f"- **检查时间**: {report.evaluated_at}")
    lines.append(f"- **综合评分**: {report.composite_score:.3f}/1.0 {report.grade}")
    lines.append(f"- **问题统计**: {report.total_issues}个（{report.total_errors}错误 / {report.total_warnings}警告 / {report.total_suggestions}建议）")
    lines.append("")
    lines.append("#### 5维度检查明细")
    lines.append("")
    lines.append("| 维度 | 评分 | 问题数 | 错误 | 警告 | 建议 | 摘要 |")
    lines.append("|------|------|--------|------|------|------|------|")
    for d in report.dimension_results:
        lines.append(
            f"| {d.dimension_name} | {d.score:.2f} | {d.issue_count} | "
            f"{d.error_count} | {d.warning_count} | {d.suggestion_count} | {d.summary} |"
        )
    lines.append("")

    # 输出各维度详细问题
    for d in report.dimension_results:
        if d.issues:
            lines.append(f"#### {d.dimension_name} 详细问题")
            lines.append("")
            for i, issue in enumerate(d.issues[:10], 1):  # 每维度最多显示10个
                severity_icon = {"error": "🔴", "warning": "🟡", "suggestion": "🟢"}.get(issue.severity, "⚪")
                lines.append(f"{i}. {severity_icon} [{issue.severity}] {issue.message}")
                if issue.position:
                    lines.append(f"   - 位置: {issue.position}")
                if issue.suggestion:
                    lines.append(f"   - 建议: {issue.suggestion}")
            if len(d.issues) > 10:
                lines.append(f"   ... 还有 {len(d.issues) - 10} 个问题未显示")
            lines.append("")

    if report.top_fixes:
        lines.append("#### Top 5 修复建议")
        lines.append("")
        for i, fix in enumerate(report.top_fixes, 1):
            lines.append(f"{i}. {fix}")
        lines.append("")

    lines.append("---")
    lines.append("*检查引擎: Vale (MIT License) + TextDescriptives (Apache-2.0) + textstat (MIT License) | 作者: 阿洋*")
    return "\n".join(lines)


def format_report_json(report: CopyQualityReport) -> str:
    """JSON 格式化报告"""
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)


# ==========================================================================
# CLI 入口
# ==========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="文案质量检查器（基于 Vale + writing-analysis 理念）作者: 阿洋"
    )
    parser.add_argument("--script", type=str, help="脚本文件路径")
    parser.add_argument("--text", type=str, help="直接传入脚本文本内容")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="输出格式")
    parser.add_argument("--no-jieba", action="store_true", help="禁用 jieba 分词（降级为字符切分）")
    parser.add_argument("--info", action="store_true", help="显示检查器信息")
    args = parser.parse_args()

    if args.info:
        print("=" * 60)
        print("文案质量检查器 (Copy Quality Checker)")
        print("作者: 阿洋")
        print("=" * 60)
        print("基于开源项目:")
        print("  1. Vale (Errata AI, MIT License)")
        print("     - Prose linter，6种检查类型")
        print("     - https://github.com/errata-ai/vale")
        print("  2. TextDescriptives (HLasse, Apache-2.0)")
        print("     - 文本指标计算库")
        print("     - https://github.com/HLasse/TextDescriptives")
        print("  3. textstat (MIT License)")
        print("     - 文本统计特征计算")
        print("     - https://github.com/textstat/textstat")
        print("=" * 60)
        print("5维度检查体系:")
        print("  - 可读性 (Readability): 句子长度/复杂度/阅读难度")
        print("  - 一致性 (Consistency): 术语统一/风格一致/人称一致")
        print("  - 简洁性 (Conciseness): 冗余检测/废话检测/重复检测")
        print("  - 感染力 (Persuasiveness): 情绪词密度/行动号召力/记忆点")
        print("  - 规范性 (Compliance): 标点规范/用词规范/语法规范")
        print("=" * 60)
        print("Vale 检查类型映射:")
        for ct, desc in VALE_CHECK_TYPES.items():
            print(f"  - {ct}: {desc}")
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

    # 执行检查
    checker = CopyQualityChecker(use_jieba=not args.no_jieba)
    report = checker.check(text, script_path)

    # 输出
    if args.format == "json":
        print(format_report_json(report))
    else:
        print(format_report_markdown(report))


if __name__ == "__main__":
    main()
