# 作者: 阿洋
"""本地竞品搜索工具（零网络 · 零外部依赖）。

从本地 JSON/CSV 数据库搜索竞品信息，输出与 search.py 完全一致的 JSON 结构，
供 yang-competitor-search 在离线环境下使用。

设计原则
--------
- **零网络**：不发起任何 HTTP 请求，不依赖 requests / playwright。
- **零外部依赖**：仅使用 Python 标准库。
- **格式兼容**：输出结构与 search.py 的 main() 完全一致。
- **多格式支持**：自动识别 JSON 和 CSV 格式的本地数据库。

用法
----
  python local_search.py "考研" --platforms douyin,bilibili
  python local_search.py "考研" --db ./local-data/competitors.json
  python local_search.py "考研" --db ./local-data/competitors.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


SUPPORTED_PLATFORMS = {"bilibili", "douyin", "xiaohongshu", "kuaishou", "weibo", "zhihu"}


def _new_competitor(
    platform, account_name, account_id, account_url,
    avatar_url=None, follower_count=None, content_count=None,
    avg_likes=None, category_tags=None, bio=None, verified=False,
    discovery_source="local_db", confidence_score=0.5, recent_videos=None,
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


def _load_json_db(db_path: Path) -> list[dict]:
    """加载 JSON 格式的竞品数据库。"""
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[local_search] 无法读取 {db_path}: {e}", file=sys.stderr)
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("competitors", "items", "data", "results"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return [data]
    return []


def _load_csv_db(db_path: Path) -> list[dict]:
    """加载 CSV 格式的竞品数据库。"""
    items = []
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(dict(row))
    except OSError as e:
        print(f"[local_search] 无法读取 {db_path}: {e}", file=sys.stderr)
    return items


def _normalize_entry(entry: dict) -> dict | None:
    """将数据库条目标准化为 competitor 结构。"""
    platform = entry.get("platform", "").lower().strip()
    account_name = entry.get("account_name") or entry.get("name") or entry.get("nickname") or ""
    account_id = entry.get("account_id") or entry.get("uid") or entry.get("mid") or account_name

    if not account_name:
        return None

    account_url = entry.get("account_url") or entry.get("url") or entry.get("link") or ""
    if not account_url and platform and account_id:
        url_templates = {
            "bilibili": f"https://space.bilibili.com/{account_id}",
            "douyin": f"https://www.douyin.com/user/{account_id}",
            "xiaohongshu": f"https://www.xiaohongshu.com/user/profile/{account_id}",
            "weibo": f"https://weibo.com/u/{account_id}",
            "zhihu": f"https://www.zhihu.com/people/{account_id}",
        }
        account_url = url_templates.get(platform, "")

    follower_count = entry.get("follower_count") or entry.get("fans") or entry.get("followers")
    if isinstance(follower_count, str):
        follower_count = _parse_follower_count(follower_count)

    content_count = entry.get("content_count") or entry.get("videos")
    if isinstance(content_count, str):
        try:
            content_count = int(content_count)
        except (ValueError, TypeError):
            content_count = None

    avg_likes = entry.get("avg_likes")
    if isinstance(avg_likes, str):
        try:
            avg_likes = int(avg_likes)
        except (ValueError, TypeError):
            avg_likes = None

    category_tags = entry.get("category_tags") or entry.get("tags") or []
    if isinstance(category_tags, str):
        category_tags = [t.strip() for t in category_tags.split(",") if t.strip()]

    bio = entry.get("bio") or entry.get("description") or entry.get("desc") or ""
    verified = entry.get("verified", False)
    if isinstance(verified, str):
        verified = verified.lower() in ("true", "1", "yes")

    confidence = entry.get("confidence_score")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = 0.5
    else:
        confidence = 0.5

    return _new_competitor(
        platform=platform or "unknown",
        account_name=account_name,
        account_id=str(account_id),
        account_url=account_url,
        avatar_url=entry.get("avatar_url"),
        follower_count=follower_count,
        content_count=content_count,
        avg_likes=avg_likes,
        category_tags=category_tags,
        bio=bio,
        verified=verified,
        discovery_source=entry.get("discovery_source", "local_db"),
        confidence_score=confidence,
    )


def _keyword_match(entry: dict, keyword: str) -> bool:
    """检查条目是否匹配关键词。"""
    keyword_lower = keyword.lower()
    searchable_fields = [
        entry.get("account_name", ""),
        entry.get("bio", ""),
        entry.get("account_id", ""),
        " ".join(str(t) for t in (entry.get("category_tags") or [])),
    ]
    for field in searchable_fields:
        if keyword_lower in str(field).lower():
            return True
    return False


def _discover_db_files(data_dir: Path) -> list[Path]:
    """发现本地数据库文件。"""
    files = []
    if not data_dir.is_dir():
        return files
    for fpath in sorted(data_dir.iterdir()):
        if not fpath.is_file():
            continue
        if fpath.suffix.lower() in (".json", ".csv"):
            files.append(fpath)
    return files


def search(keyword: str, platforms: list[str] | None = None,
           limit: int = 20, db_path: str | None = None) -> dict:
    """从本地数据库搜索竞品。"""
    # 确定数据目录
    if db_path:
        db_file = Path(db_path)
        if db_file.is_file():
            db_files = [db_file]
        elif db_file.is_dir():
            db_files = _discover_db_files(db_file)
        else:
            db_files = []
    else:
        env_dir = os.environ.get("YANG_LOCAL_DATA_DIR", "")
        if env_dir:
            data_dir = Path(env_dir) / "competitors"
        else:
            data_dir = Path(__file__).parent / "local-data"
        db_files = _discover_db_files(data_dir)

    if not db_files:
        print(f"[local_search] 未找到本地数据库文件", file=sys.stderr)
        return {
            "search_meta": {
                "keyword": keyword,
                "platforms_searched": platforms or list(SUPPORTED_PLATFORMS),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_found": 0,
                "errors": [{"platform": "local", "error": "未找到本地数据库文件"}],
                "mode": "local",
            },
            "competitors": [],
        }

    # 加载所有数据库
    all_entries = []
    for fpath in db_files:
        if fpath.suffix.lower() == ".json":
            entries = _load_json_db(fpath)
        elif fpath.suffix.lower() == ".csv":
            entries = _load_csv_db(fpath)
        else:
            continue
        print(f"[local_search] 从 {fpath.name} 加载 {len(entries)} 条记录", file=sys.stderr)
        all_entries.extend(entries)

    # 标准化 + 过滤
    competitors = []
    for entry in all_entries:
        comp = _normalize_entry(entry)
        if comp is None:
            continue

        # 平台过滤
        if platforms and comp["platform"] not in platforms:
            continue

        # 关键词过滤
        if keyword and not _keyword_match(comp, keyword):
            continue

        competitors.append(comp)

    # 去重（同 platform + account_id 只保留一条）
    seen = {}
    deduped = []
    for comp in competitors:
        key = (comp["platform"], comp["account_id"])
        if key in seen:
            existing = seen[key]
            if comp["follower_count"] is not None and existing["follower_count"] is None:
                existing["follower_count"] = comp["follower_count"]
            if comp["confidence_score"] > existing["confidence_score"]:
                existing["confidence_score"] = comp["confidence_score"]
                existing["discovery_source"] = comp["discovery_source"]
            continue
        seen[key] = comp
        deduped.append(comp)

    # 排序：粉丝数降序
    deduped.sort(key=lambda x: x.get("follower_count") or 0, reverse=True)

    # 限制数量
    deduped = deduped[:limit]

    return {
        "search_meta": {
            "keyword": keyword,
            "platforms_searched": platforms or list(SUPPORTED_PLATFORMS),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_found": len(deduped),
            "errors": [],
            "mode": "local",
        },
        "competitors": deduped,
    }


def main():
    parser = argparse.ArgumentParser(
        description="本地竞品搜索工具（零网络 · 零外部依赖）"
    )
    parser.add_argument("keyword", help="搜索关键词")
    parser.add_argument(
        "--platforms", default="douyin,bilibili,xiaohongshu,kuaishou",
        help="逗号分隔的目标平台列表（默认: douyin,bilibili,xiaohongshu,kuaishou）",
    )
    parser.add_argument(
        "--limit", type=int, default=20,
        help="最大返回数（默认: 20）",
    )
    parser.add_argument(
        "--db", default=None,
        help="本地数据库文件或目录路径（JSON/CSV）",
    )
    parser.add_argument(
        "--output", default=None,
        help="JSON 输出文件路径（不指定则输出到 stdout）",
    )

    args = parser.parse_args()
    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    result = search(args.keyword, platforms, args.limit, args.db)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    else:
        print(output)

    if not result["competitors"]:
        print(
            "[local_search] 未找到匹配的竞品——请检查本地数据库和关键词。\n"
            "详见 shared-protocols/local-fallback.md",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
