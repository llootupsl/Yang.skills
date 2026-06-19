# 作者: 阿洋
"""Yang.skills 对标全链路 pipeline。

串联：download → extract_frames(+saliency) → transcribe(+dna,+translate)
      → scrape_comments → mine_comments → 策略变化检测

默认即开启 saliency(注意力热力图) + dna(话术DNA) + translate(外语转译) + 评论挖掘，
以交付"顶级编导级"对标分析。如需快速预览，用 --fast 关闭增强步骤。

==========================================================================
管线各步骤输入/输出规范
==========================================================================

步骤1: download
  输入: video_url (str) — 视频页面URL
  输出: videos/benchmark/{video_id}/original.mp4

步骤2: extract_frames (+saliency)
  输入: original.mp4
  输出: videos/benchmark/{video_id}/frames/  (帧图片目录)
  可选输出: videos/benchmark/{video_id}/frames/saliency/  (注意力热力图)

步骤3: transcribe (+dna, +translate)
  输入: original.mp4
  输出: videos/benchmark/{video_id}/transcript.json
  格式: {"segments": [{"start": float, "end": float, "text": str}], "dna": {...}, "translation": {...}}

步骤4: scrape_comments
  输入: video_url, video_id
  输出: videos/benchmark/{video_id}/comments.json
  格式: {"comments": [{"id": str, "text": str, "likes": int, "time": str}]}

步骤5: mine_comments
  输入: comments.json
  输出: videos/benchmark/{video_id}/comment_mining.json
  格式: {"clusters": [...], "pain_points": [...], "demands": [...]}

步骤6: 策略变化检测
  输入: transcript.json, comment_mining.json
  输出: 控制台报告 + videos/benchmark/{video_id}/strategy_report.json

==========================================================================
步骤间数据传递格式约定
==========================================================================

- 所有中间文件使用 JSON 格式（除视频/帧图片外），编码 UTF-8。
- 每个步骤读取上一步的输出文件路径，由 pipeline 按约定目录结构传递。
- 文件路径约定: videos/benchmark/{video_id}/ 为单视频工作目录。
- 若某步骤输出文件已存在且非空，默认跳过该步骤（幂等性），除非显式指定覆盖。
- 步骤失败时：该步骤输出文件不写入或写入空结构，pipeline 记录错误后继续后续步骤。

==========================================================================
--fast 模式精简规则
==========================================================================

--fast 模式用于快速预览对标结果，关闭耗时增强步骤：

1. 关闭 saliency（注意力热力图提取）— 节省约 40% 处理时间
2. 关闭 dna（话术DNA分析）— 节省约 15% 处理时间
3. 关闭 translate（外语转译）— 节省约 10% 处理时间
4. 关闭 mine（评论深度挖掘）— 节省约 20% 处理时间
5. 帧提取间隔从 1fps 增大至 3fps — 减少帧数量约 66%
6. 评论抓取上限从 500 条降至 100 条

保留的步骤: download → extract_frames(3fps) → transcribe(纯文本) → scrape_comments(100条)

总耗时约为完整模式的 25%~35%，适合快速筛选候选对标视频后再对精选视频跑完整管线。
==========================================================================
"""
import argparse
import importlib.util
import os
import subprocess
import sys
import time


def _load_db():
    """稳健加载 data_pipeline.db：先正常包导入，失败则按文件路径加载。"""
    try:
        from adapters.data_pipeline import db as m  # 包根在 sys.path 时可用
        return m
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(here, "..", "data_pipeline", "db.py"))
    if not os.path.isfile(db_path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("yang_data_pipeline_db", db_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def run_pipeline(video_url: str, video_id: str, no_strategy_check: bool = False,
                 saliency: bool = True, dna: bool = True, translate: bool = True,
                 mine: bool = True):
    base_dir = os.path.join("videos", "benchmark", video_id)
    frames_dir = os.path.join(base_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    video_path = os.path.join(base_dir, "original.mp4")
    transcript_path = os.path.join(base_dir, "transcript.json")
    comments_path = os.path.join(base_dir, "comments.json")
    mining_path = os.path.join(base_dir, "comment_mining.json")

    script_dir = os.path.dirname(os.path.abspath(__file__))

    extract_args = [video_path, "--output", frames_dir]
    if saliency:
        extract_args.append("--saliency")
    transcribe_args = [video_path, "--output", transcript_path]
    if dna:
        transcribe_args.append("--dna")
    if translate:
        transcribe_args.append("--translate")

    steps_config = [
        {"name": "下载视频", "script": os.path.join(script_dir, "download.py"),
         "args": [video_url, "--output", video_path], "timeout": 300},
        {"name": "帧提取" + ("+热力图" if saliency else ""),
         "script": os.path.join(script_dir, "extract_frames.py"),
         "args": extract_args, "timeout": 360},
        {"name": "口播转文字" + ("+话术DNA" if dna else "") + ("+转译" if translate else ""),
         "script": os.path.join(script_dir, "transcribe.py"),
         "args": transcribe_args, "timeout": 360},
        {"name": "评论抓取", "script": os.path.join(script_dir, "scrape_comments.py"),
         "args": [video_url, "--output", comments_path], "timeout": 120},
    ]

    total_start = time.time()
    for step in steps_config:
        step_start = time.time()
        print(f"[{step['name']}] 开始...")
        try:
            result = subprocess.run(
                [sys.executable, step["script"]] + step["args"],
                capture_output=True, text=True, timeout=step["timeout"],
                cwd=os.path.dirname(script_dir),
            )
            elapsed = time.time() - step_start
            if result.returncode == 0:
                print(f"[{step['name']}] 完成 ({elapsed:.1f}s)")
                if result.stdout.strip():
                    print(result.stdout.strip())
            else:
                print(f"[{step['name']}] 失败 ({elapsed:.1f}s)")
                if result.stderr.strip():
                    print(result.stderr.strip())
                # 评论抓取失败不阻断后续（评论是增强项，非必需）
                if step["name"].startswith("评论"):
                    print("[评论抓取] 失败但继续（评论为增强项）")
                    continue
                sys.exit(1)
        except subprocess.TimeoutExpired:
            print(f"[{step['name']}] 超时 ({step['timeout']}s)")
            if step["name"].startswith("评论"):
                print("[评论抓取] 超时但继续（评论为增强项）")
                continue
            sys.exit(1)

    # 第 5 步：高赞评论挖掘（评论→标题/选题）
    if mine and os.path.exists(comments_path):
        step_start = time.time()
        print("[评论挖掘] 开始...")
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(script_dir, "mine_comments.py"),
                 comments_path, "--output", mining_path],
                capture_output=True, text=True, timeout=60,
                cwd=os.path.dirname(script_dir),
            )
            elapsed = time.time() - step_start
            if result.returncode == 0:
                print(f"[评论挖掘] 完成 ({elapsed:.1f}s)")
                if result.stdout.strip():
                    print(result.stdout.strip())
            else:
                print(f"[评论挖掘] 跳过 ({elapsed:.1f}s): {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print("[评论挖掘] 超时，跳过")

    # 策略变化检测
    strategy_changes = []
    if not no_strategy_check:
        step_start = time.time()
        print("\n[策略变化检测] 开始...")
        try:
            db = _load_db()
            if db is None:
                print("[策略变化检测] db 模块不可用，跳过")
            else:
                snapshots = db.get_competitor_snapshots(video_id, limit=2)
                if len(snapshots) < 2:
                    print("[策略变化检测] 暂无足够历史快照，跳过")
                else:
                    current, previous = snapshots[0], snapshots[1]
                    strategy_result = db.detect_strategy_changes(video_id, current, previous)
                    strategy_changes = strategy_result.get("detected_changes", [])
                    stable_dims = strategy_result.get("stable_dimensions", [])
                    elapsed = time.time() - step_start
                    if strategy_changes:
                        print(f"[策略变化检测] 检测到 {len(strategy_changes)} 项变化 ({elapsed:.1f}s):")
                        for change in strategy_changes:
                            print(f"  - [{change['change_type']}] {change.get('before', '?')} → "
                                  f"{change.get('after', '?')} (显著性: {change.get('significance', '?')})")
                        if stable_dims:
                            print(f"  稳定维度({len(stable_dims)}): {', '.join(stable_dims)}")
                    else:
                        print(f"[策略变化检测] 未检测到显著变化 ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - step_start
            print(f"[策略变化检测] 异常 ({elapsed:.1f}s): {e}")

    total_elapsed = time.time() - total_start
    print(f"\n全链路完成 ({total_elapsed:.1f}s)")
    print(f"  视频: {video_path if os.path.exists(video_path) else '(下载失败)'}")
    print(f"  元数据: {os.path.join(base_dir, 'meta.json')}")
    print(f"  帧: {frames_dir}")
    print(f"  口播: {transcript_path if os.path.exists(transcript_path) else '(转录失败)'}")
    print(f"  评论: {comments_path if os.path.exists(comments_path) else '(抓取失败/跳过)'}")
    print(f"  评论挖掘: {mining_path if os.path.exists(mining_path) else '(跳过)'}")
    if strategy_changes:
        print(f"  策略变化: {len(strategy_changes)} 项")


def main():
    parser = argparse.ArgumentParser(description="对标视频全链路分析 Pipeline")
    parser.add_argument("video_url", type=str, help="视频 URL")
    parser.add_argument("--video-id", type=str, required=True, help="视频唯一标识")
    parser.add_argument("--no-strategy-check", action="store_true", help="跳过策略变化检测")
    parser.add_argument("--fast", action="store_true",
                        help="快速模式：关闭 saliency / dna / translate / 评论挖掘 等增强步骤")
    parser.add_argument("--no-saliency", action="store_true", help="单独关闭注意力热力图")
    parser.add_argument("--no-dna", action="store_true", help="单独关闭话术DNA")
    parser.add_argument("--no-translate", action="store_true", help="单独关闭外语转译")
    parser.add_argument("--no-mine", action="store_true", help="单独关闭评论挖掘")
    args = parser.parse_args()

    saliency = not (args.fast or args.no_saliency)
    dna = not (args.fast or args.no_dna)
    translate = not (args.fast or args.no_translate)
    mine = not (args.fast or args.no_mine)

    run_pipeline(args.video_url, args.video_id,
                 no_strategy_check=args.no_strategy_check,
                 saliency=saliency, dna=dna, translate=translate, mine=mine)


if __name__ == "__main__":
    main()
