# 作者: 阿洋
"""搜索意图适配器 — Search Intent Discovery

填补选题系统"只搜热榜不搜意图"的根本性缺陷。
热榜 = 已热（高竞争、短窗口），搜索意图 = 将热/未热（低竞争、长窗口）。

六种搜索意图信号：
1. 搜索建议（Autocomplete）— 百度/Google/必应搜索框自动补全
2. 相关搜索（Related Searches）— 百度搜索结果页底部"相关搜索"
3. 问题型需求（Question Mining）— 知乎问题搜索
4. 长尾关键词（Long-tail Keywords）— 基于种子词的多级扩展
5. 趋势查询（Rising Queries）— 由搜索建议频率推断
6. 内容空白检测（Content Gap）— 搜索结果质量差=机会

设计原则：
- 零API Key：只用公开端点+浏览器UA
- 优雅降级：单源失败不影响其余
- 输出格式与 fetch_trends.py 完全一致（candidate schema）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timezone

try:
    import requests as _requests
except ImportError:
    _requests = None


# ----------------------------- 公共工具 -----------------------------

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
TIMEOUT = 15


def _load_freshness():
    """加载时效锁工具；多路径兜底（包内 / adapters 同级）。"""
    try:
        from adapters._common import freshness as _f
        return _f
    except Exception:
        pass
    try:
        import os as _os
        import sys as _sys
        _here = _os.path.dirname(_os.path.abspath(__file__))
        _common = _os.path.normpath(_os.path.join(_here, "..", "_common"))
        if _common not in _sys.path:
            _sys.path.insert(0, _common)
        import freshness as _f  # type: ignore
        return _f
    except Exception:
        return None


_FRESH = _load_freshness()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cid(title: str, source: str = "intent") -> str:
    return hashlib.sha256((source + "|" + (title or "").strip()).encode("utf-8")).hexdigest()[:12]


def _url_quote(s: str) -> str:
    return urllib.parse.quote(s or "", safe="")


def _intent_candidate(
    title: str,
    source: str,
    url: str = "",
    hotness=None,
    rank=None,
    signal_type: str = "suggestion",
    seed_keyword: str = "",
) -> dict:
    """构建与 fetch_trends.py candidate schema 一致的条目，额外增加意图字段。"""
    return {
        "id": _cid(title, source),
        "title": (title or "").strip(),
        "source": source,
        "url": url or "",
        "hotness": hotness,
        "rank": rank,
        "publish_date": None,
        "snapshot_at": _now_iso(),
        "_freshness": "fresh",
        "_checked_at": _now_iso(),
        "_signal_type": signal_type,
        "_seed_keyword": seed_keyword,
    }


def _get_json(url, headers=None, params=None):
    if _requests is None:
        raise RuntimeError("requests 未安装，请执行 pip install requests")
    resp = _requests.get(url, headers=headers or HEADERS, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _get_text(url, headers=None, params=None):
    if _requests is None:
        raise RuntimeError("requests 未安装，请执行 pip install requests")
    resp = _requests.get(url, headers=headers or HEADERS, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding
    return resp.text


# ----------------------------- 1. 百度搜索建议 -----------------------------

def fetch_baidu_suggestions(seed_keyword: str, limit: int = 20) -> list[dict]:
    """调用百度搜索建议API，返回搜索建议列表。

    端点：https://suggestion.baidu.com/su?wd={keyword}&cb=
    零鉴权，公开端点，返回 JSONP 格式（cb=空时返回纯 JSON）。
    """
    if not seed_keyword:
        return []
    try:
        url = "https://suggestion.baidu.com/su"
        params = {"wd": seed_keyword, "cb": ""}
        text = _get_text(url, params=params)
        # 百度建议返回格式：window.baidu.sug({q:"...",p:false,s:["...", ...]})
        # cb=空时可能直接返回 JSON 或带前缀
        m = re.search(r'\((\{.*\})\)', text, re.S)
        if m:
            data = json.loads(m.group(1))
        else:
            # 尝试直接解析
            data = json.loads(text)
        suggestions = data.get("s", []) or []
        out = []
        for i, s in enumerate(suggestions):
            if not s or not s.strip():
                continue
            out.append(_intent_candidate(
                title=s.strip(),
                source="intent:baidu-suggest",
                url=f"https://www.baidu.com/s?wd={_url_quote(s.strip())}",
                rank=i + 1,
                signal_type="suggestion",
                seed_keyword=seed_keyword,
            ))
            if len(out) >= limit:
                break
        return out
    except Exception as exc:
        print(f"[intent:baidu-suggest] 失败: {exc}", file=sys.stderr)
        return []


# ----------------------------- 2. 百度相关搜索 -----------------------------

def fetch_baidu_related(keyword: str, limit: int = 15) -> list[dict]:
    """抓取百度搜索结果页底部的"相关搜索"。

    URL: https://www.baidu.com/s?wd={keyword}
    需要浏览器UA，解析HTML中的相关搜索词。
    """
    if not keyword:
        return []
    try:
        url = "https://www.baidu.com/s"
        params = {"wd": keyword}
        html = _get_text(url, params=params)
        out = []
        seen = set()

        # 百度相关搜索通常在 <div id="rs"> 或 class="rs" 内
        # 匹配相关搜索链接：<a href="/s?wd=...">关键词</a>
        # 多种模式兜底
        patterns = [
            # 模式1：rs 区域内的链接
            r'<div[^>]*id="rs"[^>]*>.*?</div>',
            # 模式2：相关搜索区块
            r'<div[^>]*class="rs[^"]*"[^>]*>.*?</div>',
        ]
        rs_block = ""
        for pat in patterns:
            m = re.search(pat, html, re.S)
            if m:
                rs_block = m.group(0)
                break

        # 如果找到相关搜索区块，从中提取；否则从全页提取
        search_area = rs_block if rs_block else html
        for m in re.finditer(
            r'<a[^>]*href="(/s\?wd=[^"]*)"[^>]*>([^<]{2,60})</a>',
            search_area, re.S
        ):
            title = m.group(2).strip()
            if not title or title in seen or title == keyword:
                continue
            seen.add(title)
            out.append(_intent_candidate(
                title=title,
                source="intent:baidu-related",
                url="https://www.baidu.com" + m.group(1),
                rank=len(out) + 1,
                signal_type="related",
                seed_keyword=keyword,
            ))
            if len(out) >= limit:
                break
        return out
    except Exception as exc:
        print(f"[intent:baidu-related] 失败: {exc}", file=sys.stderr)
        return []


# ----------------------------- 3. Google搜索建议 -----------------------------

def fetch_google_suggestions(seed_keyword: str, limit: int = 20) -> list[dict]:
    """调用Google搜索建议API，返回搜索建议列表。

    端点：https://suggestqueries.google.com/complete/search?client=firefox&q={keyword}
    零鉴权，返回 JSON 格式 ["query", ["sugg1", "sugg2", ...]]。
    """
    if not seed_keyword:
        return []
    try:
        url = "https://suggestqueries.google.com/complete/search"
        params = {"client": "firefox", "q": seed_keyword}
        data = _get_json(url, params=params)
        # 返回格式：["query", ["sugg1", "sugg2", ...], ...]
        suggestions = []
        if isinstance(data, list) and len(data) >= 2:
            suggestions = data[1] if isinstance(data[1], list) else []
        out = []
        for i, s in enumerate(suggestions):
            if not s or not str(s).strip():
                continue
            out.append(_intent_candidate(
                title=str(s).strip(),
                source="intent:google-suggest",
                url=f"https://www.google.com/search?q={_url_quote(str(s).strip())}",
                rank=i + 1,
                signal_type="suggestion",
                seed_keyword=seed_keyword,
            ))
            if len(out) >= limit:
                break
        return out
    except Exception as exc:
        print(f"[intent:google-suggest] 失败: {exc}", file=sys.stderr)
        return []


# ----------------------------- 4. 知乎问题搜索 -----------------------------

def fetch_zhihu_questions(keyword: str, limit: int = 15) -> list[dict]:
    """调用知乎搜索API，提取问题标题+回答数+关注数。

    端点：https://www.zhihu.com/api/v4/search_v3?q={keyword}&t=general
    需浏览器UA，可能需要Referer。
    """
    if not keyword:
        return []
    try:
        url = "https://www.zhihu.com/api/v4/search_v3"
        params = {"q": keyword, "t": "general"}
        headers = {
            **HEADERS,
            "Referer": "https://www.zhihu.com/search",
        }
        data = _get_json(url, headers=headers, params=params)
        out = []
        items = data.get("data", []) or []
        for i, it in enumerate(items):
            obj = it.get("object", {}) or {}
            # 知乎搜索结果可能是问题、文章等，只取问题类型
            qtype = it.get("type") or obj.get("type") or ""
            title = ""
            qid = ""
            answer_count = None
            follower_count = None

            if "question" in qtype.lower() or obj.get("question"):
                q = obj.get("question") or obj
                title = q.get("title") or q.get("name") or obj.get("title") or ""
                qid = q.get("id") or obj.get("id") or ""
                answer_count = q.get("answer_count") or obj.get("answer_count")
                follower_count = q.get("follower_count") or obj.get("follower_count")
            elif obj.get("type") == "answer":
                q = obj.get("question") or {}
                title = q.get("title") or ""
                qid = q.get("id") or ""
                answer_count = q.get("answer_count")
                follower_count = q.get("follower_count")
            else:
                title = obj.get("title") or obj.get("name") or ""
                qid = obj.get("id") or ""
                answer_count = obj.get("answer_count")
                follower_count = obj.get("follower_count")

            if not title or not title.strip():
                continue

            hotness = follower_count or answer_count
            qurl = f"https://www.zhihu.com/question/{qid}" if qid else ""

            out.append(_intent_candidate(
                title=title.strip(),
                source="intent:zhihu-question",
                url=qurl,
                hotness=hotness,
                rank=i + 1,
                signal_type="question",
                seed_keyword=keyword,
            ))
            if len(out) >= limit:
                break
        return out
    except Exception as exc:
        print(f"[intent:zhihu-question] 失败: {exc}", file=sys.stderr)
        return []


# ----------------------------- 5. 必应搜索建议 -----------------------------

def fetch_bing_suggestions(seed_keyword: str, limit: int = 20) -> list[dict]:
    """调用必应搜索建议API，返回搜索建议列表。

    端点：https://api.bing.com/qsonhs.aspx?q={keyword}
    零鉴权，返回 JSON 格式。
    """
    if not seed_keyword:
        return []
    try:
        url = "https://api.bing.com/qsonhs.aspx"
        params = {"q": seed_keyword}
        data = _get_json(url, params=params)
        # 必应返回格式：{ AS: { Query: "...", FullResults: N, Results: [{ Suggests: [{ Txt: "..." }] }] } }
        suggestions = []
        as_block = data.get("AS", {}) or {}
        results = as_block.get("Results", []) or []
        for r in results:
            for s in (r.get("Suggests") or []):
                txt = s.get("Txt") or ""
                if txt and txt.strip():
                    suggestions.append(txt.strip())
        out = []
        for i, s in enumerate(suggestions):
            out.append(_intent_candidate(
                title=s,
                source="intent:bing-suggest",
                url=f"https://www.bing.com/search?q={_url_quote(s)}",
                rank=i + 1,
                signal_type="suggestion",
                seed_keyword=seed_keyword,
            ))
            if len(out) >= limit:
                break
        return out
    except Exception as exc:
        print(f"[intent:bing-suggest] 失败: {exc}", file=sys.stderr)
        return []


# ----------------------------- 6. 长尾关键词扩展 -----------------------------

def expand_longtail(seed_keyword: str, depth: int = 2, limit: int = 30) -> list[dict]:
    """基于种子词的多级扩展，生成长尾关键词列表。

    第1级：seed_keyword → 5个函数各取建议
    第2级：取第1级的高频词 → 再搜一轮
    去重+按频率排序。
    """
    if not seed_keyword:
        return []

    # 所有建议函数
    suggest_fns = [
        fetch_baidu_suggestions,
        fetch_google_suggestions,
        fetch_bing_suggestions,
    ]

    def _fetch_suggestions(kw: str) -> list[str]:
        """从多个源获取建议词，返回去重后的词列表。"""
        words = []
        for fn in suggest_fns:
            try:
                items = fn(kw, limit=20)
                words.extend([it["title"] for it in items if it.get("title")])
            except Exception:
                continue
        return words

    # 第1级扩展
    level1_words = _fetch_suggestions(seed_keyword)
    word_freq = Counter(level1_words)

    # 第2级扩展（如果 depth >= 2）
    if depth >= 2:
        # 取第1级中出现频率最高的前5个词作为第2级种子
        top_seeds = [w for w, _ in word_freq.most_common(5)]
        for seed in top_seeds:
            try:
                level2_words = _fetch_suggestions(seed)
                word_freq.update(level2_words)
            except Exception:
                continue

        # 第3级（如果 depth >= 3）
        if depth >= 3:
            top_seeds_3 = [w for w, _ in word_freq.most_common(5) if w not in top_seeds]
            for seed in top_seeds_3[:3]:
                try:
                    level3_words = _fetch_suggestions(seed)
                    word_freq.update(level3_words)
                except Exception:
                    continue

    # 排除种子词本身，按频率排序
    sorted_words = [
        (w, c) for w, c in word_freq.most_common()
        if w != seed_keyword and len(w) > 1
    ]

    out = []
    for i, (word, freq) in enumerate(sorted_words):
        out.append(_intent_candidate(
            title=word,
            source="intent:longtail",
            url=f"https://www.baidu.com/s?wd={_url_quote(word)}",
            hotness=freq,
            rank=i + 1,
            signal_type="longtail",
            seed_keyword=seed_keyword,
        ))
        if len(out) >= limit:
            break
    return out


# ----------------------------- 7. 内容空白检测 -----------------------------

def detect_content_gap(keyword: str, limit: int = 10) -> list[dict]:
    """搜索百度，分析前10条结果，判断内容空白信号。

    检测维度：
    - 搜索结果中"百家号/知乎/小红书"占比过高 → 内容同质化
    - 搜索结果中无视频内容 → 视频内容空白
    - 搜索结果标题与query匹配度低 → 需求未满足
    - 搜索结果发布时间>1年 → 内容过时
    """
    if not keyword:
        return []

    try:
        url = "https://www.baidu.com/s"
        params = {"wd": keyword, "rn": "10"}
        html = _get_text(url, params=params)
    except Exception as exc:
        print(f"[intent:content-gap] 搜索失败: {exc}", file=sys.stderr)
        return []

    # 解析搜索结果
    results = _parse_baidu_serp(html, keyword)

    if not results:
        # 无结果本身就是巨大的内容空白
        return [_intent_candidate(
            title=f"[内容空白] 「{keyword}」无搜索结果",
            source="intent:content-gap",
            url=f"https://www.baidu.com/s?wd={_url_quote(keyword)}",
            hotness=100,
            rank=1,
            signal_type="content_gap",
            seed_keyword=keyword,
        )]

    # --- 信号1：同质化检测 ---
    homogeneity_domains = {"baijiahao", "zhihu", "xiaohongshu", "xhslink"}
    homogeneity_count = 0
    for r in results:
        rurl = (r.get("url") or "").lower()
        rsource = (r.get("source_site") or "").lower()
        for domain in homogeneity_domains:
            if domain in rurl or domain in rsource:
                homogeneity_count += 1
                break
    homogeneity_ratio = homogeneity_count / len(results) if results else 0

    # --- 信号2：视频内容空白 ---
    video_domains = {"bilibili", "douyin", "youtube", "ixigua", "video"}
    has_video = any(
        any(d in (r.get("url") or "").lower() for d in video_domains)
        for r in results
    )

    # --- 信号3：标题匹配度 ---
    keyword_chars = set(keyword)
    low_match_count = 0
    for r in results:
        title = r.get("title") or ""
        # 去除常见后缀
        clean_title = re.sub(r"[-_|].*$", "", title).strip()
        title_chars = set(clean_title)
        # 关键词字符在标题中的覆盖率
        if keyword_chars:
            overlap = len(keyword_chars & title_chars) / len(keyword_chars)
            if overlap < 0.3:
                low_match_count += 1
    low_match_ratio = low_match_count / len(results) if results else 0

    # --- 信号5：内容过时（基于可提取的日期） ---
    stale_count = 0
    now = datetime.now(timezone.utc)
    for r in results:
        date_str = r.get("date") or ""
        if date_str:
            try:
                if _FRESH is not None:
                    label = _FRESH.freshness_label(date_str, window_days=365, hard_limit_days=730)
                    if label in ("aging", "stale"):
                        stale_count += 1
            except Exception:
                pass

    # --- 信号6：搜索意图竞品发现 ---
    # 当检测到内容空白时，同时返回在该关键词下排名前列的账号/网站
    competitor_accounts = []
    if homogeneity_ratio >= 0.4 or not has_video or low_match_ratio >= 0.3:
        # 从搜索结果中提取排名前列的账号/网站
        competitor_domains = {}
        for r in results:
            rurl = (r.get("url") or "").lower()
            rtitle = r.get("title") or ""
            rsource = (r.get("source_site") or "").lower()
            # 提取域名
            domain_match = re.search(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+)', rurl)
            if domain_match:
                domain = domain_match.group(1)
                if domain not in competitor_domains:
                    competitor_domains[domain] = {
                        "domain": domain,
                        "title": rtitle,
                        "url": rurl,
                        "source_site": rsource,
                        "rank": len(competitor_domains) + 1,
                    }
        competitor_accounts = list(competitor_domains.values())[:5]

    # --- 综合评分 ---
    gap_score = 0
    opportunities = []

    if homogeneity_ratio >= 0.6:
        gap_score += 30
        opportunities.append(
            f"内容同质化严重（{homogeneity_ratio:.0%}来自百家号/知乎/小红书），"
            f"差异化内容有机会"
        )
    elif homogeneity_ratio >= 0.4:
        gap_score += 15
        opportunities.append(
            f"内容有一定同质化（{homogeneity_ratio:.0%}来自百家号/知乎/小红书）"
        )

    if not has_video:
        gap_score += 25
        opportunities.append("搜索结果中无视频内容，视频内容空白")
    else:
        gap_score += 5

    if low_match_ratio >= 0.5:
        gap_score += 25
        opportunities.append(
            f"搜索结果标题与关键词匹配度低（{low_match_ratio:.0%}），需求未满足"
        )
    elif low_match_ratio >= 0.3:
        gap_score += 10
        opportunities.append(
            f"部分搜索结果标题与关键词匹配度偏低（{low_match_ratio:.0%}）"
        )

    if stale_count >= 3:
        gap_score += 20
        opportunities.append(
            f"搜索结果中{stale_count}条内容过时（>1年），更新内容有机会"
        )

    # 生成内容空白条目
    out = []

    # 总体评分条目
    if gap_score > 0:
        out.append(_intent_candidate(
            title=f"[内容空白评分:{gap_score}] 「{keyword}」{'；'.join(opportunities)}",
            source="intent:content-gap",
            url=f"https://www.baidu.com/s?wd={_url_quote(keyword)}",
            hotness=gap_score,
            rank=1,
            signal_type="content_gap",
            seed_keyword=keyword,
        ))

    # 各维度详情
    if homogeneity_ratio >= 0.4:
        out.append(_intent_candidate(
            title=f"[同质化] 「{keyword}」{homogeneity_ratio:.0%}结果来自平台号，独立深度内容有机会",
            source="intent:content-gap",
            url=f"https://www.baidu.com/s?wd={_url_quote(keyword)}",
            hotness=int(homogeneity_ratio * 100),
            rank=len(out) + 1,
            signal_type="content_gap",
            seed_keyword=keyword,
        ))

    if not has_video:
        out.append(_intent_candidate(
            title=f"[视频空白] 「{keyword}」搜索结果无视频，视频内容有机会",
            source="intent:content-gap",
            url=f"https://www.baidu.com/s?wd={_url_quote(keyword)}",
            hotness=25,
            rank=len(out) + 1,
            signal_type="content_gap",
            seed_keyword=keyword,
        ))

    if low_match_ratio >= 0.3:
        out.append(_intent_candidate(
            title=f"[需求未满足] 「{keyword}」{low_match_ratio:.0%}结果标题匹配度低",
            source="intent:content-gap",
            url=f"https://www.baidu.com/s?wd={_url_quote(keyword)}",
            hotness=int(low_match_ratio * 100),
            rank=len(out) + 1,
            signal_type="content_gap",
            seed_keyword=keyword,
        ))

    if stale_count >= 3:
        out.append(_intent_candidate(
            title=f"[内容过时] 「{keyword}」{stale_count}条结果超过1年",
            source="intent:content-gap",
            url=f"https://www.baidu.com/s?wd={_url_quote(keyword)}",
            hotness=stale_count * 10,
            rank=len(out) + 1,
            signal_type="content_gap",
            seed_keyword=keyword,
        ))

    # 竞品发现条目
    if competitor_accounts:
        competitor_names = [f"{c['domain']}(#{c['rank']})" for c in competitor_accounts]
        out.append(_intent_candidate(
            title=f"[搜索意图竞品] 「{keyword}」排名前列：{'、'.join(competitor_names[:3])}",
            source="intent:content-gap-competitor",
            url=f"https://www.baidu.com/s?wd={_url_quote(keyword)}",
            hotness=len(competitor_accounts) * 10,
            rank=len(out) + 1,
            signal_type="content_gap",
            seed_keyword=keyword,
        ))

    return out[:limit]


def _parse_baidu_serp(html: str, keyword: str) -> list[dict]:
    """解析百度搜索结果页，提取前10条结果的基本信息。"""
    results = []
    # 百度搜索结果容器：<div class="result c-container ..."> 或 <div class="c-container ...">
    # 标题在 <h3> 内，链接在 <a href="..."> 内
    # 每个结果块
    blocks = re.findall(
        r'<div[^>]*class="[^"]*(?:result|c-container)[^"]*"[^>]*>(.*?)</div>\s*(?=<div[^>]*class="[^"]*(?:result|c-container)|$)',
        html, re.S,
    )

    # 如果正则没匹配到，用更宽松的方式
    if not blocks:
        blocks = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.S)

    for block in blocks[:10]:
        title = ""
        url = ""
        source_site = ""
        date_str = ""

        # 提取标题
        tm = re.search(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', block, re.S)
        if tm:
            url = tm.group(1).strip()
            title = re.sub(r'<[^>]+>', '', tm.group(2)).strip()
        else:
            title = re.sub(r'<[^>]+>', '', block).strip()

        if not title:
            continue

        # 提取来源站点
        sm = re.search(r'<span[^>]*class="[^"]*c-color-gray[^"]*"[^>]*>(.*?)</span>', block, re.S)
        if sm:
            source_site = re.sub(r'<[^>]+>', '', sm.group(1)).strip()

        # 提取日期
        dm = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)', block)
        if dm:
            date_str = dm.group(1)

        results.append({
            "title": title,
            "url": url,
            "source_site": source_site,
            "date": date_str,
        })

    return results


# ----------------------------- 8. 主入口：聚合所有搜索意图信号 -----------------------------

# 可用的搜索意图源
INTENT_SOURCES = {
    "baidu-suggest": lambda kw, lim: fetch_baidu_suggestions(kw, limit=lim),
    "baidu-related": lambda kw, lim: fetch_baidu_related(kw, limit=lim),
    "google-suggest": lambda kw, lim: fetch_google_suggestions(kw, limit=lim),
    "zhihu-question": lambda kw, lim: fetch_zhihu_questions(kw, limit=lim),
    "bing-suggest": lambda kw, lim: fetch_bing_suggestions(kw, limit=lim),
    "longtail": lambda kw, lim: expand_longtail(kw, depth=2, limit=lim),
    "content-gap": lambda kw, lim: detect_content_gap(kw, limit=lim),
}

DEFAULT_INTENT_SOURCES = [
    "baidu-suggest", "baidu-related", "google-suggest",
    "zhihu-question", "bing-suggest",
]


def collect_intent_signals(
    keyword: str,
    sources: list[str] | None = None,
    limit_per_source: int = 20,
) -> dict:
    """主入口函数，聚合所有搜索意图信号。

    输出格式与 fetch_trends.py 的 collect() 完全一致：
    {
        "meta": { anchor, sources_requested, sources_succeeded, keyword, total, errors, ... },
        "trends": [ candidate, ... ]
    }
    每条候选额外增加 _signal_type 和 _seed_keyword 字段。
    """
    if not keyword:
        return {
            "meta": {
                "anchor": _FRESH.now_anchor().isoformat() if _FRESH else _now_iso(),
                "sources_requested": sources or [],
                "sources_succeeded": [],
                "keyword": keyword,
                "total": 0,
                "errors": [{"source": "input", "error": "keyword 不能为空"}],
                "freshness_available": _FRESH is not None,
            },
            "trends": [],
        }

    if sources is None:
        sources = DEFAULT_INTENT_SOURCES

    all_items: list[dict] = []
    errors: list[dict] = []
    used: list[str] = []

    for name in sources:
        fn = INTENT_SOURCES.get(name)
        if fn is None:
            errors.append({"source": name, "error": "未知搜索意图源"})
            continue
        try:
            items = fn(keyword, limit_per_source)
            # 注入新鲜度标注
            for it in items:
                if _FRESH is not None:
                    _FRESH.annotate(it, date_field="publish_date")
                else:
                    it["_freshness"] = it.get("_freshness", "unknown")
                    it.setdefault("_checked_at", _now_iso())
            all_items.extend(items)
            used.append(name)
            print(f"[intent:{name}] 拉取 {len(items)} 条", file=sys.stderr)
        except Exception as exc:
            errors.append({"source": name, "error": str(exc)})
            print(f"[intent:{name}] 失败（已跳过，其余源继续）: {exc}", file=sys.stderr)

    # 去重（同标题保留热度更高/排名更前者）
    dedup: dict[str, dict] = {}
    for it in all_items:
        key = it["title"]
        if not key:
            continue
        if key not in dedup:
            dedup[key] = it
        else:
            old = dedup[key]
            if (it.get("hotness") or 0) > (old.get("hotness") or 0):
                dedup[key] = it
    merged = list(dedup.values())
    merged.sort(key=lambda x: (x.get("hotness") or 0), reverse=True)

    return {
        "meta": {
            "anchor": _FRESH.now_anchor().isoformat() if _FRESH else _now_iso(),
            "sources_requested": sources,
            "sources_succeeded": used,
            "keyword": keyword,
            "total": len(merged),
            "errors": errors,
            "freshness_available": _FRESH is not None,
        },
        "trends": merged,
    }


# ----------------------------- 9. CLI入口 -----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="搜索意图适配器 — 零API Key、零外部依赖的搜索引擎关键词研究工具",
    )
    parser.add_argument(
        "--keyword", "-k", required=True,
        help="种子关键词（必填）",
    )
    parser.add_argument(
        "--sources", "-s",
        default=",".join(DEFAULT_INTENT_SOURCES),
        help="逗号分隔的搜索意图源；可选: " + ",".join(INTENT_SOURCES.keys()),
    )
    parser.add_argument(
        "--depth", "-d", type=int, default=2,
        help="长尾关键词扩展深度（1-3，默认2）",
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=20,
        help="每个源最多取多少条（默认20）",
    )
    parser.add_argument(
        "--out", "-o", default=None,
        help="输出 JSON 路径（默认打印到 stdout）",
    )
    args = parser.parse_args()

    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]

    # 如果 sources 包含 longtail，需要用自定义 depth
    # collect_intent_signals 使用默认 depth=2，这里通过替换函数来支持自定义 depth
    if "longtail" in sources and args.depth != 2:
        INTENT_SOURCES["longtail"] = lambda kw, lim: expand_longtail(kw, depth=args.depth, limit=lim)

    result = collect_intent_signals(args.keyword, sources, args.limit)

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"[search-intent] 已写入 {args.out}（{result['meta']['total']} 条，"
              f"成功源 {len(result['meta']['sources_succeeded'])}/{len(sources)}）",
              file=sys.stderr)
    else:
        print(payload)

    # 全部源失败才算硬失败
    if not result["meta"]["sources_succeeded"]:
        print("[search-intent] 所有搜索意图源均不可用——可能是网络受限或端点临时变更。",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
