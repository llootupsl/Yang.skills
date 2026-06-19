#!/usr/bin/env python3
# 作者: 阿洋
"""将转录文本导入到 benchmark.md 格式"""
import sys
import json
import argparse
from datetime import datetime

def import_to_benchmark(transcript_path, metadata_path, output_path):
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = f.read()

    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    word_count = len(transcript)

    entry = f"""
### {metadata.get('title', 'Unknown')}
- 链接: {metadata.get('url', 'N/A')}
- 发布时间: {metadata.get('publish_date', 'N/A')}
- 播放量: {metadata.get('views', 'N/A')}
- 转录字数: {word_count}
- 导入时间: {datetime.now().isoformat()}

#### 转录文本
{transcript[:500]}{'...' if len(transcript) > 500 else ''}
"""
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write(entry)

    print(f"Imported to {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--transcript', required=True)
    parser.add_argument('--metadata', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    import_to_benchmark(args.transcript, args.metadata, args.output)