#!/usr/bin/env python3
# 作者: 阿洋
"""
graphrag_index.py — GraphRAG knowledge index builder and searcher for Yang.skills v4.

Builds a graph-based knowledge index from three knowledge bases (ansir, xuehui,
shekong), supports entity extraction, relationship extraction, community detection,
and multi-mode search (local, global, drift).

Usage:
    python tools/graphrag_index.py --init
    python tools/graphrag_index.py --rebuild
    python tools/graphrag_index.py --search "钩子技巧" --mode local
    python tools/graphrag_index.py --search "商业定位" --mode global

Dependencies: graphrag (optional — falls back to keyword search)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
STATE_FILE = PROJECT_DIR / ".yang-state.json"

KNOWLEDGE_PATHS = {
    "ansir": PROJECT_DIR / "knowledge" / "ansir" / "SKILL.md",
    "xuehui": PROJECT_DIR / "knowledge" / "xuehui" / "SKILL.md",
    "shekong": PROJECT_DIR / "knowledge" / "shekong" / "SKILL.md",
}

INDEX_DIR = PROJECT_DIR / "knowledge" / "index"

GRAPHRAG_AVAILABLE = False
try:
    import graphrag  # noqa: F401

    GRAPHRAG_AVAILABLE = True
except ImportError:
    pass


def _load_json(path: Path) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _save_json(path: Path, data: dict) -> bool:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except OSError as e:
        print(f"error: 无法写入 {path}: {e}", file=sys.stderr)
        return False


def _update_yang_state(updates: dict) -> None:
    state = _load_json(STATE_FILE) or {}
    state.update(updates)
    _save_json(STATE_FILE, state)


def _load_knowledge_texts() -> dict[str, str]:
    """Load all three knowledge base texts. Returns {name: text} dict."""
    texts = {}
    for name, path in KNOWLEDGE_PATHS.items():
        if not path.is_file():
            print(f"warn: 知识文件缺失: {path}", file=sys.stderr)
            texts[name] = ""
            continue
        try:
            texts[name] = path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"warn: 无法读取 {path}: {e}", file=sys.stderr)
            texts[name] = ""
    return texts


def init_index():
    """Build GraphRAG index from three knowledge bases.

    Pipeline: Entity Extraction → Relationship Extraction →
    Community Detection → Summarization.

    If graphrag is not installed, falls back to building a lightweight
    keyword-based index stored as JSON.
    """
    kb_texts = _load_knowledge_texts()

    missing = [name for name, text in kb_texts.items() if not text]
    if missing:
        print(
            f"warn: 以下知识库缺失，将跳过: {', '.join(missing)}",
            file=sys.stderr,
        )

    present = {k: v for k, v in kb_texts.items() if v}
    if not present:
        print("error: 所有知识库均缺失，无法构建索引", file=sys.stderr)
        sys.exit(1)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    if GRAPHRAG_AVAILABLE:
        _init_graphrag_full(present)
    else:
        print(
            "graphrag 未安装，使用轻量关键词索引。安装 graphrag 以获得完整功能: pip install graphrag",
            file=sys.stderr,
        )
        _init_lightweight(present)


def _init_graphrag_full(kb_texts: dict[str, str]):
    """Run full GraphRAG pipeline."""
    print("启动 GraphRAG 全量索引构建...", file=sys.stderr)
    print(
        f"知识库: {', '.join(kb_texts.keys())} | "
        f"总字符数: {sum(len(t) for t in kb_texts.values())}",
        file=sys.stderr,
    )

    input_dir = INDEX_DIR / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    for name, text in kb_texts.items():
        input_path = input_dir / f"{name}.txt"
        input_path.write_text(text, encoding="utf-8")

    settings_yml = INDEX_DIR / "settings.yaml"
    if not settings_yml.exists():
        _write_graphrag_settings(settings_yml)

    try:
        import subprocess

        print("步骤 1/4: 实体提取...", file=sys.stderr)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "graphrag",
                "index",
                "--root",
                str(INDEX_DIR),
                "--resume",
                "create_base_extracted_entities",
            ],
            cwd=str(PROJECT_DIR),
            check=False,
            capture_output=False,
        )

        print("步骤 2/4: 关系提取...", file=sys.stderr)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "graphrag",
                "index",
                "--root",
                str(INDEX_DIR),
                "--resume",
                "create_final_entities",
            ],
            cwd=str(PROJECT_DIR),
            check=False,
            capture_output=False,
        )

        print("步骤 3/4: 社区检测...", file=sys.stderr)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "graphrag",
                "index",
                "--root",
                str(INDEX_DIR),
                "--resume",
                "create_final_communities",
            ],
            cwd=str(PROJECT_DIR),
            check=False,
            capture_output=False,
        )

        print("步骤 4/4: 社区摘要生成...", file=sys.stderr)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "graphrag",
                "index",
                "--root",
                str(INDEX_DIR),
                "--resume",
                "create_final_text_units",
            ],
            cwd=str(PROJECT_DIR),
            check=False,
            capture_output=False,
        )
    except Exception as e:
        print(f"error: GraphRAG 索引构建失败: {e}", file=sys.stderr)
        print("info: 回退至轻量关键词索引", file=sys.stderr)
        _init_lightweight(kb_texts)
        return

    stats = _count_graphrag_artifacts()
    print(f"索引构建完成: {stats}", file=sys.stderr)

    _update_yang_state(
        {
            "knowledge_index_version": "v4-graphrag",
            "knowledge_index_exists": True,
            "knowledge_index_updated": datetime.now(timezone.utc).isoformat(),
            "knowledge_index_stats": stats,
        }
    )


def _count_graphrag_artifacts() -> dict:
    """Count entities, relationships, communities from parquet outputs."""
    stats = {"entities": 0, "relationships": 0, "communities": 0, "text_units": 0}
    try:
        import pandas as pd
    except ImportError:
        print("info: pandas 未安装，无法统计 GraphRAG 产物数量", file=sys.stderr)
        return {}
    try:

        for artifact, key in [
            ("entities.parquet", "entities"),
            ("relationships.parquet", "relationships"),
            ("communities.parquet", "communities"),
            ("text_units.parquet", "text_units"),
        ]:
            path = INDEX_DIR / "output" / artifact
            if path.is_file():
                df = pd.read_parquet(path)
                stats[key] = len(df)
    except Exception:
        pass
    return stats


def _write_graphrag_settings(settings_path: Path):
    """Write a minimal GraphRAG settings.yaml."""
    settings = {
        "encoding_model": "cl100k_base",
        "llm": {
            "type": "openai_chat",
            "model": "gpt-4o",
            "api_key": "${GRAPHRAG_API_KEY}",
            "max_tokens": 4000,
            "temperature": 0.0,
        },
        "embeddings": {
            "llm": {
                "type": "openai_embedding",
                "model": "text-embedding-3-small",
                "api_key": "${GRAPHRAG_API_KEY}",
            }
        },
        "chunks": {
            "size": 1200,
            "overlap": 100,
        },
        "input": {
            "type": "text",
            "base_dir": "input",
        },
        "skip_workflows": [],
    }
    settings_text = (
        "encoding_model: cl100k_base\n"
        "llm:\n"
        "  type: openai_chat\n"
        "  model: gpt-4o\n"
        "  api_key: ${GRAPHRAG_API_KEY}\n"
        "  max_tokens: 4000\n"
        "  temperature: 0.0\n"
        "embeddings:\n"
        "  llm:\n"
        "    type: openai_embedding\n"
        "    model: text-embedding-3-small\n"
        "    api_key: ${GRAPHRAG_API_KEY}\n"
        "chunks:\n"
        "  size: 1200\n"
        "  overlap: 100\n"
        "input:\n"
        "  type: text\n"
        "  base_dir: input\n"
        "skip_workflows: []\n"
    )
    settings_path.write_text(settings_text, encoding="utf-8")


def _init_lightweight(kb_texts: dict[str, str]):
    """Build a lightweight keyword-based index stored as JSON."""
    print("构建轻量关键词索引...", file=sys.stderr)

    index = {
        "version": "v4-lightweight",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sources": list(kb_texts.keys()),
        "total_chars": sum(len(t) for t in kb_texts.values()),
        "entries": [],
    }

    chunk_size = 500
    chunk_overlap = 100

    for source, text in kb_texts.items():
        lines = text.split("\n")
        paragraphs = []
        current = []

        for line in lines:
            stripped = line.strip()
            if stripped:
                current.append(stripped)
            elif current:
                paragraphs.append("\n".join(current))
                current = []

        if current:
            paragraphs.append("\n".join(current))

        for para in paragraphs:
            if len(para) < 30:
                continue

            keywords = _extract_keywords(para)
            heading = _extract_heading(para)

            if len(para) <= chunk_size:
                index["entries"].append(
                    {
                        "source": source,
                        "heading": heading,
                        "text": para[:2000],
                        "keywords": keywords,
                        "char_count": len(para),
                    }
                )
            else:
                words = list(para)
                pos = 0
                while pos < len(words):
                    chunk = "".join(words[pos : pos + chunk_size])
                    if len(chunk) < 30:
                        break
                    chunk_keywords = _extract_keywords(chunk)
                    index["entries"].append(
                        {
                            "source": source,
                            "heading": heading,
                            "text": chunk[:2000],
                            "keywords": chunk_keywords,
                            "char_count": len(chunk),
                        }
                    )
                    pos += chunk_size - chunk_overlap

    index["entity_count"] = len(index["entries"])

    index_path = INDEX_DIR / "lightweight_index.json"
    _save_json(index_path, index)

    stats = {
        "chunks": len(index["entries"]),
        "sources": len(kb_texts),
        "total_chars": index["total_chars"],
    }

    print(f"轻量索引构建完成: {stats}", file=sys.stderr)

    _update_yang_state(
        {
            "knowledge_index_version": "v4-lightweight",
            "knowledge_index_exists": True,
            "knowledge_index_updated": datetime.now(timezone.utc).isoformat(),
            "knowledge_index_stats": stats,
        }
    )


def _extract_keywords(text: str, top_n: int = 8) -> list[str]:
    """Extract key Chinese phrases as keywords from a text chunk."""
    phrases = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    freq: dict[str, int] = {}
    for phrase in phrases:
        if len(phrase) >= 2:
            freq[phrase] = freq.get(phrase, 0) + 1

    stop_words = {
        "一个", "可以", "这个", "那个", "我们", "他们", "自己", "什么",
        "没有", "不是", "就是", "还是", "不过", "但是", "因为", "所以",
        "如果", "虽然", "而且", "然后", "之后", "之前", "以及", "以及",
        "需要", "通过", "进行", "使用", "对于", "关于", "这些", "那些",
        "已经", "或者", "其中", "所有", "能够", "一种", "比较", "不要",
        "大家", "一下", "如何", "怎么", "知道", "可能", "应该",
    }

    filtered = [(p, c) for p, c in freq.items() if p not in stop_words]
    filtered.sort(key=lambda x: -x[1])
    return [p for p, _ in filtered[:top_n]]


def _extract_heading(text: str) -> str:
    """Extract the nearest heading from text."""
    heading_match = re.search(r"^#{1,4}\s+(.+)$", text, re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()
    bracket_match = re.search(r"^##?\s*(.+?)(?:##|\n|$)", text)
    if bracket_match:
        return bracket_match.group(1).strip()[:60]
    return ""


def rebuild_index():
    """Delete old index and rebuild."""
    if INDEX_DIR.exists():
        print(f"删除旧索引: {INDEX_DIR}", file=sys.stderr)
        shutil.rmtree(INDEX_DIR)
    init_index()


def search(query: str, mode: str = "local"):
    """Search the knowledge graph.

    Args:
        query: Search query string.
        mode: Search mode — "local" (entity/neighborhood),
              "global" (community summaries), "drift" (drift search).

    If graphrag index exists (parquet files), use graphrag query.
    Otherwise, fall back to lightweight keyword search over knowledge texts.
    """
    if not query or not query.strip():
        print(json.dumps({"error": "查询为空", "results": []}, ensure_ascii=False))
        return

    query = query.strip()

    if GRAPHRAG_AVAILABLE and _has_graphrag_index():
        _search_graphrag(query, mode)
    else:
        _search_lightweight(query, mode)


def _has_graphrag_index() -> bool:
    """Check if GraphRAG parquet files exist."""
    output_dir = INDEX_DIR / "output"
    required = ["entities.parquet", "communities.parquet"]
    return all((output_dir / f).is_file() for f in required)


def _search_graphrag(query: str, mode: str):
    """Execute GraphRAG search via CLI."""
    try:
        import subprocess

        cmd = [
            sys.executable,
            "-m",
            "graphrag",
            "query",
            "--root",
            str(INDEX_DIR),
            "--method",
            mode,
            "--query",
            query,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(PROJECT_DIR))

        if result.returncode != 0:
            print(
                f"warn: GraphRAG 查询失败，回退至轻量搜索: {result.stderr}",
                file=sys.stderr,
            )
            _search_lightweight(query, mode)
            return

        try:
            parsed = json.loads(result.stdout)
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(
                json.dumps(
                    {"mode": mode, "query": query, "response": result.stdout.strip()},
                    ensure_ascii=False,
                    indent=2,
                )
            )
    except Exception as e:
        print(f"warn: GraphRAG 查询异常: {e}，回退至轻量搜索", file=sys.stderr)
        _search_lightweight(query, mode)


def _search_lightweight(query: str, mode: str):
    """Fallback keyword search in knowledge texts and lightweight index."""
    index_path = INDEX_DIR / "lightweight_index.json"

    results = []

    if index_path.is_file():
        index_data = _load_json(index_path)
        if index_data:
            entries = index_data.get("entries", [])
            results = _score_entries(query, entries)

    if not results:
        kb_texts = _load_knowledge_texts()
        for source, text in kb_texts.items():
            if not text:
                continue
            for match in _find_matches_in_text(query, text, source):
                results.append(match)

    if not results:
        results.append(
            {
                "source": "none",
                "heading": "无匹配",
                "text": f"未找到与 '{query}' 相关的内容",
                "relevance": 0.0,
            }
        )

    output = {
        "mode": mode,
        "query": query,
        "engine": "lightweight",
        "total_matches": len(results),
        "results": results[:10],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _score_entries(query: str, entries: list[dict]) -> list[dict]:
    """Score entries by keyword relevance."""
    query_keywords = _extract_keywords(query, top_n=5)
    query_chars = set(query)

    scored = []
    for entry in entries:
        text = entry.get("text", "")
        entry_keywords = entry.get("keywords", [])

        keyword_matches = sum(1 for kw in query_keywords if kw in text)
        char_overlap = len(query_chars & set(text)) / max(len(query_chars), 1)
        kw_direct = sum(1 for kw in query_keywords if kw in entry_keywords)

        score = keyword_matches * 2.0 + kw_direct * 1.5 + char_overlap * 0.5
        if score > 0:
            scored.append(
                {
                    "source": entry.get("source", ""),
                    "heading": entry.get("heading", ""),
                    "text": text[:300] + ("..." if len(text) > 300 else ""),
                    "relevance": round(score, 3),
                }
            )

    scored.sort(key=lambda x: -x["relevance"])
    return scored


def _find_matches_in_text(query: str, text: str, source: str) -> list[dict]:
    """Find paragraphs in text that match the query."""
    matches = []
    query_lower = query.lower()

    paragraphs = re.split(r"\n{2,}", text)
    for para in paragraphs:
        para = para.strip()
        if not para or len(para) < 20:
            continue
        if query_lower in para.lower() or any(
            char in para for char in query if "\u4e00" <= char <= "\u9fff"
        ):
            heading = _extract_heading(para)
            relevance = _calc_relevance(query, para)
            matches.append(
                {
                    "source": source,
                    "heading": heading,
                    "text": para[:300] + ("..." if len(para) > 300 else ""),
                    "relevance": relevance,
                }
            )

    matches.sort(key=lambda x: -x["relevance"])
    return matches[:10]


def _calc_relevance(query: str, text: str) -> float:
    """Calculate simple relevance score between query and text."""
    query_chars = set(query)
    text_chars = set(text)
    if not query_chars:
        return 0.0
    ratio = len(query_chars & text_chars) / len(query_chars)
    return round(min(ratio * 2.0, 1.0), 3)


def main():
    parser = argparse.ArgumentParser(
        description="GraphRAG Knowledge Index for Yang.skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--init", action="store_true", help="构建知识图谱索引")
    parser.add_argument("--rebuild", action="store_true", help="删除旧索引并重建")
    parser.add_argument("--search", type=str, help="搜索查询字符串")
    parser.add_argument(
        "--mode",
        type=str,
        default="local",
        choices=["local", "global", "drift"],
        help="搜索模式: local（实体邻域）| global（社区摘要）| drift（漂移搜索）",
    )

    args = parser.parse_args()

    if args.init:
        init_index()
    elif args.rebuild:
        rebuild_index()
    elif args.search:
        search(args.search, args.mode)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()