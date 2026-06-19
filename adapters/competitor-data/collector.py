# 作者: 阿洋
"""Yang.skills 多源数据采集管线 - Multi-source competitor data collection"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone

try:
    import requests as _requests
except ImportError:
    _requests = None

_PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright

    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


def _load_freshness():
    """加载时效锁工具；多路径兜底，确保从不同 cwd 运行都能导入。"""
    try:
        from adapters._common import freshness as _f  # 包内绝对导入
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


def _generate_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_account_metrics() -> dict:
    return {
        "follower_count": None,
        "total_likes": None,
        "total_videos": None,
        "avg_views_30d": None,
        "avg_likes_30d": None,
        "avg_comments_30d": None,
        "follower_growth_30d": None,
        "engagement_rate": None,
    }


def _default_audience_insight() -> dict:
    return {
        "age_distribution": {"18-23": 0, "24-30": 0, "31-40": 0, "41+": 0},
        "gender_ratio": {"male": 0, "female": 0},
        "top_regions": [],
        "active_hours": [],
    }


def _build_output(source: str, competitor_id: str) -> dict:
    return {
        "source": source,
        "competitor_id": competitor_id,
        "collected_at": _now_iso(),
        "account_metrics": _default_account_metrics(),
        "audience_insight": _default_audience_insight(),
        "content_trends": [],
        "recent_videos": [],
        "freshness_summary": None,
        "raw_source": None,
    }


def _parse_bilibili_uid(input_str: str) -> str | None:
    url_match = re.search(r"space\.bilibili\.com/(\d+)", input_str)
    if url_match:
        return url_match.group(1)
    if re.fullmatch(r"\d+", input_str):
        return input_str
    return None


def _parse_generic_url(input_str: str) -> str | None:
    if input_str.startswith(("http://", "https://")):
        return input_str
    if re.match(r"^[\w.-]+\.[a-z]{2,}", input_str):
        return "https://" + input_str
    return None


def _parse_bilibili_duration(length_str: str) -> int:
    if not length_str:
        return 0
    parts = length_str.split(":")
    if len(parts) == 2:
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, TypeError):
            return 0
    if len(parts) == 3:
        try:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except (ValueError, TypeError):
            return 0
    try:
        return int(length_str)
    except (ValueError, TypeError):
        return 0


def _parse_number(s: str) -> int:
    s = s.strip().lower()
    multipliers: dict[str, int] = {
        "\u4e07": 10000,
        "\u4ebf": 100000000,
        "k": 1000,
        "m": 1000000,
    }
    for unit, mult in multipliers.items():
        if unit in s:
            num_part = s.replace(unit, "").strip()
            return int(float(num_part) * mult)
    return int(float(s.replace(",", "")))


def collect_bilibili_api(input_str: str, competitor_id: str) -> dict:
    output = _build_output("bilibili_api", competitor_id)

    if _requests is None:
        print(
            "[collector:bilibili_api] requests \u672a\u5b89\u88c5\u3002\u8bf7\u6267\u884c: pip install requests",
            file=sys.stderr,
        )
        return output

    uid = _parse_bilibili_uid(input_str)
    if not uid:
        print(
            f"[collector:bilibili_api] \u65e0\u6cd5\u89e3\u6790 B\u7ad9 UID: {input_str}\n"
            "\u8bf7\u63d0\u4f9b B\u7ad9 UID \uff08\u5982 123456\uff09\u6216\u7a7a\u95f4\u94fe\u63a5\uff08\u5982 https://space.bilibili.com/123456\uff09",
            file=sys.stderr,
        )
        return output

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com",
    }

    any_success = False

    try:
        resp = _requests.get(
            f"https://api.bilibili.com/x/space/acc/info?mid={uid}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        info_data = resp.json()
        if info_data.get("code") == 0 and info_data.get("data"):
            output["raw_source"] = {"acc_info": info_data["data"]}
            any_success = True
    except Exception as exc:
        print(
            f"[collector:bilibili_api] \u7528\u6237\u4fe1\u606f\u83b7\u53d6\u5931\u8d25: {exc}",
            file=sys.stderr,
        )

    try:
        resp = _requests.get(
            f"https://api.bilibili.com/x/relation/stat?vmid={uid}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        stat_data = resp.json()
        if stat_data.get("code") == 0 and stat_data.get("data"):
            stat = stat_data["data"]
            output["account_metrics"]["follower_count"] = stat.get("follower")
            if output["raw_source"] is None:
                output["raw_source"] = {}
            output["raw_source"]["relation_stat"] = stat
            any_success = True
    except Exception as exc:
        print(
            f"[collector:bilibili_api] \u5173\u6ce8\u7edf\u8ba1\u83b7\u53d6\u5931\u8d25: {exc}",
            file=sys.stderr,
        )

    try:
        resp = _requests.get(
            f"https://api.bilibili.com/x/space/upstat?mid={uid}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        upstat_data = resp.json()
        if upstat_data.get("code") == 0 and upstat_data.get("data"):
            upstat = upstat_data["data"]
            output["account_metrics"]["total_likes"] = upstat.get("likes")
            if output["raw_source"] is None:
                output["raw_source"] = {}
            output["raw_source"]["upstat"] = upstat
            any_success = True
    except Exception as exc:
        print(
            f"[collector:bilibili_api] UP\u4e3b\u7edf\u8ba1\u83b7\u53d6\u5931\u8d25: {exc}",
            file=sys.stderr,
        )

    try:
        resp = _requests.get(
            f"https://api.bilibili.com/x/space/arc/search?mid={uid}&ps=30&pn=1&order=pubdate",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        video_data = resp.json()
        if video_data.get("code") == 0 and video_data.get("data"):
            vdata = video_data["data"]
            total_videos = vdata.get("page", {}).get("count") or 0
            output["account_metrics"]["total_videos"] = total_videos

            vlist = vdata.get("list", {}).get("vlist") or []
            recent_videos: list[dict] = []
            total_views = 0
            total_video_likes = 0
            total_comments = 0
            video_count = 0

            for v in vlist:
                bvid = v.get("bvid", "")
                title = v.get("title", "")
                created_ts = v.get("created")
                length = v.get("length", "")
                views = v.get("play")
                likes_val = v.get("video_review")
                comments_val = v.get("comment")

                publish_date = None
                if created_ts:
                    publish_date = datetime.fromtimestamp(
                        created_ts, tz=timezone.utc
                    ).isoformat()

                video_entry: dict = {
                    "video_url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
                    "title": title or "",
                    "publish_date": publish_date,
                    "duration_sec": _parse_bilibili_duration(length),
                    "views": views,
                    "likes": likes_val,
                    "comments": comments_val,
                    "shares": None,
                    "completion_rate": None,
                }
                recent_videos.append(video_entry)

                if isinstance(views, (int, float)):
                    total_views += int(views)
                    video_count += 1
                if isinstance(likes_val, (int, float)):
                    total_video_likes += int(likes_val)
                if isinstance(comments_val, (int, float)):
                    total_comments += int(comments_val)

            output["recent_videos"] = recent_videos

            if video_count > 0:
                output["account_metrics"]["avg_views_30d"] = total_views // video_count
                output["account_metrics"]["avg_likes_30d"] = total_video_likes // video_count
                output["account_metrics"]["avg_comments_30d"] = total_comments // video_count

            if output["raw_source"] is None:
                output["raw_source"] = {}
            output["raw_source"]["video_list"] = vdata
            any_success = True
    except Exception as exc:
        print(
            f"[collector:bilibili_api] \u89c6\u9891\u5217\u8868\u83b7\u53d6\u5931\u8d25: {exc}",
            file=sys.stderr,
        )

    follower_count = output["account_metrics"]["follower_count"]
    avg_views = output["account_metrics"]["avg_views_30d"]
    if (
        isinstance(follower_count, (int, float))
        and isinstance(avg_views, (int, float))
        and follower_count > 0
    ):
        output["account_metrics"]["engagement_rate"] = round(avg_views / follower_count, 4)

    if not any_success:
        print(
            "[collector:bilibili_api] \u6240\u6709 API \u8bf7\u6c42\u5747\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u7f51\u7edc\u8fde\u63a5\u6216 B\u7ad9 UID \u662f\u5426\u6b63\u786e\u3002\n"
            "\u66ff\u4ee3\u65b9\u6848\uff1a\u4f7f\u7528 --source playwright_fallback \u5bf9\u7ade\u54c1\u4e3b\u9875\u505a\u901a\u7528\u63d0\u53d6\u3002",
            file=sys.stderr,
        )

    return output


def collect_oceanengine(keyword: str, competitor_id: str) -> dict:
    output = _build_output("oceanengine", competitor_id)

    if not _PLAYWRIGHT_AVAILABLE:
        print(
            "[collector:oceanengine] Playwright \u672a\u5b89\u88c5\u3002\n"
            "\u8bf7\u6267\u884c: pip install playwright && playwright install chromium\n"
            "\u66ff\u4ee3\u65b9\u6848: \u4f7f\u7528 --source bilibili_api \u91c7\u96c6 B\u7ad9\u6570\u636e\uff0c\u6216\u4f7f\u7528 --source playwright_fallback \u505a\u901a\u7528\u9875\u9762\u63d0\u53d6\u3002",
            file=sys.stderr,
        )
        return output

    print(
        "[collector:oceanengine] \u63d0\u793a: \u5de8\u91cf\u7b97\u6570 (trendinsight.oceanengine.com) \u9700\u8981\u767b\u5f55\u8ba4\u8bc1\u3002\n"
        "\u5982\u9700\u91c7\u96c6\u5de8\u91cf\u7b97\u6570\u6570\u636e\uff0c\u8bf7\u624b\u52a8\u767b\u5f55\u540e\u5bfc\u51fa\u6570\u636e\uff0c\u6216\u4f7f\u7528\u4ee5\u4e0b\u66ff\u4ee3\u6570\u636e\u6e90\uff1a\n"
        "  - --source bilibili_api : B\u7ad9\u516c\u5f00API\uff08\u65e0\u9700\u767b\u5f55\uff09\n"
        "  - --source playwright_fallback : \u901a\u7528\u9875\u9762\u63d0\u53d6",
        file=sys.stderr,
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(
                    f"https://trendinsight.oceanengine.com/arithmetic-index/analysis?keyword={keyword}",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                page.wait_for_timeout(3000)

                page_text = page.inner_text("body")

                if "\u767b\u5f55" in page_text or "login" in page_text.lower():
                    print(
                        "[collector:oceanengine] \u9875\u9762\u9700\u8981\u767b\u5f55\uff0c\u65e0\u6cd5\u81ea\u52a8\u91c7\u96c6\u3002\n"
                        "\u66ff\u4ee3\u65b9\u6848: \u4f7f\u7528 --source bilibili_api \u6216 --source playwright_fallback\u3002",
                        file=sys.stderr,
                    )
                else:
                    output["raw_source"] = {"page_text": page_text[:10000]}
                    print(
                        "[collector:oceanengine] \u9875\u9762\u5185\u5bb9\u5df2\u63d0\u53d6\uff0c\u4f46\u7ed3\u6784\u5316\u6570\u636e\u89e3\u6790\u9700\u8981\u767b\u5f55\u6001\u3002\n"
                        "\u5efa\u8bae\u624b\u52a8\u767b\u5f55\u540e\u5bfc\u51fa\u6570\u636e\u3002",
                        file=sys.stderr,
                    )
            except Exception as exc:
                print(
                    f"[collector:oceanengine] \u9875\u9762\u8bbf\u95ee\u5931\u8d25: {exc}\n"
                    "\u66ff\u4ee3\u65b9\u6848: \u4f7f\u7528 --source bilibili_api \u6216 --source playwright_fallback\u3002",
                    file=sys.stderr,
                )
            finally:
                browser.close()
    except Exception as exc:
        print(
            f"[collector:oceanengine] Playwright \u542f\u52a8\u5931\u8d25: {exc}\n"
            "\u66ff\u4ee3\u65b9\u6848: \u4f7f\u7528 --source bilibili_api \u91c7\u96c6 B\u7ad9\u6570\u636e\u3002",
            file=sys.stderr,
        )

    return output


def collect_playwright_fallback(url_or_domain: str, competitor_id: str) -> dict:
    output = _build_output("playwright_fallback", competitor_id)

    if not _PLAYWRIGHT_AVAILABLE:
        print(
            "[collector:playwright_fallback] Playwright \u672a\u5b89\u88c5\u3002\n"
            "\u8bf7\u6267\u884c: pip install playwright && playwright install chromium\n"
            "\u66ff\u4ee3\u65b9\u6848: \u4f7f\u7528 --source bilibili_api \u91c7\u96c6 B\u7ad9\u6570\u636e\u3002",
            file=sys.stderr,
        )
        return output

    url = _parse_generic_url(url_or_domain)
    if not url:
        print(
            f"[collector:playwright_fallback] \u65e0\u6cd5\u89e3\u6790 URL: {url_or_domain}\n"
            "\u8bf7\u63d0\u4f9b\u5b8c\u6574\u7684 URL\uff08\u5982 https://www.douyin.com/user/xxx\uff09\u3002",
            file=sys.stderr,
        )
        return output

    any_success = False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)

                page_text = page.inner_text("body")
                page_title = page.title()
                final_url = page.url

                output["raw_source"] = {
                    "url": final_url,
                    "title": page_title,
                    "page_text": page_text[:10000],
                }
                any_success = True

                follower_patterns = [
                    r"\u7c89\u4e1d[:\s]*(\d[\d,.]*[\u4e07\u4ebf]?)",
                    r"followers?[:\s]*(\d[\d,.]*[KkMm]?)",
                    r"(\d[\d,.]*[\u4e07\u4ebf]?)\s*\u7c89\u4e1d",
                ]
                for pattern in follower_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        follower_str = match.group(1).replace(",", "")
                        try:
                            output["account_metrics"]["follower_count"] = _parse_number(
                                follower_str
                            )
                            break
                        except (ValueError, TypeError, IndexError):
                            pass

                print(
                    f"[collector:playwright_fallback] \u9875\u9762\u5df2\u63d0\u53d6: {url}\n"
                    f"\u6807\u9898: {page_title}\n"
                    "\u6ce8\u610f: Playwright \u515c\u5e95\u6a21\u5f0f\u53ea\u80fd\u63d0\u53d6\u9875\u9762\u4e0a\u53ef\u89c1\u7684\u6587\u672c\uff0c\u7ed3\u6784\u5316\u6570\u636e\u6709\u9650\u3002\n"
                    "\u5efa\u8bae\u4f18\u5148\u4f7f\u7528\u7279\u5b9a\u5e73\u53f0\u7684 source\uff08\u5982 bilibili_api\uff09\u3002",
                    file=sys.stderr,
                )
            except Exception as exc:
                print(
                    f"[collector:playwright_fallback] \u9875\u9762\u8bbf\u95ee\u5931\u8d25: {exc}\n"
                    "\u8bf7\u68c0\u67e5 URL \u662f\u5426\u6b63\u786e\uff0c\u6216\u5c1d\u8bd5\u5176\u4ed6\u6570\u636e\u6e90\u3002",
                    file=sys.stderr,
                )
            finally:
                browser.close()
    except Exception as exc:
        print(
            f"[collector:playwright_fallback] Playwright \u542f\u52a8\u5931\u8d25: {exc}\n"
            "\u66ff\u4ee3\u65b9\u6848: \u4f7f\u7528 --source bilibili_api \u91c7\u96c6 B\u7ad9\u6570\u636e\u3002",
            file=sys.stderr,
        )

    if not any_success:
        print(
            "[collector:playwright_fallback] \u9875\u9762\u63d0\u53d6\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u7f51\u7edc\u8fde\u63a5\u6216 URL \u662f\u5426\u6b63\u786e\u3002\n"
            "\u66ff\u4ee3\u65b9\u6848: \u4f7f\u7528 --source bilibili_api \u91c7\u96c6 B\u7ad9\u6570\u636e\u3002",
            file=sys.stderr,
        )

    return output


def collect_creator_center(creator_id: str, competitor_id: str) -> dict:
    output = _build_output("creator_center", competitor_id)
    print(
        "[collector:creator_center] 提示: 抖音创作者中心需要登录认证。\n"
        "替代方案:\n"
        "  - --source bilibili_api : B站公开API（无需登录）\n"
        "  - --source playwright_fallback : 通用页面提取",
        file=sys.stderr,
    )
    return output


def _annotate_freshness(output: dict) -> dict:
    """对采集到的 recent_videos 做时效判定，并汇总到 freshness_summary。

    - 每条视频补充 _freshness / _days_since / _checked_at
    - 汇总 newest_publish_date、各档计数、运行锚点
    - 若最新一条视频已 aging/stale，向 stderr 给出显式提醒（防止把旧时间内容当作当下规律）
    源无关：任何填充了 recent_videos[*].publish_date 的采集源都会被覆盖。
    """
    videos = output.get("recent_videos") or []
    if _FRESH is None:
        output["freshness_summary"] = {
            "available": False,
            "note": "时效锁工具未加载，未做新鲜度判定，请人工核对视频发布时间。",
        }
        return output

    anchor = _FRESH.now_anchor()
    counts = {"fresh": 0, "aging": 0, "stale": 0, "unknown": 0}
    newest_dt = None
    newest_raw = None
    for v in videos:
        _FRESH.annotate(v, date_field="publish_date")
        counts[v.get("_freshness", "unknown")] = counts.get(v.get("_freshness", "unknown"), 0) + 1
        dt = _FRESH.parse_publish_date(v.get("publish_date"))
        if dt is not None and (newest_dt is None or dt > newest_dt):
            newest_dt = dt
            newest_raw = v.get("publish_date")

    newest_label = _FRESH.freshness_label(newest_raw) if newest_raw is not None else "unknown"
    output["freshness_summary"] = {
        "available": True,
        "anchor": anchor.isoformat(),
        "newest_publish_date": newest_raw,
        "newest_freshness": newest_label,
        "counts": counts,
        "total": len(videos),
    }

    if videos:
        if newest_label == "stale":
            print(
                f"[collector:freshness] ⚠️ 该账号最新视频距今已超过硬上限（最新发布 {newest_raw}），"
                "抓到的极可能是旧时间内容，规律可能已失效——请确认是否换更活跃的对标账号或核对抓取范围。",
                file=sys.stderr,
            )
        elif newest_label == "aging":
            print(
                f"[collector:freshness] 提示：该账号最新视频已偏旧（最新发布 {newest_raw}），"
                "分析结论需标注时效，建议优先参考近期作品。",
                file=sys.stderr,
            )
        elif newest_label == "unknown":
            print(
                "[collector:freshness] 提示：无法解析该账号视频发布时间，未能判定时效，请人工核对是否为近期内容。",
                file=sys.stderr,
            )
    return output


def _source_collected_data(output: dict) -> bool:
    metrics = output.get("account_metrics", {})
    for val in metrics.values():
        if val is not None:
            return True
    videos = output.get("recent_videos", [])
    if len(videos) > 0:
        return True
    raw = output.get("raw_source")
    if raw is not None:
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Yang.skills \u591a\u6e90\u6570\u636e\u91c7\u96c6\u7ba1\u7ebf - Multi-source competitor data collection"
    )
    parser.add_argument(
        "competitor_url_or_id",
        help="\u7ade\u54c1 URL \u6216\u5e73\u53f0 ID\uff08B\u7ad9 UID\u3001\u6296\u97f3\u4e3b\u9875\u94fe\u63a5\u7b49\uff09",
    )
    parser.add_argument(
        "--source",
        required=True,
        choices=["bilibili_api", "oceanengine", "playwright_fallback", "creator_center"],
        help="\u6570\u636e\u6e90\u7c7b\u578b",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="\u8f93\u51fa JSON \u6587\u4ef6\u8def\u5f84",
    )

    args = parser.parse_args()

    competitor_id = _generate_id()

    if args.source == "bilibili_api":
        result = collect_bilibili_api(args.competitor_url_or_id, competitor_id)
    elif args.source == "oceanengine":
        result = collect_oceanengine(args.competitor_url_or_id, competitor_id)
    elif args.source == "playwright_fallback":
        result = collect_playwright_fallback(args.competitor_url_or_id, competitor_id)
    elif args.source == "creator_center":
        result = collect_creator_center(args.competitor_url_or_id, competitor_id)
    else:
        print(
            f"[collector] \u672a\u77e5\u6570\u636e\u6e90: {args.source}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not _source_collected_data(result):
        print(
            f"[collector] \u6570\u636e\u6e90 '{args.source}' \u91c7\u96c6\u5931\u8d25\uff0c\u672a\u83b7\u53d6\u5230\u4efb\u4f55\u6709\u6548\u6570\u636e\u3002\n"
            "\u8bf7\u68c0\u67e5\u8f93\u5165\u53c2\u6570\u6216\u5c1d\u8bd5\u5176\u4ed6 --source \u9009\u9879\u3002",
            file=sys.stderr,
        )
        sys.exit(1)

    _annotate_freshness(result)

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"[collector] \u6570\u636e\u5df2\u4fdd\u5b58\u81f3: {args.output}")
    except Exception as exc:
        print(
            f"[collector] \u6587\u4ef6\u5199\u5165\u5931\u8d25: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()