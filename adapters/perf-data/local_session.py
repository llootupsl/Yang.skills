# 作者: 阿洋
"""本地抖音数据会话（零网络 · 零外部依赖）。

从本地 CSV/JSON 文件读取抖音视频数据，输出与 douyin-session/crawler.py 的
fetch_all() 完全一致的数据结构，供 yang-retro / yang-learn-from 在离线环境下使用。

设计原则
--------
- **零网络**：不依赖 Playwright / requests。
- **零外部依赖**：仅使用 Python 标准库。
- **格式兼容**：输出结构与 crawler.py 的 fetch_all() 一致。
- **多格式支持**：支持抖音创作者中心导出的 CSV 和自定义 JSON 格式。

用法
----
  python local_session.py --data-dir ./local-data/douyin
  python local_session.py --csv ./local-data/douyin/videos.csv
  python local_session.py --json ./local-data/douyin/videos.json --aweme-id 7xxx
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _normalize_video_from_csv(row: dict) -> dict:
    """从 CSV 行标准化视频数据。"""
    aweme_id = row.get("aweme_id") or row.get("视频ID") or row.get("id") or ""
    desc = row.get("desc") or row.get("标题") or row.get("description") or row.get("视频标题") or ""
    create_time_str = row.get("create_time") or row.get("发布时间") or row.get("发布日期") or ""
    duration_str = row.get("duration_ms") or row.get("时长") or row.get("时长(ms)") or "0"
    play_count_str = row.get("play_count") or row.get("播放量") or row.get("播放") or "0"
    digg_count_str = row.get("digg_count") or row.get("点赞数") or row.get("点赞") or "0"
    comment_count_str = row.get("comment_count") or row.get("评论数") or row.get("评论") or "0"
    share_count_str = row.get("share_count") or row.get("分享数") or row.get("分享") or "0"
    collect_count_str = row.get("collect_count") or row.get("收藏数") or row.get("收藏") or "0"

    # 解析时间
    create_time = 0
    if create_time_str:
        try:
            # 尝试 Unix 时间戳
            create_time = int(float(create_time_str))
        except (ValueError, TypeError):
            # 尝试日期字符串
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
                try:
                    dt = datetime.strptime(str(create_time_str).strip(), fmt)
                    create_time = int(dt.timestamp())
                    break
                except ValueError:
                    continue

    return {
        "aweme_id": str(aweme_id).strip(),
        "desc": desc.strip(),
        "create_time": create_time,
        "duration_ms": _safe_int(duration_str),
        "play_count": _safe_int(play_count_str),
        "digg_count": _safe_int(digg_count_str),
        "comment_count": _safe_int(comment_count_str),
        "share_count": _safe_int(share_count_str),
        "collect_count": _safe_int(collect_count_str),
        "raw": row,
    }


def _normalize_video_from_json(v: dict) -> dict:
    """从 JSON 标准化视频数据（与 crawler.py 的 _normalize_video 一致）。"""
    aweme_id = v.get("aweme_id") or v.get("item_id") or v.get("id") or ""
    stats = v.get("statistics") or v.get("stats") or {}
    video_info = v.get("video") or {}
    return {
        "aweme_id": str(aweme_id),
        "desc": v.get("desc") or v.get("title") or "",
        "create_time": v.get("create_time") or v.get("createTime") or 0,
        "duration_ms": video_info.get("duration") or v.get("duration") or 0,
        "play_count": stats.get("play_count") or v.get("play_count") or 0,
        "digg_count": stats.get("digg_count") or v.get("digg_count") or 0,
        "comment_count": stats.get("comment_count") or v.get("comment_count") or 0,
        "share_count": stats.get("share_count") or v.get("share_count") or 0,
        "collect_count": stats.get("collect_count") or v.get("collect_count") or 0,
        "raw": v,
    }


def _normalize_comment(c: dict) -> dict:
    """标准化评论数据。"""
    user = c.get("user") or {}
    return {
        "cid": str(c.get("cid") or c.get("comment_id") or c.get("id") or ""),
        "aweme_id": str(c.get("aweme_id") or c.get("item_id") or ""),
        "text": c.get("text") or c.get("content") or "",
        "digg_count": c.get("digg_count") or c.get("like_count") or 0,
        "reply_comment_total": c.get("reply_comment_total") or c.get("reply_count") or 0,
        "create_time": c.get("create_time") or 0,
        "user_name": user.get("nickname") or user.get("name") or c.get("user_name") or "",
        "ip_label": c.get("ip_label") or c.get("ip_location") or "",
    }


def _safe_int(s) -> int:
    """安全转换为整数。"""
    if s is None:
        return 0
    try:
        # 处理带万/亿的中文数字
        s_str = str(s).strip().replace(",", "").replace(" ", "")
        if "亿" in s_str:
            return int(float(s_str.replace("亿", "")) * 100000000)
        if "万" in s_str:
            return int(float(s_str.replace("万", "")) * 10000)
        if "w" in s_str.lower():
            return int(float(s_str.lower().replace("w", "")) * 10000)
        return int(float(s_str))
    except (ValueError, TypeError):
        return 0


def _load_csv_data(csv_path: str) -> list[dict]:
    """从 CSV 文件加载视频列表。"""
    videos = []
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                video = _normalize_video_from_csv(row)
                if video["aweme_id"]:
                    videos.append(video)
    except OSError as e:
        print(f"[local_session] 无法读取 CSV: {e}", file=sys.stderr)
    return videos


def _load_json_data(json_path: str) -> list[dict]:
    """从 JSON 文件加载视频列表。"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[local_session] 无法读取 JSON: {e}", file=sys.stderr)
        return []

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ("videos", "items", "data", "list"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        else:
            items = [data]
    else:
        return []

    videos = []
    for v in items:
        if not isinstance(v, dict):
            continue
        video = _normalize_video_from_json(v)
        if video["aweme_id"]:
            videos.append(video)
    return videos


def _load_comments_from_dir(data_dir: str, aweme_id: str | None = None) -> list[dict]:
    """从目录中加载评论数据。"""
    comments = []
    comments_dir = os.path.join(data_dir, "comments")
    if not os.path.isdir(comments_dir):
        # 尝试直接在数据目录下找
        comments_dir = data_dir

    for fname in os.listdir(comments_dir):
        if not fname.endswith(".json"):
            continue
        # 如果指定了 aweme_id，只加载对应文件
        if aweme_id and aweme_id not in fname:
            continue
        fpath = os.path.join(comments_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(data, list):
            raw_comments = data
        elif isinstance(data, dict):
            for key in ("comments", "comment_list", "data"):
                if key in data and isinstance(data[key], list):
                    raw_comments = data[key]
                    break
            else:
                raw_comments = [data]
        else:
            continue

        for c in raw_comments:
            if isinstance(c, dict):
                comments.append(_normalize_comment(c))

    return comments


def _discover_data_files(data_dir: str) -> list[str]:
    """发现数据目录中的视频数据文件。"""
    files = []
    if not os.path.isdir(data_dir):
        return files
    for fname in sorted(os.listdir(data_dir)):
        fpath = os.path.join(data_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if fname.lower().endswith((".json", ".csv")):
            files.append(fpath)
    return files


def fetch_all_local(data_dir: str | None = None,
                    csv_path: str | None = None,
                    json_path: str | None = None,
                    aweme_id: str | None = None) -> dict:
    """从本地文件读取抖音数据，输出与 crawler.py fetch_all() 一致的结构。"""
    videos = []
    comments = []
    detail = {"captured": []}

    # 加载视频列表
    if csv_path:
        videos = _load_csv_data(csv_path)
        print(f"[local_session] 从 CSV 加载 {len(videos)} 条视频", file=sys.stderr)
    elif json_path:
        videos = _load_json_data(json_path)
        print(f"[local_session] 从 JSON 加载 {len(videos)} 条视频", file=sys.stderr)
    elif data_dir:
        data_files = _discover_data_files(data_dir)
        for fpath in data_files:
            if fpath.endswith(".csv"):
                videos.extend(_load_csv_data(fpath))
            elif fpath.endswith(".json"):
                # 区分视频数据和评论数据
                fname = os.path.basename(fpath).lower()
                if "comment" in fname:
                    comments.extend(_load_comments_from_dir(data_dir, aweme_id))
                else:
                    videos.extend(_load_json_data(fpath))
        print(f"[local_session] 从目录加载 {len(videos)} 条视频", file=sys.stderr)
    else:
        env_dir = os.environ.get("YANG_LOCAL_DATA_DIR", "")
        if env_dir:
            local_dir = os.path.join(env_dir, "douyin")
        else:
            local_dir = os.path.join(os.path.dirname(__file__), "local-data")
        data_files = _discover_data_files(local_dir)
        for fpath in data_files:
            if fpath.endswith(".csv"):
                videos.extend(_load_csv_data(fpath))
            elif fpath.endswith(".json"):
                videos.extend(_load_json_data(fpath))
        print(f"[local_session] 从默认目录加载 {len(videos)} 条视频", file=sys.stderr)

    # 去重
    seen = set()
    dedup_videos = []
    for v in videos:
        vid = v["aweme_id"]
        if vid in seen:
            continue
        seen.add(vid)
        dedup_videos.append(v)
    videos = dedup_videos

    # 查找目标视频
    video = None
    if aweme_id:
        video = next((v for v in videos if v["aweme_id"] == aweme_id), None)
        if not video:
            print(f"[local_session] 未找到 aweme_id={aweme_id}，使用最小元数据", file=sys.stderr)
            video = _normalize_video_from_json({"aweme_id": aweme_id})
    elif videos:
        video = videos[0]

    # 加载评论
    if data_dir and not comments:
        comments = _load_comments_from_dir(data_dir, aweme_id)

    # 按 aweme_id 过滤评论
    if aweme_id and comments:
        comments = [c for c in comments if not c.get("aweme_id") or str(c["aweme_id"]) == str(aweme_id)]

    # 排序评论
    comments.sort(key=lambda x: x.get("digg_count", 0), reverse=True)

    return {
        "video": video,
        "detail": detail,
        "comments": comments,
        "_meta": {
            "mode": "local",
            "total_videos": len(videos),
            "total_comments": len(comments),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="本地抖音数据会话（零网络 · 零外部依赖）"
    )
    parser.add_argument(
        "--data-dir", default=None,
        help="本地数据目录路径",
    )
    parser.add_argument(
        "--csv", default=None,
        help="CSV 文件路径（抖音创作者中心导出格式）",
    )
    parser.add_argument(
        "--json", default=None,
        help="JSON 文件路径",
    )
    parser.add_argument(
        "--aweme-id", default=None,
        help="目标视频 aweme_id（不指定则返回全部视频列表）",
    )
    parser.add_argument(
        "--output", default=None,
        help="JSON 输出文件路径（不指定则输出到 stdout）",
    )

    args = parser.parse_args()

    if not any([args.data_dir, args.csv, args.json]):
        # 使用默认目录
        pass

    result = fetch_all_local(
        data_dir=args.data_dir,
        csv_path=args.csv,
        json_path=args.json,
        aweme_id=args.aweme_id,
    )

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
        print(f"[local_session] 已写入 {args.output}", file=sys.stderr)
    else:
        print(payload)

    if not result.get("video") and not result.get("comments"):
        print(
            "[local_session] 未找到任何数据——请检查数据目录和文件格式。\n"
            "详见 shared-protocols/local-fallback.md",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
