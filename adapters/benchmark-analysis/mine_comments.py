# 作者: 阿洋
"""高赞评论金句挖掘器 —— 把"几千几万人愿意点赞的评论"转成标题 / 选题候选。

输入  : scrape_comments.py 产出的 comments.json
输出  : comment_mining.json，含
        - top_comments          按点赞排序的高赞评论（去重、去水）
        - resonance_clusters    高赞评论的主题聚类（基于关键词共现，零模型依赖）
        - title_candidates      由高赞评论直接改写的视频标题候选
        - topic_candidates      由高赞评论暴露的需求/争议提炼的选题候选
        - emotion_signals       高赞评论里反复出现的情绪词信号
逻辑依据：高赞评论是"已被规模化验证愿意接受"的表达，是最低风险的标题/选题来源。

零第三方硬依赖；若存在 jieba 则启用更准的中文分词，否则回退到字符级 n-gram。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

# 中文常见情绪 / 共鸣信号词（用于标注高赞评论的情绪能量）
EMOTION_WORDS = [
    "\u592a\u771f\u5b9e", "\u592a\u51c6\u4e86", "\u8bf4\u51fa\u4e86", "\u5fc3\u9178", "\u6cea\u76ee", "\u54ed\u4e86", "\u611f\u540c\u8eab\u53d7",
    "\u62b1\u6b49", "\u751f\u6c14", "\u592a\u96be\u4e86", "\u5171\u9e23", "\u4e2d\u80af", "\u9192\u4e86", "\u6cbb\u6108",
    "\u70b8\u88c2", "\u9707\u60ca", "\u79bb\u8c31", "\u5984\u60f3", "\u62b1\u4f4f", "\u5c45\u7136", "\u771f\u7684\u662f",
    "\u5c31\u662f\u6211", "\u8bf4\u7684\u5c31\u662f\u6211", "\u4e3a\u4ec0\u4e48", "\u600e\u4e48\u529e", "\u7edd\u4e86",
]

# 停用词（聚类时过滤）
STOPWORDS = set("""的 了 是 我 你 他 她 它 们 也 在 和 与 就 都 而 及 这 那 有 啊 吧 呢 吗 嘛 把 被 给 让 对 跟 向 从
一个 不 没 很 太 真 还 又 再 更 最 会 能 要 想 说 看 做 个 上 下 里 中 之 其 以 为 等 啊啊 哈哈 哈哈哈""".split())

INJECTION_HINTS = [
    "ignore previous", "system prompt", "you are now", "忽略以上", "忽略之前", "扮演", "越狱",
    "http://", "https://", "加微信", "加v", "私聊", "扫码",
]


def _load_comments(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("comments", []) if isinstance(data, dict) else (data or [])


def _is_low_value(text: str) -> bool:
    t = text.strip()
    if len(t) < 4:
        return True
    # 纯表情 / 纯标点
    if re.fullmatch(r"[\W_]+", t):
        return True
    # 疑似注入 / 引流
    low = t.lower()
    if any(h in low for h in INJECTION_HINTS):
        return True
    return False


def _tokens(text: str):
    try:
        import jieba
        return [w for w in jieba.cut(text) if len(w) >= 2 and w not in STOPWORDS]
    except ImportError:
        # 回退：2-gram 字符
        chars = re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]", text)
        return ["".join(chars[i:i+2]) for i in range(len(chars) - 1) if "".join(chars[i:i+2]) not in STOPWORDS]


def rank_and_dedup(comments: list[dict], top_n: int = 30) -> list[dict]:
    seen = set()
    cleaned = []
    for c in comments:
        text = (c.get("content") or c.get("text") or "").strip()
        if _is_low_value(text):
            continue
        key = text[:60]
        if key in seen:
            continue
        seen.add(key)
        likes = c.get("likes", 0)
        try:
            likes = int(likes)
        except (ValueError, TypeError):
            likes = 0
        cleaned.append({"content": text, "likes": likes, "reply_count": c.get("reply_count", 0)})
    cleaned.sort(key=lambda x: (x["likes"], x["reply_count"], len(x["content"])), reverse=True)
    return cleaned[:top_n]


def cluster_by_keyword(top_comments: list[dict], max_clusters: int = 6) -> list[dict]:
    """基于高频关键词的轻量聚类：把含同一高频词的评论归到一组。"""
    kw_counter = Counter()
    per_comment_tokens = []
    for c in top_comments:
        toks = _tokens(c["content"])
        per_comment_tokens.append(set(toks))
        kw_counter.update(set(toks))

    top_keywords = [w for w, n in kw_counter.most_common(max_clusters * 2) if n >= 2]
    clusters = []
    used_idx = set()
    for kw in top_keywords:
        members = []
        weight = 0
        for i, toks in enumerate(per_comment_tokens):
            if kw in toks and i not in used_idx:
                members.append(top_comments[i]["content"])
                weight += top_comments[i]["likes"]
        if len(members) >= 2:
            for i, toks in enumerate(per_comment_tokens):
                if kw in toks:
                    used_idx.add(i)
            clusters.append({"keyword": kw, "weight_likes": weight, "size": len(members), "samples": members[:4]})
        if len(clusters) >= max_clusters:
            break
    clusters.sort(key=lambda x: x["weight_likes"], reverse=True)
    return clusters


def _to_title(comment: str) -> str:
    """把一条高赞评论改写成视频/笔记标题（保留其情绪与措辞，做轻度收口）。"""
    t = re.sub(r"\s+", "", comment).strip()
    t = re.split(r"[。！!？?\n]", t)[0]  # 取第一句作主干
    if len(t) > 28:
        t = t[:28]
    return t


def derive_titles(top_comments: list[dict], n: int = 8) -> list[dict]:
    out = []
    for c in top_comments[:n]:
        title = _to_title(c["content"])
        if len(title) < 4:
            continue
        out.append({
            "title": title,
            "source_likes": c["likes"],
            "rationale": "\u9ad8\u8d5e\u8bc4\u8bba\u539f\u53e5\u6539\u5199\uff08\u5df2\u88ab {} \u4eba\u70b9\u8d5e\u9a8c\u8bc1\uff09".format(c["likes"]),
        })
    return out


def derive_topics(clusters: list[dict], n: int = 6) -> list[dict]:
    out = []
    for cl in clusters[:n]:
        out.append({
            "topic": "\u56f4\u7ed5\u300c{}\u300d\u7684\u9700\u6c42/\u4e89\u8bae\u5c55\u5f00\u4e00\u671f".format(cl["keyword"]),
            "evidence": "{} \u6761\u9ad8\u8d5e\u8bc4\u8bba\u96c6\u4e2d\u63d0\u53ca\uff0c\u5408\u8ba1\u70b9\u8d5e {}".format(cl["size"], cl["weight_likes"]),
            "angle_hint": cl["samples"][0] if cl["samples"] else "",
        })
    return out


def detect_emotion_signals(top_comments: list[dict]) -> list[dict]:
    counter = Counter()
    for c in top_comments:
        for w in EMOTION_WORDS:
            if w in c["content"]:
                counter[w] += 1
    return [{"signal": w, "count": n} for w, n in counter.most_common(10)]


def mine(comments_path: str, top_n: int = 30) -> dict:
    comments = _load_comments(comments_path)
    top = rank_and_dedup(comments, top_n=top_n)
    clusters = cluster_by_keyword(top)
    return {
        "source": os.path.basename(comments_path),
        "total_comments_in": len(comments),
        "top_comments": top,
        "resonance_clusters": clusters,
        "title_candidates": derive_titles(top),
        "topic_candidates": derive_topics(clusters),
        "emotion_signals": detect_emotion_signals(top),
        "note": "title/topic 候选源自高赞评论，是经规模化验证的低风险选题与标题来源；使用时仍需结合人设与赛道判断。",
    }


def main():
    parser = argparse.ArgumentParser(description="高赞评论金句挖掘器（评论→标题/选题）")
    parser.add_argument("comments_json", type=str, help="comments.json 路径")
    parser.add_argument("--output", type=str, required=True, help="输出 JSON 路径")
    parser.add_argument("--top-n", type=int, default=30, help="参与挖掘的高赞评论数量")
    args = parser.parse_args()

    if not os.path.isfile(args.comments_json):
        print(f"评论文件不存在: {args.comments_json}")
        sys.exit(1)

    try:
        result = mine(args.comments_json, top_n=args.top_n)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"评论挖掘完成: {len(result['top_comments'])} 条高赞 / "
              f"{len(result['title_candidates'])} 标题候选 / "
              f"{len(result['topic_candidates'])} 选题候选 → {args.output}")
    except Exception as e:
        print(f"评论挖掘失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
