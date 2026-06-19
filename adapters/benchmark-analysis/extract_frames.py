# 作者: 阿洋
"""Yang.skills v4 帧提取器 - 基于 OpenCV (零 ffmpeg 依赖)"""
import argparse
import json
import sys
import os


def _cv2_available():
    try:
        import cv2
        return True
    except ImportError:
        return False


def extract_frames(video_path: str, output_dir: str, saliency: bool = False, saliency_threshold: float = 0.5) -> int:
    try:
        import cv2
    except ImportError:
        print("请先安装 opencv-python: pip install opencv-python")
        sys.exit(1)

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频文件: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_count <= 0:
        frame_count = 999999

    safety_interval = max(1, int(fps * 0.5))
    prev_hist = None
    frame_idx = 0
    saved_count = 0
    last_saved_frame_idx = -safety_interval
    last_correlation = 1.0
    frame_metadata_list = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        should_save = False

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

        if prev_hist is not None:
            last_correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
            if last_correlation < 0.7:
                should_save = True

        if (frame_idx - last_saved_frame_idx) >= safety_interval:
            should_save = True

        if should_save:
            filename = f"frame_{saved_count:04d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)

            if saliency:
                import numpy as np
                timestamp_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

                try:
                    saliency_obj = cv2.saliency.StaticSaliencyFineGrained_create()
                    success, saliency_map = saliency_obj.computeSaliency(frame)

                    if success and saliency_map is not None:
                        heatmap = cv2.applyColorMap(saliency_map, cv2.COLORMAP_JET)
                        overlay = cv2.addWeighted(frame, 0.6, heatmap, 0.4, 0)
                        heat_path = os.path.join(output_dir, f"frame_{saved_count:04d}_heat.jpg")
                        cv2.imwrite(heat_path, overlay)

                        h, w = saliency_map.shape
                        y_coords, x_coords = np.mgrid[0:h, 0:w]
                        total = float(saliency_map.sum())
                        if total > 0:
                            focus_x = float((x_coords * saliency_map).sum()) / total / float(w)
                            focus_y = float((y_coords * saliency_map).sum()) / total / float(h)
                        else:
                            focus_x = 0.5
                            focus_y = 0.5

                        threshold_val = int(saliency_threshold * 255)
                        binary = (saliency_map > threshold_val).astype(np.uint8)
                        heat_coverage = float(binary.sum()) / float(h * w)

                        num_labels, _ = cv2.connectedComponents(binary)
                        num_hotspots = int(num_labels) - 1

                        frame_metadata_list.append({
                            "frame_id": f"frame_{saved_count:04d}",
                            "timestamp_sec": round(timestamp_sec, 2),
                            "scene_change_score": round(last_correlation, 4),
                            "saliency": {
                                "focus_x": round(focus_x, 4),
                                "focus_y": round(focus_y, 4),
                                "heat_coverage": round(heat_coverage, 4),
                                "num_hotspots": num_hotspots
                            }
                        })
                except Exception:
                    pass

            saved_count += 1
            last_saved_frame_idx = frame_idx

        prev_hist = hist
        frame_idx += 1

        if frame_idx >= frame_count:
            break

    if saliency and frame_metadata_list:
        metadata = {
            "video_path": video_path,
            "video_fps": round(fps, 2),
            "total_frames_extracted": saved_count,
            "extraction_method": "scene_detection",
            "scene_threshold": 0.7,
            "saliency_enabled": True,
            "frames": frame_metadata_list
        }
        metadata_path = os.path.join(output_dir, "frames_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    cap.release()
    return saved_count


def main():
    parser = argparse.ArgumentParser(description="帧提取器 (零 ffmpeg)")
    parser.add_argument("video_path", type=str, help="视频文件路径")
    parser.add_argument("--output", type=str, required=True, help="输出目录")
    parser.add_argument("--saliency", action="store_true", default=False, help="启用注意力热力图生成")
    parser.add_argument("--saliency-threshold", type=float, default=0.5, help="显著性阈值 (0-1)")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    try:
        count = extract_frames(args.video_path, args.output, saliency=args.saliency, saliency_threshold=args.saliency_threshold)
        print(f"提取完成: {count} 帧 → {args.output}")
    except Exception as e:
        print(f"提取失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()