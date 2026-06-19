# 作者: 阿洋
"""Yang.skills v4 口播转文字器 - 基于 faster-whisper"""
import argparse
import json
import sys
import os
import hashlib


def _make_video_id(video_path: str) -> str:
    abs_path = os.path.abspath(video_path)
    return hashlib.md5(abs_path.encode("utf-8")).hexdigest()[:12]


def compute_script_dna(full_text, segments) -> dict:
    try:
        import jieba
        JIEBA_AVAILABLE = True
    except ImportError:
        JIEBA_AVAILABLE = False

    import re
    word_count = len(full_text.replace(' ', ''))
    sentences = re.split(r'[。！？!?\n]+', full_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)
    avg_sentence_length = word_count / max(sentence_count, 1)

    total_duration = segments[-1]['end'] - segments[0]['start'] if segments else 1
    total_duration = max(total_duration, 1)
    overall_wpm = word_count / (total_duration / 60)

    first_15_cutoff = min(15, total_duration / 2)
    last_15_start = max(0, total_duration - 15)

    first_15_words = sum(len(s['text'].replace(' ', '')) for s in segments if s['start'] < first_15_cutoff)
    first_15s_wpm = first_15_words / (min(first_15_cutoff, total_duration) / 60)

    mid_words = sum(len(s['text'].replace(' ', '')) for s in segments if first_15_cutoff <= s['start'] < last_15_start)
    mid_duration = max(last_15_start - first_15_cutoff, 0.1)
    mid_wpm = mid_words / (mid_duration / 60)

    last_15_words = sum(len(s['text'].replace(' ', '')) for s in segments if s['start'] >= last_15_start)
    last_15_duration = max(total_duration - last_15_start, 0.1)
    last_15s_wpm = last_15_words / (last_15_duration / 60)

    total_sentences = len(sentences)
    declarative = sum(1 for s in sentences if s.endswith('。'))
    interrogative = sum(1 for s in sentences if s.endswith('？') or s.endswith('?'))
    exclamatory = sum(1 for s in sentences if s.endswith('！') or s.endswith('!'))
    imperative = total_sentences - declarative - interrogative - exclamatory

    catchphrases = []
    if JIEBA_AVAILABLE:
        words = list(jieba.cut(full_text))
        from collections import Counter
        bigrams = Counter()
        trigrams = Counter()
        for i in range(len(words)-1):
            if len(words[i]) >= 2 and len(words[i+1]) >= 1:
                bigrams[words[i] + words[i+1]] += 1
            if i < len(words)-2 and len(words[i]) >= 2:
                trigrams[words[i] + words[i+1] + words[i+2]] += 1
        for phrase, count in bigrams.most_common(20):
            if count >= 3:
                category = 'filler' if any(w in phrase for w in ['就是','然后','那个','这个','是吧']) else 'emphasis'
                catchphrases.append({"phrase": phrase, "count": count, "category": category})
        for phrase, count in trigrams.most_common(10):
            if count >= 3:
                catchphrases.append({"phrase": phrase, "count": count, "category": "signature"})

    punctuation = re.findall(r'[，。！？、；：""''（）\n]', full_text)
    key_points = max(1, len(punctuation) // 3)
    points_per_minute = key_points / (total_duration / 60)
    redundancy_score = min(1.0, catchphrases[0]['count'] / 50 if catchphrases else 0)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": round(avg_sentence_length, 1),
        "speech_rate": {
            "overall_wpm": round(overall_wpm, 1),
            "first_15s_wpm": round(first_15s_wpm, 1),
            "mid_wpm": round(mid_wpm, 1),
            "last_15s_wpm": round(last_15s_wpm, 1)
        },
        "sentence_patterns": {
            "declarative_pct": round(declarative / max(total_sentences, 1), 3),
            "interrogative_pct": round(interrogative / max(total_sentences, 1), 3),
            "exclamatory_pct": round(exclamatory / max(total_sentences, 1), 3),
            "imperative_pct": round(imperative / max(total_sentences, 1), 3)
        },
        "catchphrase_fingerprint": catchphrases[:15],
        "information_density": {
            "key_points_total": key_points,
            "points_per_minute": round(points_per_minute, 2),
            "redundancy_score": round(redundancy_score, 3)
        },
        "emotion_triggers": [],
        "rhythm_signature": {
            "pace_pattern": "steady",
            "pause_pattern": "natural",
            "emphasis_pattern": "pause_before"
        }
    }


def transcribe_video(video_path: str, output_path: str, dna: bool = False, translate: bool = False) -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("请先安装 faster-whisper: pip install faster-whisper")
        sys.exit(1)

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    video_id = _make_video_id(video_path)

    model = WhisperModel("medium", device="cpu", compute_type="int8")

    segments_result, info = model.transcribe(
        video_path,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    if info.language not in ("zh", "en", "ja", "ko", "fr", "de", "es", "pt", "it"):
        print(f"警告: 检测到非主流语种 ({info.language})，转录结果可能不准确")

    segments = []
    full_text_parts = []

    for segment in segments_result:
        segments.append({
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
            "confidence": round(segment.avg_logprob, 4) if segment.avg_logprob is not None else 0.0,
        })
        full_text_parts.append(segment.text.strip())

    full_text = "".join(full_text_parts) if info.language == "zh" else " ".join(full_text_parts)

    result = {
        "video_id": video_id,
        "language": info.language,
        "segments": segments,
        "full_text": full_text,
    }

    # 转译桥接：对外语对标视频，用 whisper 的 translate 任务额外产出英文轨，
    # 作为"原文→中文"的中间桥（whisper 仅能译到英文；最终中文转译由 yang-benchmark
    # 在 SKILL 层用模型对 full_text / full_text_en 做中文意译并对齐时间轴）。
    if translate and info.language != "zh":
        try:
            tr_segments_result, _ = model.transcribe(
                video_path,
                task="translate",
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )
            tr_segments = []
            tr_parts = []
            for seg in tr_segments_result:
                tr_segments.append({
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text.strip(),
                })
                tr_parts.append(seg.text.strip())
            result["segments_en"] = tr_segments
            result["full_text_en"] = " ".join(tr_parts)
            result["translation_note"] = (
                "full_text_en 为 whisper translate 产出的英文桥接译文；"
                "最终中文转译需在 SKILL 层基于 full_text(原文)+full_text_en 做意译并按时间轴对齐。"
            )
        except Exception as e:
            result["translation_error"] = str(e)
    elif translate and info.language == "zh":
        result["translation_note"] = "源语言为中文，无需转译。"

    if dna:
        result["script_dna"] = compute_script_dna(full_text, segments)

    return result


def main():
    parser = argparse.ArgumentParser(description="口播转文字器")
    parser.add_argument("video_path", type=str, help="视频文件路径")
    parser.add_argument("--output", type=str, required=True, help="输出 JSON 路径")
    parser.add_argument("--dna", action="store_true", default=False, help="启用话术DNA分析")
    parser.add_argument("--translate", action="store_true", default=False, help="对外语视频额外产出英文桥接译文（转译）")
    args = parser.parse_args()

    try:
        result = transcribe_video(args.video_path, args.output, dna=args.dna, translate=args.translate)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        extra = " + 转译" if (args.translate and result.get("language") != "zh") else ""
        print(f"转录完成{extra}: {len(result.get('segments', []))} 段 → {args.output}")
    except Exception as e:
        print(f"转录失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()