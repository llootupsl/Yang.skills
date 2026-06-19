# 作者: 阿洋
"""Competitor monitoring system for Yang.skills

CLI commands:
  python monitor.py --add <competitor_id> --interval-hours <n>
  python monitor.py --remove <competitor_id>
  python monitor.py --list
  python monitor.py --check [<competitor_id>]
"""

import argparse
import sys
import os
import json
import sqlite3
import time
import hashlib
import xml.etree.ElementTree as ET
import subprocess
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from adapters.data_pipeline import db as db_module
except ImportError:
    try:
        import importlib
        db_module = importlib.import_module("..data_pipeline.db", package="adapters.competitor_monitor")
    except ImportError:
        _db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data_pipeline')
        sys.path.insert(0, _db_dir)
        import db as db_module

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RSSHUB_BASE = "https://rsshub.app"

PLATFORM_RSS_ROUTES = {
    "bilibili": "/bilibili/user/video/{account_id}",
    "weibo": "/weibo/user/{account_id}",
    "zhihu": "/zhihu/people/activities/{account_id}",
}

RSS_FETCH_TIMEOUT = 30
PLAYWRIGHT_TIMEOUT = 120


def _get_db_conn(db_path="project_data.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _get_monitor_by_competitor(competitor_id, db_path="project_data.db"):
    conn = _get_db_conn(db_path)
    row = conn.execute("SELECT * FROM competitor_monitors WHERE competitor_id = ? AND is_enabled = 1", (competitor_id,)).fetchone()
    conn.close()
    return row


def _disable_monitor(competitor_id, db_path="project_data.db"):
    conn = _get_db_conn(db_path)
    conn.execute("UPDATE competitor_monitors SET is_enabled = 0 WHERE competitor_id = ?", (competitor_id,))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected


def _update_last_checked(monitor_id, db_path="project_data.db"):
    conn = _get_db_conn(db_path)
    conn.execute("UPDATE competitor_monitors SET last_checked_at = datetime('now') WHERE id = ?", (monitor_id,))
    conn.commit()
    conn.close()


def _update_last_video_found(monitor_id, video_date_str, db_path="project_data.db"):
    conn = _get_db_conn(db_path)
    conn.execute("UPDATE competitor_monitors SET last_video_found_at = ? WHERE id = ?", (video_date_str, monitor_id))
    conn.commit()
    conn.close()


def _get_competitor_name(competitor_id, db_path="project_data.db"):
    comp = db_module.get_competitor_by_id(competitor_id, db_path)
    if comp:
        return comp.get("account_name", competitor_id)
    return competitor_id


def _rsshub_url(platform, account_id):
    route_template = PLATFORM_RSS_ROUTES.get(platform)
    if not route_template:
        return None
    return f"{RSSHUB_BASE}{route_template.format(account_id=account_id)}"


def _detect_monitor_type(platform):
    if platform in PLATFORM_RSS_ROUTES:
        return "rsshub"
    return "playwright_poll"


def _parse_rss_date(date_str):
    if not date_str:
        return None
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str.strip())
    except Exception:
        return None


def _parse_last_video_found(value):
    if not value:
        return None
    return _parse_rss_date(value)


def _fetch_rss_feed(rss_url):
    try:
        resp = requests.get(rss_url, timeout=RSS_FETCH_TIMEOUT, headers={
            "User-Agent": "Yang.skills-CompetitorMonitor/4.5",
        })
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            return ("json", resp.json())
        return ("xml", resp.text)
    except requests.exceptions.Timeout:
        print(f"  [WARN] RSS 获取超时 ({RSS_FETCH_TIMEOUT}s): {rss_url}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [WARN] RSS 获取失败: {e}", file=sys.stderr)
        return None


def _extract_entries_rss(rss_data, content_type):
    entries = []
    if content_type == "json":
        data = rss_data
        items = data.get("items", data.get("data", {}).get("items", []))
        if not isinstance(items, list):
            items = []
        for item in items:
            entries.append({
                "title": item.get("title", ""),
                "url": item.get("link", item.get("url", "")),
                "published": item.get("pubDate", item.get("date_published", item.get("published", ""))),
            })
    else:
        xml_text = rss_data
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []
        ns_map = {"atom": "http://www.w3.org/2005/Atom"}
        is_atom = root.tag in ("{http://www.w3.org/2005/Atom}feed", "feed")
        if is_atom:
            for entry in root.findall("atom:entry", ns_map) or root.findall("entry"):
                link_el = entry.find("atom:link", ns_map) or entry.find("link")
                link = link_el.get("href", link_el.text or "") if link_el is not None else ""
                title_el = entry.find("atom:title", ns_map) or entry.find("title")
                title = title_el.text or "" if title_el is not None else ""
                pub_el = entry.find("atom:published", ns_map) or entry.find("published") or entry.find("atom:updated", ns_map) or entry.find("updated")
                published = pub_el.text or "" if pub_el is not None else ""
                entries.append({"title": title, "url": link, "published": published})
        else:
            for item in root.findall(".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate")
                entries.append({
                    "title": title_el.text or "" if title_el is not None else "",
                    "url": link_el.text or "" if link_el is not None else "",
                    "published": pub_el.text or "" if pub_el is not None else "",
                })
    return entries


def _run_pipeline_for_video(video_url, competitor_name):
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    url_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
    video_id = f"auto-{date_str}-{competitor_name}-{url_hash}"
    pipeline_script = os.path.join(PROJECT_ROOT, "adapters", "benchmark-analysis", "pipeline.py")
    if not os.path.isfile(pipeline_script):
        print(f"  [WARN] pipeline.py 不存在: {pipeline_script}", file=sys.stderr)
        return False
    try:
        result = subprocess.run(
            [sys.executable, pipeline_script, video_url, "--video-id", video_id],
            capture_output=True, text=True, timeout=600,
            cwd=PROJECT_ROOT,
        )
        if result.returncode == 0:
            print(f"  [OK] Pipeline 完成: {video_id}")
            return True
        else:
            print(f"  [WARN] Pipeline 失败 (exit={result.returncode}): {video_id}")
            if result.stderr.strip():
                print(f"    stderr: {result.stderr.strip()[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  [WARN] Pipeline 超时 (600s): {video_id}")
        return False
    except Exception as e:
        print(f"  [WARN] Pipeline 异常: {e}")
        return False


def _check_rsshub(monitor):
    monitor_id = monitor["id"]
    competitor_id = monitor["competitor_id"]
    rss_url = monitor["rss_url"]
    last_video_found = _parse_last_video_found(monitor.get("last_video_found_at"))
    competitor_name = _get_competitor_name(competitor_id)

    if not rss_url:
        print(f"  [WARN] 没有 RSS URL，跳过", file=sys.stderr)
        return (competitor_name, 0, 0)

    data = _fetch_rss_feed(rss_url)
    if data is None:
        return (competitor_name, 0, 1)

    content_type, rss_data = data
    entries = _extract_entries_rss(rss_data, content_type)
    if not entries:
        print(f"  [WARN] RSS 中没有条目", file=sys.stderr)
        _update_last_checked(monitor_id)
        return (competitor_name, 0, 0)

    new_entries = []
    newest_date = None
    for entry in entries:
        pub_date = _parse_rss_date(entry["published"])
        if pub_date is None:
            continue
        if newest_date is None or pub_date > newest_date:
            newest_date = pub_date
        if last_video_found is None or pub_date > last_video_found:
            new_entries.append(entry)

    if last_video_found is None and new_entries:
        newest_str = newest_date.strftime("%Y-%m-%d %H:%M:%S") if newest_date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _update_last_video_found(monitor_id, newest_str)
        _update_last_checked(monitor_id)
        print(f"  [INFO] 初始化基线: 最近视频 {newest_str}, 跳过 {len(new_entries)} 条历史")
        return (competitor_name, 0, 0)

    for entry in new_entries:
        print(f"  [NEW] {entry['title'][:80]}")
        print(f"        {entry['url']}")
        _run_pipeline_for_video(entry["url"], competitor_name)

    if newest_date:
        newest_str = newest_date.strftime("%Y-%m-%d %H:%M:%S")
        _update_last_video_found(monitor_id, newest_str)

    _update_last_checked(monitor_id)
    return (competitor_name, len(new_entries), 0)


def _check_playwright_poll(monitor):
    monitor_id = monitor["id"]
    competitor_id = monitor["competitor_id"]
    last_video_found = _parse_last_video_found(monitor.get("last_video_found_at"))
    competitor_name = _get_competitor_name(competitor_id)
    competitor = db_module.get_competitor_by_id(competitor_id)
    if not competitor:
        print(f"  [WARN] 竞品不存在: {competitor_id}", file=sys.stderr)
        return (competitor_name, 0, 1)

    account_url = competitor.get("account_url", "")
    if not account_url:
        print(f"  [WARN] 没有竞品页面 URL", file=sys.stderr)
        _update_last_checked(monitor_id)
        return (competitor_name, 0, 1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(f"  [WARN] playwright 未安装，跳过 Playwright 轮询", file=sys.stderr)
        _update_last_checked(monitor_id)
        return (competitor_name, 0, 1)

    print(f"  [PLAYWRIGHT] 打开 {account_url[:100]}")
    new_videos = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            try:
                page.goto(account_url, timeout=PLAYWRIGHT_TIMEOUT * 1000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"  [WARN] 页面加载失败: {e}", file=sys.stderr)
                browser.close()
                _update_last_checked(monitor_id)
                return (competitor_name, 0, 1)

            videos = page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a'));
                const seen = new Set();
                const results = [];
                links.forEach(a => {
                    const href = a.href || '';
                    const text = (a.textContent || '').trim();
                    if (!href || !text || seen.has(href)) return;
                    if (href.includes('/video/') || href.includes('/v/') || href.includes('/watch') || href.includes('/play/') || href.includes('/item/')) {
                        seen.add(href);
                        results.push({ title: text.substring(0, 200), url: href });
                    }
                });
                return results.slice(0, 20);
            }""")

            if not videos:
                print(f"  [WARN] 未提取到视频链接", file=sys.stderr)

            for video in videos:
                url = video.get("url", "")
                if not url:
                    continue
                full_url = url
                if url.startswith("/"):
                    parsed_base = account_url.rstrip("/")
                    full_url = f"{parsed_base}{url}"
                pub_date = _parse_rss_date(video.get("published", ""))
                if pub_date and last_video_found and pub_date <= last_video_found:
                    continue
                new_videos.append({"title": video.get("title", ""), "url": full_url})

            browser.close()
    except Exception as e:
        print(f"  [WARN] Playwright 异常: {e}", file=sys.stderr)
        _update_last_checked(monitor_id)
        return (competitor_name, 0, 1)

    if last_video_found is None and new_videos:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _update_last_video_found(monitor_id, now_str)
        _update_last_checked(monitor_id)
        print(f"  [INFO] 初始化基线: 跳过 {len(new_videos)} 条历史")
        return (competitor_name, 0, 0)

    for video in new_videos:
        print(f"  [NEW] {video['title'][:80]}")
        print(f"        {video['url']}")
        _run_pipeline_for_video(video["url"], competitor_name)

    if new_videos:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _update_last_video_found(monitor_id, now_str)

    _update_last_checked(monitor_id)
    return (competitor_name, len(new_videos), 0)


def _check_single_monitor(monitor):
    monitor_type = monitor.get("platform_monitor_type", "")
    if monitor_type == "rsshub":
        return _check_rsshub(monitor)
    elif monitor_type == "playwright_poll":
        return _check_playwright_poll(monitor)
    else:
        monitor_id = monitor["id"]
        competitor_id = monitor["competitor_id"]
        competitor_name = _get_competitor_name(competitor_id)
        print(f"  [WARN] 未知 monitor_type: {monitor_type}", file=sys.stderr)
        _update_last_checked(monitor_id)
        return (competitor_name, 0, 1)


def add_monitor(competitor_id, interval_hours):
    competitor = db_module.get_competitor_by_id(competitor_id)
    if not competitor:
        print(f"错误: 竞品 {competitor_id} 不存在", file=sys.stderr)
        sys.exit(1)

    platform = competitor.get("platform", "")
    account_id = competitor.get("account_id", "")
    account_name = competitor.get("account_name", competitor_id)

    monitor_type = _detect_monitor_type(platform)
    rss_url = _rsshub_url(platform, account_id) if monitor_type == "rsshub" else None

    existing = _get_monitor_by_competitor(competitor_id)
    if existing:
        conn = _get_db_conn()
        conn.execute("DELETE FROM competitor_monitors WHERE competitor_id = ?", (competitor_id,))
        conn.commit()
        conn.close()

    config = {
        "rss_url": rss_url,
        "platform_monitor_type": monitor_type,
        "check_interval_hours": interval_hours,
        "is_enabled": 1,
    }
    row_id = db_module.insert_competitor_monitor(competitor_id, config)
    if not row_id:
        print(f"错误: 添加监控失败", file=sys.stderr)
        sys.exit(1)

    print(f"已添加监控: {account_name} ({platform}) [{monitor_type}] 间隔 {interval_hours}h")

    monitor = _get_monitor_by_competitor(competitor_id)
    if monitor:
        print(f"立即检查 {account_name}...")
        name, new_count, failed = _check_single_monitor(dict(monitor))
        if new_count > 0:
            print(f"  发现 {new_count} 条新视频并已触发 pipeline")
        elif failed:
            print(f"  检查时遇到问题")
        else:
            print(f"  暂无新视频")


def remove_monitor(competitor_id):
    existing = _get_monitor_by_competitor(competitor_id)
    if not existing:
        print(f"错误: 未找到竞品 {competitor_id} 的监控记录", file=sys.stderr)
        sys.exit(1)

    competitor_name = _get_competitor_name(competitor_id)
    affected = _disable_monitor(competitor_id)
    if affected:
        print(f"已移除监控: {competitor_name} ({competitor_id})")
    else:
        print(f"警告: 删除操作未影响任何行", file=sys.stderr)


def list_monitors():
    monitors = db_module.get_active_monitors()
    if not monitors:
        print("当前没有活跃的竞品监控")
        return

    print(f"{'竞品名称':<20} {'平台':<12} {'监控类型':<16} {'间隔(h)':<10} {'上次检查':<20} {'最近视频':<20}")
    print("-" * 110)
    for m in monitors:
        name = _get_competitor_name(m["competitor_id"])
        platform = ""
        comp = db_module.get_competitor_by_id(m["competitor_id"])
        if comp:
            platform = comp.get("platform", "")
        monitor_type = m.get("platform_monitor_type", "—")
        interval = str(m.get("check_interval_hours", "—"))
        last_checked = str(m.get("last_checked_at") or "—")
        last_video = str(m.get("last_video_found_at") or "—")
        print(f"{name:<20} {platform:<12} {monitor_type:<16} {interval:<10} {last_checked:<20} {last_video:<20}")


def check_monitors(competitor_id=None):
    if competitor_id:
        monitor = _get_monitor_by_competitor(competitor_id)
        if not monitor:
            print(f"错误: 未找到竞品 {competitor_id} 的活跃监控", file=sys.stderr)
            sys.exit(1)
        monitors = [dict(monitor)]
    else:
        monitors = db_module.get_active_monitors()

    if not monitors:
        print("当前没有活跃的竞品监控")
        return

    total = len(monitors)
    total_new = 0
    total_failed = 0
    for monitor in monitors:
        competitor_id = monitor["competitor_id"]
        competitor_name = _get_competitor_name(competitor_id)
        print(f"\n检查: {competitor_name} ({competitor_id}) [{monitor.get('platform_monitor_type', '—')}]")
        name, new_count, failed = _check_single_monitor(monitor)
        total_new += new_count
        total_failed += failed
        if failed:
            print(f"  检查失败")

    print(f"\n检查了 {total} 个竞品，发现 {total_new} 条新视频", end="")
    if total_failed:
        print(f"，{total_failed} 个检查失败", end="")
    print()


def main():
    parser = argparse.ArgumentParser(description="竞品监控系统 - Yang.skills")
    parser.add_argument("--add", type=str, default=None, metavar="COMPETITOR_ID", help="添加竞品监控")
    parser.add_argument("--remove", type=str, default=None, metavar="COMPETITOR_ID", help="移除竞品监控")
    parser.add_argument("--list", action="store_true", default=False, help="列出所有活跃监控")
    parser.add_argument("--check", type=str, default=None, nargs="?", const="__all__", metavar="COMPETITOR_ID", help="检查竞品更新（可选指定竞品 ID）")
    parser.add_argument("--interval-hours", type=int, default=24, help="检查间隔（小时），默认 24")

    args = parser.parse_args()

    if args.add:
        add_monitor(args.add, args.interval_hours)
    elif args.remove:
        remove_monitor(args.remove)
    elif args.list:
        list_monitors()
    elif args.check is not None:
        cid = None if args.check == "__all__" else args.check
        check_monitors(cid)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()