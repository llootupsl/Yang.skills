# 作者: 阿洋
"""Yang.skills v4 视频下载器 - 基于 yt-dlp

作者: 阿洋

引入策略：优先使用 vendor 版本的 yt-dlp 源码，回退到 pip install 版本。
详见 adapters/benchmark-analysis/yt_dlp_vendor/README.md
"""
import argparse
import sys
import os

SUPPORTED_PLATFORMS = ["douyin", "bilibili", "xiaohongshu", "youtube", "kuaishou"]


def _import_yt_dlp():
    """优先使用 vendor 版本的 yt-dlp，回退到 pip install 版本。

    作者: 阿洋

    加载顺序：
    1. vendor 目录下的 yt-dlp 源码（用户手动引入的完整源码）
    2. pip install 的 yt-dlp 包
    3. 两者均不可用则报错退出

    返回 yt_dlp 模块对象。
    """
    try:
        # 优先从 vendor 目录导入
        _vendor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt_dlp_vendor")
        if _vendor_dir not in sys.path:
            sys.path.insert(0, _vendor_dir)
        from yt_dlp_vendor import yt_dlp_loader
        return yt_dlp_loader.get_yt_dlp()
    except ImportError:
        pass
    except Exception:
        # vendor 加载任何异常都回退到 pip 版本，保证不破坏现有功能
        pass
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        print("请先安装 yt-dlp: pip install yt-dlp")
        print("或将 yt-dlp 完整源码放入 adapters/benchmark-analysis/yt_dlp_vendor/yt_dlp/")
        sys.exit(1)


def _write_meta(info: dict, output: str, platform: str) -> None:
    """把视频元数据写入 meta.json，并做时效（freshness）判定。"""
    import json as _json
    from datetime import datetime, timezone

    # 复用通用时效工具（容错导入，缺失则降级为不判定）
    fresh = None
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
        _root = os.path.dirname(os.path.dirname(_here))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        from adapters._common import freshness as fresh
    except Exception:
        fresh = None

    upload_date = info.get("upload_date")  # YYYYMMDD
    timestamp = info.get("timestamp")
    publish_iso = None
    if timestamp:
        try:
            publish_iso = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
        except Exception:
            publish_iso = None
    if publish_iso is None and upload_date and len(str(upload_date)) == 8:
        try:
            d = str(upload_date)
            publish_iso = datetime(int(d[:4]), int(d[4:6]), int(d[6:8]), tzinfo=timezone.utc).isoformat()
        except Exception:
            publish_iso = None

    meta = {
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "uploader_id": info.get("uploader_id") or info.get("channel_id"),
        "platform": platform,
        "duration_sec": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "upload_date": upload_date,
        "publish_date": publish_iso or upload_date,
        "webpage_url": info.get("webpage_url"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    if fresh is not None:
        label = fresh.freshness_label(meta["publish_date"])
        meta["_freshness"] = label
        meta["_days_since"] = fresh.days_since(meta["publish_date"])
        if label == "stale":
            print(f"⚠️ 时效警告: 该视频发布于 {meta['publish_date']}，距今 "
                  f"{meta['_days_since']:.0f} 天，已超过新鲜上限——旧时间内容的规律可能已失效，"
                  f"建议优先选用近期视频做对标。")
        elif label == "aging":
            print(f"提示: 该视频距今 {meta['_days_since']:.0f} 天，属偏旧区间，分析结论需标注时效。")
        elif label == "unknown":
            print("提示: 无法解析该视频发布时间，无法判定时效，请人工核对是否为近期内容。")

    out_dir = os.path.dirname(output) or "."
    meta_path = os.path.join(out_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        _json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"元数据: {meta_path}（发布 {meta.get('publish_date')} · 时效 {meta.get('_freshness', 'n/a')}）")


def _detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "douyin.com" in url_lower:
        return "douyin"
    if "bilibili.com" in url_lower or "b23.tv" in url_lower:
        return "bilibili"
    if "xiaohongshu.com" in url_lower or "xhslink.com" in url_lower:
        return "xiaohongshu"
    if "kuaishou.com" in url_lower or "kwai" in url_lower or "chenzhongtech" in url_lower:
        return "kuaishou"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    return "unknown"


def download_video(url: str, output: str) -> str:
    yt_dlp = _import_yt_dlp()

    platform = _detect_platform(url)
    if platform not in SUPPORTED_PLATFORMS:
        print("不支持该平台，请尝试使用浏览器手动下载")
        sys.exit(1)

    output_dir = os.path.dirname(output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    output_template = os.path.splitext(output)[0] + ".%(ext)s"

    ydl_opts = {
        "outtmpl": output_template,
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": False,
        "extract_flat": False,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as e:
            print(f"下载失败: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"下载失败: {e}")
            sys.exit(1)

    # 采集元数据 + 时效判定（写 sidecar meta.json，供 §1 视频信息 + 时效锁使用）
    try:
        _write_meta(info, output, platform)
    except Exception as e:
        print(f"元数据写入跳过: {e}")

    actual_path = os.path.splitext(output)[0] + ".mp4"
    if os.path.exists(actual_path):
        if actual_path != output:
            if os.path.exists(output):
                os.remove(output)
            os.rename(actual_path, output)

    if not os.path.exists(output):
        candidates = []
        base = os.path.splitext(output)[0]
        for ext in [".mp4", ".mkv", ".webm", ".flv", ".mov"]:
            candidate = base + ext
            if os.path.exists(candidate):
                candidates.append(candidate)
        if candidates:
            for candidate in candidates:
                if candidate != output:
                    if os.path.exists(output):
                        os.remove(output)
                    os.rename(candidate, output)
                    break
        else:
            print("下载完成但找不到输出文件")
            sys.exit(1)

    return output


def main():
    parser = argparse.ArgumentParser(description="视频下载器")
    parser.add_argument("url", type=str, help="视频 URL")
    parser.add_argument("--output", type=str, required=True, help="输出路径")
    args = parser.parse_args()

    try:
        path = download_video(args.url, args.output)
        print(f"下载完成: {path}")
    except Exception as e:
        print(f"下载失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()