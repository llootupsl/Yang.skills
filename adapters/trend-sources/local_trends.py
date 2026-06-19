# 作者: 阿洋
"""本地热点数据读取器（零网络 · 零外部依赖）。

从本地 .md / .json / .csv 文件读取热点数据，输出与 fetch_trends.py 完全一致的
JSON 结构，供 yang-trends / yang-seed 在离线环境下使用。

设计原则
--------
- **零网络**：不发起任何 HTTP 请求，不依赖 requests / httpx 等。
- **零外部依赖**：仅使用 Python 标准库（json / re / csv / pathlib）。
- **格式兼容**：输出结构与 fetch_trends.py 的 collect() 完全一致，上层调用方无需修改。
- **多格式支持**：自动识别 Markdown 表格、Markdown 列表、JSON 行、CSV 四种格式。
- **优雅降级**：单个文件解析失败只跳过该文件，不影响其他源。

本地数据文件命名约定
------------------
文件名（不含扩展名）即数据源名称，映射关系：

| 文件名            | 对应在线源        | source 标签        |
|-------------------|-------------------|--------------------|
| weibo-hot.md      | 微博热搜          | trend:weibo-hot    |
| zhihu-hot.md      | 知乎热榜          | trend:zhihu-hot    |
| bilibili.md       | B站热门           | trend:bilibili-popular |
| baidu-hot.md      | 百度热搜          | trend:baidu-hot    |
| douyin-hot.md     | 抖音热点          | trend:douyin-hot   |
| toutiao-hot.md    | 头条热榜          | trend:toutiao-hot  |
| ithome.md         | IT之家            | trend:ithome       |
| 36kr.md           | 36氪              | trend:36kr         |
| aihot.md          | AI 垂直资讯       | trend:aihot        |

用法
----
  python local_trends.py --sources weibo,zhihu --out trends.json
  python local_trends.py --data-dir ./local-data/trends --limit 50
  python local_trends.py                            # 全部源、默认目录
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ----------------------------- 文件名→源映射 -----------------------------

SOURCE_MAP = {
    "weibo-hot": "trend:weibo-hot",
    "zhihu-hot": "trend:zhihu-hot",
    "bilibili": "trend:bilibili-popular",
    "baidu-hot": "trend:baidu-hot",
    "douyin-hot": "trend:douyin-hot",
    "toutiao-hot": "trend:toutiao-hot",
    "ithome": "trend:ithome",
    "36kr": "trend:36kr",
    "aihot": "trend:aihot",
}

# 扩展名→解析器 映射
PARSER_MAP = {
    ".md": "markdown",
    ".json": "json",
    ".csv": "csv",
    ".jsonl": "jsonl",
    ".txt": "text",
}

# ----------------------------- 公共工具 -----------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cid(title: str) -> str:
    return hashlib.sha256(("trend|" + (title or "").strip()).encode("utf-8")).hexdigest()[:12]


def _candidate(title, source, url, hotness=None, rank=None, publish=None) -> dict:
    return {
        "id": _cid(title),
        "title": (title or "").strip(),
        "source": source,
        "url": url or "",
        "hotness": hotness,
        "rank": rank,
        "publish_date": publish,
        "snapshot_at": _now_iso(),
        "_freshness": "unknown",
        "_checked_at": _now_iso(),
    }


def _resolve_source_tag(stem: str) -> str:
    """从文件名解析 source 标签。"""
    lower = stem.lower()
    if lower in SOURCE_MAP:
        return SOURCE_MAP[lower]
    # 尝试前缀匹配
    for key, tag in SOURCE_MAP.items():
        if lower.startswith(key):
            return tag
    # 兜底：用文件名构造
    return f"trend:local-{lower}"


# ----------------------------- Markdown 解析 -----------------------------

def _parse_markdown(text: str, source_tag: str, limit: int) -> list:
    """解析 Markdown 格式的热点数据。

    支持三种格式：
    1. 表格：| 排名 | 标题 | 热度 | URL |
    2. 有序列表：1. 标题 (热度: 12345)
    3. 无序列表：- 标题
    """
    items = []

    # 尝试表格格式
    table_items = _parse_md_table(text, source_tag, limit)
    if table_items:
        return table_items[:limit]

    # 尝试有序/无序列表格式
    list_items = _parse_md_list(text, source_tag, limit)
    if list_items:
        return list_items[:limit]

    return items


def _parse_md_table(text: str, source_tag: str, limit: int) -> list:
    """解析 Markdown 表格。"""
    items = []
    lines = text.strip().split("\n")
    header_found = False
    col_map = {}

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue

        cells = [c.strip() for c in stripped.split("|")]
        # 去掉首尾空元素
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]

        if not cells:
            continue

        # 检测表头
        if not header_found:
            # 跳过分隔行（---|---|---）
            if all(re.match(r"^[-:]+$", c) for c in cells):
                continue
            # 这是表头行
            for i, cell in enumerate(cells):
                lower = cell.lower()
                if "标题" in lower or "title" in lower or "话题" in lower or "关键词" in lower:
                    col_map["title"] = i
                elif "热度" in lower or "hot" in lower or "热度值" in lower or "指数" in lower:
                    col_map["hotness"] = i
                elif "排名" in lower or "rank" in lower or "序号" in lower or "#" in lower:
                    col_map["rank"] = i
                elif "url" in lower or "链接" in lower or "地址" in lower:
                    col_map["url"] = i
            header_found = True
            continue

        # 跳过分隔行
        if all(re.match(r"^[-:]+$", c) for c in cells):
            continue

        # 数据行
        if len(cells) <= max(col_map.values(), default=-1):
            continue

        title = cells[col_map["title"]].strip() if "title" in col_map else ""
        if not title:
            # 如果没有识别到表头，尝试第一列作为标题
            title = cells[0].strip() if cells else ""

        if not title:
            continue

        hotness = None
        if "hotness" in col_map and col_map["hotness"] < len(cells):
            hotness = _parse_hotness(cells[col_map["hotness"]])

        rank = None
        if "rank" in col_map and col_map["rank"] < len(cells):
            rank = _parse_int(cells[col_map["rank"]])
        else:
            rank = len(items) + 1

        url = ""
        if "url" in col_map and col_map["url"] < len(cells):
            url = cells[col_map["url"]].strip()

        items.append(_candidate(title, source_tag, url, hotness=hotness, rank=rank))
        if len(items) >= limit:
            break

    return items


def _parse_md_list(text: str, source_tag: str, limit: int) -> list:
    """解析 Markdown 列表格式。

    支持格式：
    - 1. 标题文字
    - 1. 标题文字 (热度: 12345)
    - 1. [标题文字](URL)
    - - 标题文字
    """
    items = []
    rank = 0

    for line in text.strip().split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # 有序列表: 1. xxx  或  1、xxx
        m = re.match(r"^\d+[.、]\s*(.+)$", stripped)
        if not m:
            # 无序列表: - xxx 或 * xxx
            m = re.match(r"^[-*]\s+(.+)$", stripped)
        if not m:
            continue

        content = m.group(1).strip()
        if not content:
            continue

        rank += 1

        # 提取链接 [text](url)
        url = ""
        link_m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", content)
        if link_m:
            title = link_m.group(1).strip()
            url = link_m.group(2).strip()
            content = title
        else:
            # 去掉末尾的链接
            content = re.sub(r"\s*https?://\S+$", "", content).strip()
            url_m = re.search(r"(https?://\S+)", line)
            if url_m:
                url = url_m.group(1).strip()

        # 提取热度
        hotness = None
        hot_m = re.search(r"[（(]热度[:：]\s*([\d,.万亿]+)[)）]", content)
        if hot_m:
            hotness = _parse_hotness(hot_m.group(1))
            content = re.sub(r"\s*[（(]热度[:：]\s*[\d,.万亿]+[)）]", "", content)
        else:
            hot_m2 = re.search(r"(\d[\d,.]*[万亿]?)\s*(热度|热度值|指数)", content)
            if hot_m2:
                hotness = _parse_hotness(hot_m2.group(1))
                content = re.sub(r"\s*" + re.escape(hot_m2.group(0)), "", content)

        # 清理标题
        title = content.strip().rstrip("。.!！")
        if not title:
            continue

        items.append(_candidate(title, source_tag, url, hotness=hotness, rank=rank))
        if len(items) >= limit:
            break

    return items


# ----------------------------- JSON 解析 -----------------------------

def _parse_json(text: str, source_tag: str, limit: int) -> list:
    """解析 JSON 格式。支持数组或对象。"""
    items = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return items

    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        # 尝试常见字段名
        for key in ("trends", "items", "data", "list", "results"):
            if key in data and isinstance(data[key], list):
                entries = data[key]
                break
        else:
            entries = [data]
    else:
        return items

    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        title = entry.get("title") or entry.get("word") or entry.get("name") or ""
        if not title:
            continue
        url = entry.get("url") or entry.get("link") or entry.get("href") or ""
        hotness = entry.get("hotness") or entry.get("hot_value") or entry.get("heat") or entry.get("num")
        if isinstance(hotness, str):
            hotness = _parse_hotness(hotness)
        rank = entry.get("rank") or (i + 1)
        publish = entry.get("publish_date") or entry.get("pubDate") or None
        items.append(_candidate(title, source_tag, url, hotness=hotness, rank=rank, publish=publish))
        if len(items) >= limit:
            break

    return items


# ----------------------------- JSONL 解析 -----------------------------

def _parse_jsonl(text: str, source_tag: str, limit: int) -> list:
    """解析 JSON Lines 格式（每行一个 JSON 对象）。"""
    items = []
    for i, line in enumerate(text.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        title = entry.get("title") or entry.get("word") or entry.get("name") or ""
        if not title:
            continue
        url = entry.get("url") or entry.get("link") or ""
        hotness = entry.get("hotness") or entry.get("hot_value") or entry.get("heat")
        if isinstance(hotness, str):
            hotness = _parse_hotness(hotness)
        rank = entry.get("rank") or (i + 1)
        items.append(_candidate(title, source_tag, url, hotness=hotness, rank=rank))
        if len(items) >= limit:
            break
    return items


# ----------------------------- CSV 解析 -----------------------------

def _parse_csv(text: str, source_tag: str, limit: int) -> list:
    """解析 CSV 格式。自动检测分隔符和编码。"""
    items = []
    reader = csv.DictReader(io.StringIO(text))
    col_map = {}
    for field in reader.fieldnames or []:
        lower = field.lower().strip()
        if lower in ("标题", "title", "话题", "关键词", "word"):
            col_map["title"] = field
        elif lower in ("热度", "hotness", "hot_value", "heat", "热度值", "指数"):
            col_map["hotness"] = field
        elif lower in ("排名", "rank", "序号", "#"):
            col_map["rank"] = field
        elif lower in ("url", "链接", "地址", "link", "href"):
            col_map["url"] = field

    if "title" not in col_map and reader.fieldnames:
        # 默认第一列为标题
        col_map["title"] = reader.fieldnames[0]

    for i, row in enumerate(reader):
        title = row.get(col_map.get("title", ""), "").strip()
        if not title:
            continue
        url = row.get(col_map.get("url", ""), "").strip()
        hotness_str = row.get(col_map.get("hotness", ""), "").strip()
        hotness = _parse_hotness(hotness_str) if hotness_str else None
        rank_str = row.get(col_map.get("rank", ""), "").strip()
        rank = _parse_int(rank_str) if rank_str else (i + 1)
        items.append(_candidate(title, source_tag, url, hotness=hotness, rank=rank))
        if len(items) >= limit:
            break

    return items


# ----------------------------- 纯文本解析 -----------------------------

def _parse_text(text: str, source_tag: str, limit: int) -> list:
    """解析纯文本格式（每行一条热点）。"""
    items = []
    for i, line in enumerate(text.strip().split("\n")):
        stripped = line.strip()
        if not stripped:
            continue
        # 去掉行首序号
        cleaned = re.sub(r"^\d+[.、)\]]\s*", "", stripped).strip()
        if not cleaned:
            continue
        items.append(_candidate(cleaned, source_tag, "", rank=i + 1))
        if len(items) >= limit:
            break
    return items


# ----------------------------- 辅助函数 -----------------------------

def _parse_hotness(s: str) -> int | None:
    """解析热度字符串为整数。"""
    if not s:
        return None
    s = s.strip().replace(",", "").replace(" ", "")
    try:
        if "亿" in s:
            return int(float(s.replace("亿", "")) * 100000000)
        if "万" in s:
            return int(float(s.replace("万", "")) * 10000)
        if "w" in s.lower():
            return int(float(s.lower().replace("w", "")) * 10000)
        if "k" in s.lower():
            return int(float(s.lower().replace("k", "")) * 1000)
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _parse_int(s: str) -> int | None:
    """安全解析整数。"""
    if not s:
        return None
    try:
        return int(s.strip())
    except (ValueError, TypeError):
        return None


# ----------------------------- 文件发现与解析 -----------------------------

def _discover_files(data_dir: Path, sources: list[str] | None = None) -> list[tuple[Path, str]]:
    """发现本地数据文件，返回 [(path, source_tag), ...]。"""
    results = []
    if not data_dir.is_dir():
        return results

    for fpath in sorted(data_dir.iterdir()):
        if not fpath.is_file():
            continue
        if fpath.suffix.lower() not in PARSER_MAP:
            continue

        stem = fpath.stem.lower()
        source_tag = _resolve_source_tag(fpath.stem)

        # 如果指定了 sources 过滤，检查是否匹配
        if sources:
            matched = False
            for src in sources:
                src_lower = src.lower()
                # 匹配文件名前缀
                if stem.startswith(src_lower) or src_lower.startswith(stem):
                    matched = True
                    break
                # 匹配 source tag
                if src_lower in source_tag:
                    matched = True
                    break
            if not matched:
                continue

        results.append((fpath, source_tag))

    return results


def _parse_file(fpath: Path, source_tag: str, limit: int) -> list:
    """根据文件扩展名选择解析器并解析。"""
    ext = fpath.suffix.lower()
    parser_type = PARSER_MAP.get(ext, "text")

    try:
        text = fpath.read_text(encoding="utf-8")
    except OSError as e:
        print(f"[local_trends] 无法读取 {fpath}: {e}", file=sys.stderr)
        return []

    if parser_type == "markdown":
        return _parse_markdown(text, source_tag, limit)
    elif parser_type == "json":
        return _parse_json(text, source_tag, limit)
    elif parser_type == "jsonl":
        return _parse_jsonl(text, source_tag, limit)
    elif parser_type == "csv":
        return _parse_csv(text, source_tag, limit)
    else:
        return _parse_text(text, source_tag, limit)


# ----------------------------- 主逻辑 -----------------------------

def collect(sources: list[str] | None = None,
            limit_per_source: int = 30,
            keyword: str | None = None,
            data_dir: str | None = None) -> dict:
    """从本地文件读取热点数据，输出与 fetch_trends.collect() 一致的结构。"""
    # 确定数据目录
    if data_dir:
        base_dir = Path(data_dir)
    else:
        env_dir = os.environ.get("YANG_LOCAL_DATA_DIR", "")
        if env_dir:
            base_dir = Path(env_dir) / "trends"
        else:
            # 默认在 trend-sources 同级的 local-data/trends/ 下
            base_dir = Path(__file__).parent / "local-data"

    if not base_dir.is_dir():
        print(f"[local_trends] 数据目录不存在: {base_dir}", file=sys.stderr)
        print(f"[local_trends] 请创建目录并放入热点数据文件（.md/.json/.csv）", file=sys.stderr)
        return {
            "meta": {
                "anchor": _now_iso(),
                "sources_requested": sources or ["all"],
                "sources_succeeded": [],
                "keyword_filter": keyword,
                "total": 0,
                "errors": [{"source": "local", "error": f"数据目录不存在: {base_dir}"}],
                "freshness_available": False,
                "mode": "local",
            },
            "trends": [],
        }

    # 发现文件
    files = _discover_files(base_dir, sources)

    if not files:
        print(f"[local_trends] 在 {base_dir} 中未找到数据文件", file=sys.stderr)
        return {
            "meta": {
                "anchor": _now_iso(),
                "sources_requested": sources or ["all"],
                "sources_succeeded": [],
                "keyword_filter": keyword,
                "total": 0,
                "errors": [{"source": "local", "error": "未找到数据文件"}],
                "freshness_available": False,
                "mode": "local",
            },
            "trends": [],
        }

    all_items = []
    errors = []
    used = []

    for fpath, source_tag in files:
        source_name = fpath.stem.lower()
        try:
            items = _parse_file(fpath, source_tag, limit_per_source)
            if keyword:
                items = [it for it in items if keyword in (it.get("title") or "")]
            all_items.extend(items)
            used.append(source_name)
            print(f"[local_trends:{source_name}] 读取 {len(items)} 条", file=sys.stderr)
        except Exception as exc:
            errors.append({"source": source_name, "error": str(exc)})
            print(f"[local_trends:{source_name}] 解析失败: {exc}", file=sys.stderr)

    # 去重（同标题保留热度更高者）
    dedup = {}
    for it in all_items:
        key = it["title"]
        if not key:
            continue
        if key not in dedup:
            dedup[key] = it
        else:
            old = dedup[key]
            if (it.get("hotness") or 0) > (old.get("hotness") or 0):
                dedup[key] = it
    merged = list(dedup.values())
    merged.sort(key=lambda x: (x.get("hotness") or 0), reverse=True)

    return {
        "meta": {
            "anchor": _now_iso(),
            "sources_requested": sources or ["all"],
            "sources_succeeded": used,
            "keyword_filter": keyword,
            "total": len(merged),
            "errors": errors,
            "freshness_available": False,
            "mode": "local",
            "data_dir": str(base_dir),
        },
        "trends": merged,
    }


def main():
    parser = argparse.ArgumentParser(
        description="本地热点数据读取器（零网络 · 零外部依赖）"
    )
    parser.add_argument(
        "--sources", default=None,
        help="逗号分隔的热点源（文件名前缀）；不指定则读取全部文件"
    )
    parser.add_argument(
        "--limit", type=int, default=30,
        help="每个源最多取多少条（默认: 30）"
    )
    parser.add_argument(
        "--keyword", default=None,
        help="只保留标题含该关键词的热点（垂直筛选）"
    )
    parser.add_argument(
        "--data-dir", default=None,
        help="本地数据目录路径（默认: adapters/trend-sources/local-data/ 或 $YANG_LOCAL_DATA_DIR/trends/）"
    )
    parser.add_argument(
        "--out", default=None,
        help="输出 JSON 路径（默认打印到 stdout）"
    )
    args = parser.parse_args()

    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()] if args.sources else None
    result = collect(sources, args.limit, args.keyword, args.data_dir)

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(
            f"[local_trends] 已写入 {args.out}（{result['meta']['total']} 条，"
            f"成功源 {len(result['meta']['sources_succeeded'])}/{len(sources or ['all'])}）",
            file=sys.stderr,
        )
    else:
        print(payload)

    if not result["meta"]["sources_succeeded"]:
        print(
            "[local_trends] 所有本地源均不可用——请检查数据目录和文件格式。\n"
            "数据目录应包含 .md/.json/.csv 格式的热点数据文件。\n"
            "详见 shared-protocols/local-fallback.md",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()


# ----------------------------- 统一入口（供 registry.py 调用） -----------------------------

def load_from_local(sources: list[str] | None = None,
                    limit_per_source: int = 30,
                    keyword: str | None = None,
                    data_dir: str | None = None) -> dict:
    """统一入口函数，供 registry.py 或其他上层模块调用。

    参数与 collect() 完全一致，返回值结构与 fetch_trends.collect() 一致。
    额外在 meta 中标注 ``"mode": "local"`` 和 ``"data_freshness": "non-realtime"``，
    便于上层判断数据来源并附加"⚠ 数据非实时"提示。

    用法::

        from adapters.trend_sources.local_trends import load_from_local
        result = load_from_local(keyword="AI")
        if result["trends"]:
            print(f"读取到 {len(result['trends'])} 条本地热点（非实时）")
    """
    result = collect(sources, limit_per_source, keyword, data_dir)
    # 标注数据非实时
    result["meta"]["data_freshness"] = "non-realtime"
    return result
