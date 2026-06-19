<!-- 作者: 阿洋 -->
# 对标账号自动转录适配器

## 功能
从对标账号的视频中自动提取脚本：下载音频 → 语音转文字 → 保存转录文本

## 使用方法

```bash
bash run.sh --url <video-url> --output samples/<account>/<video-id>/
```

## 支持引擎

| 引擎 | 命令参数 | 优势 |
|------|---------|------|
| Whisper | `--engine whisper` | 默认引擎，通用性好 |
| SenseVoice | `--engine sensevoice` | 中文精度高 + 情感识别 |
| FunASR | `--engine funasr` | 全链路：VAD+ASR+标点+说话人分离 |
| FireRedASR | `--engine fireredasr` | 中文精度 #1 |
| GLM-ASR | `--engine glmasr` | 粤语支持好 |

## 输出
- `transcript.md`: 完整转录文本
- `metadata.json`: 视频元数据
- `emotion_labels.json`: 情绪标签（SenseVoice 引擎时额外输出）

## 依赖
- Python 3.10+
- yt-dlp (视频下载)
- 至少一个 ASR 引擎