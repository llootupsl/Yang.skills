#!/bin/bash
# 作者: 阿洋
# 对标账号视频自动转录
# Usage: bash run.sh --url <video-url> [--engine <whisper|sensevoice|funasr|fireredasr|glmasr>] --output <dir>

set -e

URL=""
ENGINE="whisper"
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --url) URL="$2"; shift 2 ;;
    --engine) ENGINE="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ -z "$URL" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: bash run.sh --url <video-url> --output <output-dir> [--engine <engine>]"
  exit 1
fi

mkdir -p "$OUTPUT"

echo "[1/3] Downloading video..."
yt-dlp -f "bestaudio[ext=m4a]/bestaudio" -o "$OUTPUT/audio.%(ext)s" "$URL"

AUDIO_FILE=$(ls "$OUTPUT"/audio.* 2>/dev/null | head -1)

echo "[2/3] Transcribing with $ENGINE..."

case $ENGINE in
  whisper)
    python scripts/whisper_transcribe.py --input "$AUDIO_FILE" --output "$OUTPUT/transcript.md"
    ;;
  sensevoice)
    python scripts/sensevoice_transcribe.py --input "$AUDIO_FILE" --output "$OUTPUT/transcript.md" --emotion "$OUTPUT/emotion_labels.json"
    ;;
  funasr)
    python scripts/funasr_transcribe.py --input "$AUDIO_FILE" --output "$OUTPUT/transcript.md"
    ;;
  fireredasr)
    python scripts/fireredasr_transcribe.py --input "$AUDIO_FILE" --output "$OUTPUT/transcript.md"
    ;;
  glmasr)
    python scripts/glmasr_transcribe.py --input "$AUDIO_FILE" --output "$OUTPUT/transcript.md"
    ;;
  *)
    echo "Unknown engine: $ENGINE"
    exit 1
    ;;
esac

echo "[3/3] Saving metadata..."
python scripts/extract_metadata.py --url "$URL" --output "$OUTPUT/metadata.json"

echo "Done! Output: $OUTPUT/"