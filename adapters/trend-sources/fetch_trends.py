# 作者: 阿洋
"""多源热点聚合器（零配置 · 可直接运行）。

设计原则
--------
- **零配置**：只用各平台的公开匿名端点，不需要 cookie / token / API Key / MCP server。
  唯一要求是带一个浏览器 User-Agent（很多端点对默认 curl/python UA 返回 403）。
- **多源**：默认覆盖 微博热搜 / 知乎热榜 / B站热门 / 百度热搜 / 抖音热点 / 头条热榜 / IT之家 / 36氪，
  解决"搜索源太单一"。可用 --sources 选择子集。
- **优雅降级**：任一源失败（结构变更/限流/网络）只影响该源，其余照常返回；绝不整体抛异常。
- **时效锁**：所有条目以"运行此刻"为锚做新鲜度判定（见 shared-protocols/freshness-protocol.md），
  防止把旧时间热点当成当下信号。热榜类本身就是"当下"，统一标 fresh/unknown，并记录抓取锚点。

输出
----
统一为候选条目列表（对齐 shared-protocols/candidate-schema.md 的核心字段）：
  { id, title, source, url, hotness, rank, snapshot_at, _freshness, _checked_at }

用法
----
  python fetch_trends.py --sources weibo,zhihu,bilibili,baidu,douyin --limit 50 --out trends.json
  python fetch_trends.py --keyword 考研            # 只保留标题含关键词的热点（垂直筛选）
  python fetch_trends.py                            # 全部源、每源 limit 条、打印到 stdout

注意
----
公开端点的页面结构/接口字段可能随平台调整而变化；本脚本对每个源都做了多重兜底，
若某源持续解析失败，stderr 会给出提示，可按本文件内对应解析函数自行微调选择器。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
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


def _cid(title: str) -> str:
    return hashlib.sha256(("trend|" + (title or "").strip()).encode("utf-8")).hexdigest()[:12]


def _candidate(title, source, url, hotness=None, rank=None, publish=None) -> dict:
    return {
        "id": _cid(title),
        "title": (title or "").strip(),
        "source": source,
        "url": url or "",
        "hotness": hotness,
        "rank": rank,
        "publish_date": publish,        # 多数热榜无单条发布时间 → None（时效标 unknown）
        "snapshot_at": _now_iso(),
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


# ----------------------------- 各源抓取 -----------------------------
# 每个 fetch_* 返回 List[dict]；失败抛异常由上层捕获并降级。

def fetch_weibo(limit: int) -> list:
    """微博热搜榜。优先 JSON 侧栏接口，失败回退 HTML 解析。"""
    out = []
    try:
        data = _get_json(
            "https://weibo.com/ajax/side/hotSearch",
            headers={**HEADERS, "Referer": "https://weibo.com/"},
        )
        band = (data or {}).get("data", {}).get("realtime", []) or []
        for i, it in enumerate(band):
            word = it.get("word") or it.get("note") or ""
            if not word:
                continue
            out.append(_candidate(
                word, "trend:weibo-hot",
                f"https://s.weibo.com/weibo?q={requests_quote(word)}",
                hotness=it.get("num"), rank=i + 1,
            ))
            if len(out) >= limit:
                break
        if out:
            return out
    except Exception:
        pass
    # 回退：HTML 榜单
    html = _get_text(
        "https://s.weibo.com/top/summary?cate=realtimehot",
        headers={**HEADERS, "Referer": "https://s.weibo.com/"},
    )
    for i, m in enumerate(re.finditer(r'href="(/weibo\?q=[^"]+)"[^>]*>([^<]{2,40})</a>', html)):
        title = m.group(2).strip()
        if title in ("微博热搜", "热搜榜"):
            continue
        out.append(_candidate(title, "trend:weibo-hot",
                              "https://s.weibo.com" + m.group(1), rank=i + 1))
        if len(out) >= limit:
            break
    return out


def fetch_zhihu(limit: int) -> list:
    """知乎热榜（官方 v3 JSON，匿名可访，需浏览器 UA）。"""
    data = _get_json(
        "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total",
        headers={**HEADERS, "Referer": "https://www.zhihu.com/hot"},
        params={"limit": min(limit, 50), "desktop": "true"},
    )
    out = []
    for i, it in enumerate((data or {}).get("data", []) or []):
        tgt = it.get("target", {}) or {}
        title = tgt.get("title") or (it.get("card_label") or {}).get("name") or ""
        if not title:
            continue
        qid = tgt.get("id") or ""
        url = f"https://www.zhihu.com/question/{qid}" if qid else "https://www.zhihu.com/hot"
        detail = (it.get("detail_text") or "")
        hot = None
        mm = re.search(r"(\d+(?:\.\d+)?)\s*万", detail)
        if mm:
            hot = int(float(mm.group(1)) * 10000)
        out.append(_candidate(title, "trend:zhihu-hot", url, hotness=hot, rank=i + 1))
        if len(out) >= limit:
            break
    return out


def fetch_bilibili(limit: int) -> list:
    """B站综合热门（公开接口，无需登录）。"""
    data = _get_json(
        "https://api.bilibili.com/x/web-interface/popular",
        headers={**HEADERS, "Referer": "https://www.bilibili.com/"},
        params={"ps": min(limit, 50), "pn": 1},
    )
    if data.get("code") != 0:
        raise RuntimeError(f"bilibili code={data.get('code')}")
    out = []
    for i, v in enumerate((data.get("data", {}) or {}).get("list", []) or []):
        title = v.get("title") or ""
        pub = v.get("pubdate")
        pub_iso = datetime.fromtimestamp(pub, tz=timezone.utc).isoformat() if pub else None
        stat = v.get("stat", {}) or {}
        out.append(_candidate(
            title, "trend:bilibili-popular",
            f"https://www.bilibili.com/video/{v.get('bvid')}" if v.get("bvid") else "",
            hotness=stat.get("view"), rank=i + 1, publish=pub_iso,
        ))
        if len(out) >= limit:
            break
    return out


def fetch_baidu(limit: int) -> list:
    """百度热搜（实时榜，HTML 内嵌 JSON）。"""
    html = _get_text("https://top.baidu.com/board?tab=realtime",
                     headers={**HEADERS, "Referer": "https://top.baidu.com/"})
    out = []
    seen = set()
    for m in re.finditer(r'"query":"([^"]{2,40})"', html):
        title = m.group(1).strip()
        if not title or title in seen:
            continue
        seen.add(title)
        out.append(_candidate(
            title, "trend:baidu-hot",
            f"https://www.baidu.com/s?wd={requests_quote(title)}", rank=len(out) + 1,
        ))
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("baidu 解析为空（页面结构可能已变）")
    return out


def fetch_douyin(limit: int) -> list:
    """抖音热点榜（公开 billboard 接口）。"""
    data = _get_json(
        "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/",
        headers={**HEADERS, "Referer": "https://www.douyin.com/hot"},
    )
    out = []
    for i, it in enumerate((data or {}).get("word_list", []) or []):
        title = it.get("word") or ""
        if not title:
            continue
        out.append(_candidate(
            title, "trend:douyin-hot",
            f"https://www.douyin.com/search/{requests_quote(title)}",
            hotness=it.get("hot_value"), rank=i + 1,
        ))
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("douyin 返回空 word_list")
    return out


def fetch_toutiao(limit: int) -> list:
    """今日头条热榜（公开 hot-event 接口）。"""
    data = _get_json(
        "https://www.toutiao.com/hot-event/hot-board/",
        headers={**HEADERS, "Referer": "https://www.toutiao.com/"},
        params={"origin": "toutiao_pc"},
    )
    out = []
    for i, it in enumerate((data or {}).get("data", []) or []):
        title = it.get("Title") or it.get("title") or ""
        if not title:
            continue
        out.append(_candidate(
            title, "trend:toutiao-hot",
            it.get("Url") or f"https://so.toutiao.com/search?keyword={requests_quote(title)}",
            hotness=it.get("HotValue") or it.get("hot_value"), rank=i + 1,
        ))
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("toutiao 返回空 data")
    return out


def fetch_ithome(limit: int) -> list:
    """IT之家（科技热榜，RSS，稳定无鉴权）。"""
    xml = _get_text("https://www.ithome.com/rss/",
                    headers={**HEADERS, "Accept": "application/rss+xml, text/xml"})
    out = []
    for i, m in enumerate(re.finditer(
            r"<item>.*?<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>.*?<link>(.*?)</link>"
            r".*?<pubDate>(.*?)</pubDate>", xml, re.S)):
        title = re.sub(r"<.*?>", "", m.group(1)).strip()
        if not title:
            continue
        out.append(_candidate(title, "trend:ithome", m.group(2).strip(),
                              rank=i + 1, publish=_rss_date(m.group(3))))
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("ithome RSS 解析为空")
    return out


def fetch_36kr(limit: int) -> list:
    """36氪（创投/商业热榜，公开 newsflash 接口）。"""
    data = _get_json(
        "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot",
        headers={**HEADERS, "Content-Type": "application/json",
                 "Referer": "https://36kr.com/"},
    )
    items = (((data or {}).get("data") or {}).get("hotRankList")) or []
    out = []
    for i, it in enumerate(items):
        tm = it.get("templateMaterial", {}) or {}
        title = tm.get("widgetTitle") or ""
        if not title:
            continue
        iid = it.get("itemId") or ""
        out.append(_candidate(
            title, "trend:36kr",
            f"https://36kr.com/p/{iid}" if iid else "https://36kr.com/hot-list/catalog",
            hotness=tm.get("statRead"), rank=i + 1,
        ))
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("36kr 返回空榜单")
    return out


# ----------------------------- 辅助 -----------------------------

def requests_quote(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s or "", safe="")


def _rss_date(s: str):
    s = (s or "").strip()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            continue
    return None


SOURCES = {
    "weibo": fetch_weibo,
    "zhihu": fetch_zhihu,
    "bilibili": fetch_bilibili,
    "baidu": fetch_baidu,
    "douyin": fetch_douyin,
    "toutiao": fetch_toutiao,
    "ithome": fetch_ithome,
    "36kr": fetch_36kr,
}
DEFAULT_SOURCES = ["weibo", "zhihu", "bilibili", "baidu", "douyin", "toutiao"]


def collect(sources, limit_per_source: int, keyword: str | None = None) -> dict:
    all_items = []
    errors = []
    used = []
    for name in sources:
        fn = SOURCES.get(name)
        if fn is None:
            errors.append({"source": name, "error": "未知热点源"})
            continue
        try:
            items = fn(limit_per_source)
            if keyword:
                items = [it for it in items if keyword in (it.get("title") or "")]
            for it in items:
                if _FRESH is not None:
                    _FRESH.annotate(it, date_field="publish_date")
                else:
                    it["_freshness"] = "unknown"
                    it["_checked_at"] = _now_iso()
            all_items.extend(items)
            used.append(name)
            print(f"[trends:{name}] 拉取 {len(items)} 条", file=sys.stderr)
        except Exception as exc:
            errors.append({"source": name, "error": str(exc)})
            print(f"[trends:{name}] 失败（已跳过，其余源继续）: {exc}", file=sys.stderr)

    # 去重（同标题保留热度更高/排名更前者）
    dedup = {}
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
            "keyword_filter": keyword,
            "total": len(merged),
            "errors": errors,
            "freshness_available": _FRESH is not None,
        },
        "trends": merged,
    }


def main():
    parser = argparse.ArgumentParser(description="多源热点聚合器（零配置，公开端点）")
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES),
                        help="逗号分隔的热点源；可选: " + ",".join(SOURCES.keys()))
    parser.add_argument("--limit", type=int, default=30, help="每个源最多取多少条")
    parser.add_argument("--keyword", default=None, help="只保留标题含该关键词的热点（垂直筛选）")
    parser.add_argument("--out", default=None, help="输出 JSON 路径（默认打印到 stdout）")
    args = parser.parse_args()

    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    result = collect(sources, args.limit, args.keyword)

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"[trends] 已写入 {args.out}（{result['meta']['total']} 条，"
              f"成功源 {len(result['meta']['sources_succeeded'])}/{len(sources)}）",
              file=sys.stderr)
    else:
        print(payload)

    # 全部源失败才算硬失败
    if not result["meta"]["sources_succeeded"]:
        print("[trends] 所有热点源均不可用——可能是网络受限或端点临时变更；"
              "可让 Agent 改用自身 WebFetch 抓取平台热搜页作为兜底。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
