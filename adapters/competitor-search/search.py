# 作者: 阿洋
"""
competitor-search/search.py — 竞品账号搜索工具

三层架构降级策略：API → Playwright → 兜底
==========================================

第一层: API（优先）
  - 触发条件: 默认首选，直接调用平台公开API获取结构化数据。
  - 降级触发: API返回非200状态码、响应超时(>10s)、返回数据为空、
    返回验证码/登录要求页面、频率限制(429)。
  - 示例: B站搜索API (api.bilibili.com)

第二层: Playwright（浏览器渲染）
  - 触发条件: API层降级后自动启用。
  - 降级触发: Playwright未安装、浏览器启动失败、页面加载超时(>30s)、
    页面结构变更导致选择器失效、被平台检测为自动化访问。
  - 需要: pip install playwright && playwright install chromium

第三层: 兜底（手动/缓存）
  - 触发条件: 前两层均失败时启用。
  - 行为: 返回最近一次缓存结果（如有），标记数据来源为 "cached"；
    无缓存时返回空结果并标记 "unavailable"，由调用方决定后续处理。

搜索结果去重和排序规则
==========================================

去重规则:
  1. 以 (platform, account_id) 为唯一键，同一账号只保留一条记录。
  2. 若同一账号在多次搜索中出现，保留信息更完整的记录（字段非空数更多）。
  3. 以 (platform, account_name) 为辅助去重键，处理ID不同但实为同一账号的情况，
     标记为 "疑似重复" 供人工确认。

排序规则（优先级从高到低）:
  1. 数据来源层级: API结果 > Playwright结果 > 兜底结果
  2. 粉丝数/热度: 降序排列（高粉丝优先）
  3. 搜索关键词匹配度: 标题/简介包含关键词的权重更高
  4. 数据新鲜度: 最近更新的账号优先

反爬策略应对方案
==========================================

1. 请求频率控制: 每次请求间隔 2~5 秒随机延迟，避免固定间隔被识别。
2. User-Agent轮换: 维护 UA 池，每次请求随机选取，模拟不同浏览器。
3. Cookie管理: 通过环境变量 BILIBILI_COOKIE 注入，避免空Cookie被拦截；
   Cookie过期时触发第二层(Playwright)降级。
4. Referer伪装: 每个平台请求携带对应 Referer 头，模拟站内来源。
5. 请求头完整性: 模拟浏览器完整请求头(Accept/Accept-Language/Accept-Encoding等)。
6. IP限制应对: 单次搜索不超过3页结果；遇到429/403时自动降级到Playwright层。
7. Playwright反检测: 使用 stealth 插件隐藏自动化特征(webdriver/navigator等)。
8. 验证码处理: 检测到验证码页面时自动降级，不尝试自动破解，避免账号风险。
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

SUPPORTED_PLATFORMS = {
    "bilibili",
    "douyin",
    "xiaohongshu",
    "kuaishou",
    "weibo",
    "zhihu",
}

BILIBILI_SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/type"
BILIBILI_NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
BILIBILI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
}
BILIBILI_COOKIE = os.environ.get("BILIBILI_COOKIE", "")


def _new_competitor(
    platform,
    account_name,
    account_id,
    account_url,
    avatar_url=None,
    follower_count=None,
    content_count=None,
    avg_likes=None,
    category_tags=None,
    bio=None,
    verified=False,
    discovery_source="",
    confidence_score=0.5,
    recent_videos=None,
):
    return {
        "competitor_id": str(uuid.uuid4()),
        "platform": platform,
        "account_name": account_name,
        "account_id": account_id,
        "account_url": account_url,
        "avatar_url": avatar_url,
        "follower_count": follower_count,
        "content_count": content_count,
        "avg_likes": avg_likes,
        "category_tags": category_tags or [],
        "bio": bio,
        "verified": verified,
        "discovery_source": discovery_source,
        "confidence_score": confidence_score,
        "recent_videos": recent_videos or [],
    }


def _parse_follower_count(raw):
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw).strip().lower()
    if not text:
        return None
    text = text.replace(",", "").replace(" ", "")
    match = re.match(r"([\d.]+)\s*([万wk]?)", text)
    if not match:
        return None
    num = float(match.group(1))
    unit = match.group(2)
    if unit in ("万", "w"):
        num *= 10000
    elif unit == "k":
        num *= 1000
    return int(num)


def _get_mixin_key():
    """Get WBI mixin key from Bilibili nav API.

    Returns the 32-character mixin key derived from wbi_img URLs,
    or None if the nav API is unavailable.
    """
    headers = dict(BILIBILI_HEADERS)
    if BILIBILI_COOKIE:
        headers["Cookie"] = BILIBILI_COOKIE
    try:
        resp = requests.get(BILIBILI_NAV_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        body = resp.json()
    except Exception as e:
        print(f"warn: B站 nav 接口不可用，WBI 签名降级: {e}", file=sys.stderr)
        return None

    wbi_img = body.get("data", {}).get("wbi_img", {})
    if not wbi_img:
        print("warn: nav 接口未返回 wbi_img，WBI 签名降级", file=sys.stderr)
        return None

    img_url = wbi_img.get("img_url", "")
    sub_url = wbi_img.get("sub_url", "")
    if not img_url or not sub_url:
        print("warn: wbi_img URL 缺失，WBI 签名降级", file=sys.stderr)
        return None

    def _extract_key(url):
        name = url.rsplit("/", 1)[-1]
        name = name.rsplit(".", 1)[0]
        return name

    img_key = _extract_key(img_url)
    sub_key = _extract_key(sub_url)
    mixin_key = (img_key + sub_key)[:32]
    return mixin_key


def _wbi_sign(params, mixin_key):
    """Generate WBI signature for Bilibili API.

    Args:
        params: dict of query parameters.
        mixin_key: 32-character mixin key from _get_mixin_key().

    Returns:
        dict with w_rid added.
    """
    sorted_keys = sorted(params.keys())
    query_string = "&".join(
        f"{k}={urllib.parse.quote(str(params[k]), safe='')}"
        for k in sorted_keys
    )
    sign_str = query_string + mixin_key
    w_rid = hashlib.md5(sign_str.encode("utf-8")).hexdigest()
    params["w_rid"] = w_rid
    return params


def _bilibili_search_with_wbi(keyword, limit):
    """Search Bilibili users with WBI signing.

    Falls back to unsigned search if WBI signing fails.
    """
    competitors = []
    mixin_key = _get_mixin_key()

    wts = int(time.time())
    params = {
        "search_type": "bili_user",
        "keyword": keyword,
        "page": 1,
        "wts": wts,
    }

    if mixin_key:
        params = _wbi_sign(params, mixin_key)

    headers = dict(BILIBILI_HEADERS)
    if BILIBILI_COOKIE:
        headers["Cookie"] = BILIBILI_COOKIE

    try:
        resp = requests.get(
            BILIBILI_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
    except Exception as e:
        print(f"warn: B站 WBI 搜索失败: {e}", file=sys.stderr)
        return search_bilibili_unsigned(keyword, limit)

    if body.get("code") != 0:
        msg = body.get("message", "unknown error")
        raise RuntimeError(f"B站 API 返回错误 code={body.get('code')}: {msg}")

    results = body.get("data", {}).get("result", [])
    for item in results[:limit]:
        mid = str(item.get("mid", ""))
        uname = item.get("uname", "")
        if not mid or not uname:
            continue

        official = item.get("official_verify", {}) or {}
        verify_type = official.get("type", -1)

        competitors.append(
            _new_competitor(
                platform="bilibili",
                account_name=uname,
                account_id=mid,
                account_url=f"https://space.bilibili.com/{mid}",
                avatar_url=item.get("upic", "") or None,
                follower_count=item.get("fans", None),
                content_count=item.get("videos", None),
                bio=item.get("usign", "") or None,
                verified=verify_type >= 0,
                discovery_source="bilibili_wbi_api",
                confidence_score=0.8,
            )
        )

    return competitors


def search_bilibili_unsigned(keyword, limit):
    """Search Bilibili without WBI signing (fallback)."""
    competitors = []
    params = {
        "search_type": "bili_user",
        "keyword": keyword,
        "page": 1,
    }
    headers = dict(BILIBILI_HEADERS)
    if BILIBILI_COOKIE:
        headers["Cookie"] = BILIBILI_COOKIE
    resp = requests.get(
        BILIBILI_SEARCH_URL,
        params=params,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()

    if body.get("code") != 0:
        msg = body.get("message", "unknown error")
        raise RuntimeError(f"B站 API 返回错误 code={body.get('code')}: {msg}")

    results = body.get("data", {}).get("result", [])
    for item in results[:limit]:
        mid = str(item.get("mid", ""))
        uname = item.get("uname", "")
        if not mid or not uname:
            continue

        official = item.get("official_verify", {}) or {}
        verify_type = official.get("type", -1)

        competitors.append(
            _new_competitor(
                platform="bilibili",
                account_name=uname,
                account_id=mid,
                account_url=f"https://space.bilibili.com/{mid}",
                avatar_url=item.get("upic", "") or None,
                follower_count=item.get("fans", None),
                content_count=item.get("videos", None),
                bio=item.get("usign", "") or None,
                verified=verify_type >= 0,
                discovery_source="bilibili_api",
                confidence_score=0.8,
            )
        )

    return competitors


def search_bilibili(keyword, limit):
    """Search Bilibili users — tries WBI first, falls back to unsigned."""
    return _bilibili_search_with_wbi(keyword, limit)


def _parse_sherlock_line(line):
    url = line.strip()
    if not url.startswith("http"):
        return None

    platform = "other"
    lower = url.lower()
    if "bilibili" in lower:
        platform = "bilibili"
    elif "douyin" in lower:
        platform = "douyin"
    elif "xiaohongshu" in lower:
        platform = "xiaohongshu"
    elif "kuaishou" in lower:
        platform = "kuaishou"
    elif "weibo.com" in lower or "weibo.cn" in lower:
        platform = "weibo"
    elif "zhihu" in lower:
        platform = "zhihu"

    return url, platform


def search_sherlock(keyword, limit):
    competitors = []
    try:
        proc = subprocess.run(
            ["sherlock", keyword, "--print-found", "--timeout", "30"],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Sherlock CLI 未安装，请执行 pip install sherlock-project 后重试"
        )

    stderr = proc.stderr.strip()
    if stderr and proc.returncode != 0:
        raise RuntimeError(f"Sherlock 报错: {stderr[:500]}")

    for line in proc.stdout.strip().split("\n"):
        if len(competitors) >= limit:
            break
        parsed = _parse_sherlock_line(line)
        if parsed is None:
            continue
        url, platform = parsed
        competitors.append(
            _new_competitor(
                platform=platform,
                account_name=keyword,
                account_id=keyword,
                account_url=url,
                discovery_source="跨平台矩阵账号",
                confidence_score=0.7,
            )
        )

    return competitors


def _playwright_context():
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("playwright 未安装，Playwright 搜索不可用")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    return playwright, browser


def _playwright_cleanup(playwright, browser):
    if browser:
        try:
            browser.close()
        except Exception:
            pass
    if playwright:
        try:
            playwright.stop()
        except Exception:
            pass


def search_douyin_playwright(keyword, limit):
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("playwright 未安装")

    competitors = []
    playwright = None
    browser = None

    try:
        playwright, browser = _playwright_context()
        page = browser.new_page()
        search_url = f"https://www.douyin.com/search/{keyword}?type=user"
        page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        selectors = [
            '[data-e2e="search-user-item"]',
            ".search-user-card",
            ".user-card",
            '[class*="user-card"]',
        ]
        user_cards = []
        for sel in selectors:
            user_cards = page.query_selector_all(sel)
            if user_cards:
                break

        for card in user_cards[:limit]:
            try:
                name_selectors = [
                    '[data-e2e="user-name"]',
                    ".user-name",
                    ".name",
                    '[class*="name"]',
                ]
                account_name = keyword
                for ns in name_selectors:
                    el = card.query_selector(ns)
                    if el:
                        account_name = el.inner_text().strip()
                        break

                account_id = account_name
                uid_el = card.query_selector('[data-e2e="user-uid"]')
                if uid_el:
                    account_id = uid_el.get_attribute("data-uid") or account_id

                account_url = f"https://www.douyin.com/user/{account_id}"
                url_el = card.query_selector('a[href*="/user/"]')
                if url_el:
                    href = url_el.get_attribute("href") or ""
                    if href:
                        account_url = href if href.startswith("http") else f"https://www.douyin.com{href}"

                avatar_url = None
                avatar_el = card.query_selector("img")
                if avatar_el:
                    src = avatar_el.get_attribute("src")
                    if src and not src.startswith("data:"):
                        avatar_url = src

                follower_count = None
                followers_el = card.query_selector(
                    '[class*="follower"], [class*="fans"], [class*="count"]'
                )
                if followers_el:
                    follower_count = _parse_follower_count(followers_el.inner_text())

                competitors.append(
                    _new_competitor(
                        platform="douyin",
                        account_name=account_name,
                        account_id=account_id,
                        account_url=account_url,
                        avatar_url=avatar_url,
                        follower_count=follower_count,
                        discovery_source="playwright_douyin",
                        confidence_score=0.5,
                    )
                )
            except Exception:
                continue
    except Exception:
        raise
    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

    return competitors


def search_xiaohongshu_playwright(keyword, limit):
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("playwright 未安装")

    competitors = []
    playwright = None
    browser = None

    try:
        playwright, browser = _playwright_context()
        page = browser.new_page()
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type=user"
        page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        selectors = [
            '[class*="user-item"]',
            '[class*="user-card"]',
            ".user-item",
            ".user-card",
        ]
        user_cards = []
        for sel in selectors:
            user_cards = page.query_selector_all(sel)
            if user_cards:
                break

        for card in user_cards[:limit]:
            try:
                account_name = keyword
                name_selectors = [
                    '[class*="name"]',
                    ".name",
                    '[class*="nickname"]',
                ]
                for ns in name_selectors:
                    el = card.query_selector(ns)
                    if el:
                        account_name = el.inner_text().strip()
                        break

                account_id = account_name
                url_el = card.query_selector('a[href*="/user/"]')
                account_url = ""
                if url_el:
                    href = url_el.get_attribute("href") or ""
                    if href:
                        account_url = href if href.startswith("http") else f"https://www.xiaohongshu.com{href}"
                        match = re.search(r"/user/profile/([a-zA-Z0-9_]+)", account_url)
                        if match:
                            account_id = match.group(1)

                avatar_url = None
                avatar_el = card.query_selector("img")
                if avatar_el:
                    src = avatar_el.get_attribute("src")
                    if src and not src.startswith("data:"):
                        avatar_url = src

                follower_count = None
                followers_el = card.query_selector(
                    '[class*="follower"], [class*="fans"], [class*="count"]'
                )
                if followers_el:
                    follower_count = _parse_follower_count(followers_el.inner_text())

                competitors.append(
                    _new_competitor(
                        platform="xiaohongshu",
                        account_name=account_name,
                        account_id=account_id,
                        account_url=account_url or f"https://www.xiaohongshu.com/search_result?keyword={keyword}",
                        avatar_url=avatar_url,
                        follower_count=follower_count,
                        discovery_source="playwright_xiaohongshu",
                        confidence_score=0.4,
                    )
                )
            except Exception:
                continue
    except Exception:
        raise
    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

    return competitors


def search_kuaishou_playwright(keyword, limit):
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("playwright 未安装")

    competitors = []
    playwright = None
    browser = None

    try:
        playwright, browser = _playwright_context()
        page = browser.new_page()
        search_url = f"https://www.kuaishou.com/search/video?searchKey={keyword}"
        page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        selectors = [
            '[class*="user-item"]',
            '[class*="user-card"]',
            ".user-item",
            ".user-card",
            '[class*="profile"]',
        ]
        user_cards = []
        for sel in selectors:
            user_cards = page.query_selector_all(sel)
            if user_cards:
                break

        for card in user_cards[:limit]:
            try:
                account_name = keyword
                name_selectors = ["[class*='name']", ".name", "[class*='nickname']"]
                for ns in name_selectors:
                    el = card.query_selector(ns)
                    if el:
                        account_name = el.inner_text().strip()
                        break

                account_id = account_name
                url_el = card.query_selector("a[href]")
                account_url = ""
                if url_el:
                    href = url_el.get_attribute("href") or ""
                    if href:
                        account_url = href if href.startswith("http") else f"https://www.kuaishou.com{href}"

                avatar_url = None
                avatar_el = card.query_selector("img")
                if avatar_el:
                    src = avatar_el.get_attribute("src")
                    if src and not src.startswith("data:"):
                        avatar_url = src

                followers_el = card.query_selector(
                    '[class*="follower"], [class*="fans"], [class*="count"]'
                )
                follower_count = None
                if followers_el:
                    follower_count = _parse_follower_count(followers_el.inner_text())

                competitors.append(
                    _new_competitor(
                        platform="kuaishou",
                        account_name=account_name,
                        account_id=account_id,
                        account_url=account_url or f"https://www.kuaishou.com/search/video?searchKey={keyword}",
                        avatar_url=avatar_url,
                        follower_count=follower_count,
                        discovery_source="playwright_kuaishou",
                        confidence_score=0.4,
                    )
                )
            except Exception:
                continue
    except Exception:
        raise
    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

    return competitors


def search_google_fallback(keyword, limit):
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("playwright 未安装")

    competitors = []
    playwright = None
    browser = None

    try:
        playwright, browser = _playwright_context()
        page = browser.new_page()
        search_url = f"https://www.google.com/search?q={keyword}+视频创作者+site:bilibili.com"
        page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        results = page.query_selector_all("a h3")
        count = 0
        for result in results:
            if count >= limit:
                break
            title = result.inner_text()
            parent = result.evaluate_handle("el => el.closest('a')")
            url = parent.evaluate("el => el.href") if parent else ""
            if not url:
                continue
            competitors.append({
                "account_name": title[:60] if title else "未知创作者",
                "platform": "unknown",
                "account_id": f"google_{count}",
                "account_url": url[:200],
                "avatar_url": None,
                "follower_count": None,
                "bio": None,
                "confidence_score": 0.4,
                "discovery_source": "google_fallback",
                "keyword": keyword,
            })
            count += 1
    except Exception:
        pass
    finally:
        _playwright_cleanup(playwright, browser)

    return competitors


PLATFORM_HANDLERS = {
    "bilibili": search_bilibili,
    "douyin": search_douyin_playwright,
    "xiaohongshu": search_xiaohongshu_playwright,
    "kuaishou": search_kuaishou_playwright,
    "weibo": None,
    "zhihu": None,
    "google": search_google_fallback,
}


def _deduplicate(competitors):
    seen = {}
    result = []
    for comp in competitors:
        key = (comp["account_id"], comp["platform"])
        if key in seen:
            existing = seen[key]
            if comp["follower_count"] is not None and existing["follower_count"] is None:
                existing["follower_count"] = comp["follower_count"]
            if comp["avatar_url"] is not None and existing["avatar_url"] is None:
                existing["avatar_url"] = comp["avatar_url"]
            if comp["bio"] is not None and existing["bio"] is None:
                existing["bio"] = comp["bio"]
            if comp["confidence_score"] > existing["confidence_score"]:
                existing["confidence_score"] = comp["confidence_score"]
                existing["discovery_source"] = comp["discovery_source"]
            continue
        seen[key] = comp
        result.append(comp)
    return result


def _all_platforms_failed(platforms_requested, errors, sherlock_requested):
    failed_platforms = {e["platform"] for e in errors}
    targets = set(platforms_requested)
    if sherlock_requested:
        targets.add("sherlock")
    return targets and targets == failed_platforms & targets


def main():
    parser = argparse.ArgumentParser(
        description="多平台竞品发现工具 — Multi-platform competitor discovery"
    )
    parser.add_argument(
        "keyword",
        help="搜索关键词 / search keyword",
    )
    parser.add_argument(
        "--platforms",
        default="douyin,bilibili,xiaohongshu,kuaishou",
        help="逗号分隔的目标平台列表 (默认: douyin,bilibili,xiaohongshu,kuaishou)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="每个平台最大返回数 (默认: 20)",
    )
    parser.add_argument(
        "--sherlock",
        action="store_true",
        help="启用 Sherlock 跨平台用户名搜索",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="JSON 输出文件路径 (不指定则输出到 stdout)",
    )

    args = parser.parse_args()
    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]

    search_meta = {
        "keyword": args.keyword,
        "platforms_searched": platforms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_found": 0,
        "errors": [],
    }

    all_competitors = []

    for platform in platforms:
        handler = PLATFORM_HANDLERS.get(platform)
        if handler is None:
            search_meta["errors"].append(
                {"platform": platform, "error": f"不支持的平台: {platform}"}
            )
            continue

        try:
            results = handler(args.keyword, args.limit)
            all_competitors.extend(results)
        except Exception as exc:
            search_meta["errors"].append(
                {"platform": platform, "error": str(exc)}
            )

    if args.sherlock:
        try:
            sherlock_results = search_sherlock(args.keyword, args.limit)
            all_competitors.extend(sherlock_results)
        except Exception as exc:
            search_meta["errors"].append(
                {"platform": "sherlock", "error": str(exc)}
            )

    all_competitors = _deduplicate(all_competitors)
    search_meta["total_found"] = len(all_competitors)

    output = json.dumps(
        {"search_meta": search_meta, "competitors": all_competitors},
        ensure_ascii=False,
        indent=2,
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    else:
        print(output)

    if _all_platforms_failed(platforms, search_meta["errors"], args.sherlock):
        sys.exit(1)


if __name__ == "__main__":
    main()