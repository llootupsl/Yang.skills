# 作者: 阿洋
"""本地对标分析管线（零网络 · 零外部依赖）。

从本地已有的视频文件、转录稿、评论数据运行对标分析管线，
跳过需要网络的下载和转录步骤，输出与 pipeline.py 兼容的结果。

设计原则
--------
- **零网络**：不依赖 yt-dlp / faster-whisper / Playwright。
- **零外部依赖**：仅使用 Python 标准库。
- **本地优先**：直接使用本地已有的数据文件，跳过缺失的步骤。
- **格式兼容**：输出文件与 pipeline.py 的输出结构一致。

用法
----
  python local_pipeline.py --video-dir ./videos/benchmark/abc123
  python local_pipeline.py --video-dir ./videos/benchmark/abc123 --skip-frames
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _load_json(path: str) -> dict | None:
    """安全加载 JSON 文件。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _check_file(path: str, label: str) -> bool:
    """检查文件是否存在并打印状态。"""
    if os.path.isfile(path):
        size = os.path.getsize(path)
        print(f"  ✓ {label}: {path} ({size:,} bytes)")
        return True
    else:
        print(f"  ✗ {label}: {path} (不存在)")
        return False


def _try_load_transcript(base_dir: str) -> dict | None:
    """尝试从多种格式加载转录数据。"""
    # 优先 JSON 格式
    transcript_json = os.path.join(base_dir, "transcript.json")
    data = _load_json(transcript_json)
    if data:
        return data

    # 尝试 Markdown 格式
    transcript_md = os.path.join(base_dir, "transcript.md")
    if os.path.isfile(transcript_md):
        try:
            with open(transcript_md, "r", encoding="utf-8") as f:
                text = f.read()
            return {
                "full_text": text,
                "segments": [],
                "source": "local_md",
            }
        except OSError:
            pass

    # 尝试纯文本格式
    transcript_txt = os.path.join(base_dir, "transcript.txt")
    if os.path.isfile(transcript_txt):
        try:
            with open(transcript_txt, "r", encoding="utf-8") as f:
                text = f.read()
            return {
                "full_text": text,
                "segments": [],
                "source": "local_txt",
            }
        except OSError:
            pass

    return None


def _try_load_comments(base_dir: str) -> list | None:
    """尝试加载评论数据。"""
    comments_json = os.path.join(base_dir, "comments.json")
    data = _load_json(comments_json)
    if data:
        return data.get("comments", data if isinstance(data, list) else [])

    comments_csv = os.path.join(base_dir, "comments.csv")
    if os.path.isfile(comments_csv):
        import csv
        comments = []
        try:
            with open(comments_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    comments.append({
                        "id": row.get("id", ""),
                        "text": row.get("text") or row.get("content") or "",
                        "likes": int(row.get("likes") or row.get("digg_count") or 0),
                        "time": row.get("time") or row.get("create_time") or "",
                    })
        except (OSError, ValueError):
            pass
        return comments if comments else None

    return None


def _generate_summary(base_dir: str, video_id: str,
                      has_video: bool, has_transcript: bool,
                      has_comments: bool, has_meta: bool,
                      transcript_data: dict | None,
                      comments_data: list | None,
                      meta_data: dict | None) -> dict:
    """生成本地管线摘要。"""
    summary = {
        "video_id": video_id,
        "mode": "local",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "available_data": {
            "video": has_video,
            "transcript": has_transcript,
            "comments": has_comments,
            "meta": has_meta,
        },
        "statistics": {},
    }

    if meta_data:
        summary["meta"] = meta_data
        summary["statistics"]["platform"] = meta_data.get("platform", "unknown")
        summary["statistics"]["title"] = meta_data.get("title", "")
        summary["statistics"]["duration_sec"] = meta_data.get("duration_sec")

    if transcript_data:
        full_text = transcript_data.get("full_text", "")
        segments = transcript_data.get("segments", [])
        summary["statistics"]["transcript_length"] = len(full_text)
        summary["statistics"]["segment_count"] = len(segments)
        summary["statistics"]["language"] = transcript_data.get("language", "unknown")

        if "script_dna" in transcript_data:
            summary["script_dna"] = transcript_data["script_dna"]

    if comments_data:
        summary["statistics"]["comment_count"] = len(comments_data)
        if comments_data:
            total_likes = sum(c.get("likes", 0) for c in comments_data if isinstance(c.get("likes"), int))
            summary["statistics"]["comment_total_likes"] = total_likes

    return summary


def run_local_pipeline(video_dir: str, skip_frames: bool = False) -> int:
    """运行本地对标分析管线。

    Returns:
        0 = 成功（至少有部分数据）
        1 = 失败（没有任何数据）
    """
    base_dir = os.path.abspath(video_dir)
    if not os.path.isdir(base_dir):
        print(f"[local_pipeline] 目录不存在: {base_dir}", file=sys.stderr)
        return 1

    video_id = os.path.basename(base_dir)
    print(f"[local_pipeline] 本地模式分析: {video_id}")
    print(f"[local_pipeline] 数据目录: {base_dir}")
    print()

    # 检查可用数据
    print("[1/4] 检查本地数据...")
    video_path = os.path.join(base_dir, "original.mp4")
    has_video = _check_file(video_path, "视频文件")

    meta_path = os.path.join(base_dir, "meta.json")
    has_meta = _check_file(meta_path, "元数据")

    frames_dir = os.path.join(base_dir, "frames")
    has_frames = os.path.isdir(frames_dir)
    if has_frames:
        frame_count = len([f for f in os.listdir(frames_dir)
                          if f.lower().endswith((".jpg", ".png", ".jpeg"))])
        print(f"  ✓ 帧目录: {frames_dir} ({frame_count} 帧)")
    else:
        print(f"  ✗ 帧目录: {frames_dir} (不存在)")

    print()
    print("[2/4] 加载转录数据...")
    transcript_data = _try_load_transcript(base_dir)
    has_transcript = transcript_data is not None
    if has_transcript:
        full_text = transcript_data.get("full_text", "")
        segments = transcript_data.get("segments", [])
        print(f"  ✓ 转录文本: {len(full_text)} 字, {len(segments)} 段")
    else:
        print("  ✗ 无转录数据（可手动创建 transcript.md 或 transcript.json）")

    print()
    print("[3/4] 加载评论数据...")
    comments_data = _try_load_comments(base_dir)
    has_comments = comments_data is not None
    if has_comments:
        print(f"  ✓ 评论: {len(comments_data)} 条")
    else:
        print("  ✗ 无评论数据（可手动创建 comments.json 或 comments.csv）")

    # 加载元数据
    meta_data = _load_json(meta_path) if has_meta else None

    # 帧提取（如果 opencv 可用且有视频但没帧）
    if not skip_frames and has_video and not has_frames:
        print()
        print("[4/4] 尝试帧提取...")
        try:
            import cv2
            print("  检测到 opencv，尝试提取帧...")
            os.makedirs(frames_dir, exist_ok=True)
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            interval = max(1, int(fps / 3))  # 3fps
            frame_idx = 0
            saved = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % interval == 0:
                    frame_path = os.path.join(frames_dir, f"frame_{saved:04d}.jpg")
                    cv2.imwrite(frame_path, frame)
                    saved += 1
                frame_idx += 1
            cap.release()
            print(f"  ✓ 提取 {saved} 帧到 {frames_dir}")
            has_frames = True
        except ImportError:
            print("  ✗ opencv 未安装，跳过帧提取")
        except Exception as e:
            print(f"  ✗ 帧提取失败: {e}")
    else:
        print()
        print("[4/4] 帧提取: 跳过" +
              ("（已有帧）" if has_frames else "（无视频或 --skip-frames）"))

    # 生成摘要
    print()
    print("=" * 50)
    print("本地管线完成")

    summary = _generate_summary(
        base_dir, video_id, has_video, has_transcript,
        has_comments, has_meta, transcript_data, comments_data, meta_data,
    )

    # 写入摘要文件
    summary_path = os.path.join(base_dir, "local_pipeline_summary.json")
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"摘要已写入: {summary_path}")
    except OSError as e:
        print(f"摘要写入失败: {e}", file=sys.stderr)

    # 打印统计
    stats = summary.get("statistics", {})
    if stats:
        print(f"  平台: {stats.get('platform', 'N/A')}")
        print(f"  标题: {stats.get('title', 'N/A')}")
        if "transcript_length" in stats:
            print(f"  转录: {stats['transcript_length']} 字 / {stats.get('segment_count', 0)} 段")
        if "comment_count" in stats:
            print(f"  评论: {stats['comment_count']} 条")

    # 检查是否有可用数据
    any_data = has_video or has_transcript or has_comments or has_meta
    if not any_data:
        print()
        print("[local_pipeline] 目录中没有任何可用数据。", file=sys.stderr)
        print("请确保目录中至少包含以下文件之一：", file=sys.stderr)
        print("  - original.mp4 (视频文件)", file=sys.stderr)
        print("  - transcript.json / transcript.md (转录稿)", file=sys.stderr)
        print("  - comments.json (评论数据)", file=sys.stderr)
        print("  - meta.json (元数据)", file=sys.stderr)
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="本地对标分析管线（零网络 · 零外部依赖）"
    )
    parser.add_argument(
        "--video-dir", required=True,
        help="视频数据目录路径（如 videos/benchmark/abc123/）",
    )
    parser.add_argument(
        "--skip-frames", action="store_true",
        help="跳过帧提取步骤",
    )

    args = parser.parse_args()
    exit_code = run_local_pipeline(args.video_dir, args.skip_frames)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
