# 作者: 阿洋
"""知乎排版：Markdown → 知乎粘贴友好的语义 HTML。

知乎 Web 编辑器在"粘贴富文本"时会保留**语义结构**（标题、段落、加粗、斜体、引用、
列表、代码块、图片、有序/无序列表），但会**丢弃多数内联样式**。因此面向知乎不需要像
公众号那样逐元素内联，而是产出干净的语义 HTML（让知乎用自己的样式渲染），同时做两处适配：

适配
----
1. **表格 → 列表**：知乎回答对表格支持差，把 Markdown 表格转成"行：列1｜列2"的无序列表。
2. **LaTeX 保留**：行内 $...$ 与块级 $$...$$ 原样保留（知乎原生支持公式）。
3. **标题降级**：知乎正文从 h2 起更自然，# 映射为 h1、## 起为 h2（与知乎层级一致）。
4. **代码块**：转 <pre><code>，知乎会识别为代码区。

用法
----
  python zhihu_format.py --in answer.md --out answer.html
  cat answer.md | python zhihu_format.py > answer.html
"""
from __future__ import annotations

import argparse
import html as _html
import re
import sys


def _inline(s: str) -> str:
    # 先抠出行内公式，避免被转义
    holds = []

    def hold(m):
        holds.append(m.group(0))
        return f"\x00{len(holds)-1}\x00"

    s = re.sub(r"\$[^$\n]+\$", hold, s)
    s = _html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    # 还原公式
    s = re.sub(r"\x00(\d+)\x00", lambda m: holds[int(m.group(1))], s)
    return s


def _table_to_list(rows: list) -> str:
    """Markdown 表格 → 无序列表。rows: 原始行（含表头与分隔行）。"""
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    if len(cells) < 2:
        return ""
    header = cells[0]
    body = cells[2:] if re.match(r"^[\s:|-]+$", "|".join(cells[1])) else cells[1:]
    items = []
    for row in body:
        pairs = []
        for j, val in enumerate(row):
            key = header[j] if j < len(header) else ""
            pairs.append(f"<strong>{_inline(key)}</strong>：{_inline(val)}" if key else _inline(val))
        items.append("<li>" + " ｜ ".join(pairs) + "</li>")
    return "<ul>" + "".join(items) + "</ul>"


def convert(md: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out, para = [], []
    i, n = 0, len(lines)

    def flush():
        if para:
            out.append("<p>" + "<br/>".join(_inline(x) for x in para) + "</p>")
            para.clear()

    while i < n:
        raw = lines[i].rstrip()
        st = raw.strip()

        # 块级公式
        if st.startswith("$$"):
            flush()
            block = [st]
            if not (st.endswith("$$") and len(st) > 2):
                i += 1
                while i < n and "$$" not in lines[i]:
                    block.append(lines[i]); i += 1
                if i < n:
                    block.append(lines[i])
            out.append("<p>" + "\n".join(block) + "</p>")
            i += 1
            continue

        # 代码块
        if st.startswith("```"):
            flush()
            code = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>" + _html.escape("\n".join(code)) + "</code></pre>")
            continue

        if not st:
            flush(); i += 1; continue

        if re.match(r"^-{3,}$", st):
            flush(); out.append("<hr/>"); i += 1; continue

        # 表格
        if "|" in st and i + 1 < n and re.match(r"^[\s:|-]+$", lines[i + 1].strip()):
            flush()
            tbl = [raw]
            i += 1
            while i < n and "|" in lines[i] and lines[i].strip():
                tbl.append(lines[i]); i += 1
            out.append(_table_to_list(tbl))
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", st)
        if m:
            flush()
            lvl = len(m.group(1))
            tag = "h1" if lvl == 1 else "h2" if lvl == 2 else "h3"
            out.append(f"<{tag}>{_inline(m.group(2))}</{tag}>")
            i += 1
            continue

        # 引用
        if st.startswith(">"):
            flush()
            q = []
            while i < n and lines[i].strip().startswith(">"):
                q.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append("<blockquote>" + "<br/>".join(_inline(x) for x in q) + "</blockquote>")
            continue

        # 列表
        if re.match(r"^[-*]\s+", st):
            flush()
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append("<li>" + _inline(re.sub(r"^\s*[-*]\s+", "", lines[i].strip())) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if re.match(r"^\d+\.\s+", st):
            flush()
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append("<li>" + _inline(re.sub(r"^\s*\d+\.\s+", "", lines[i].strip())) + "</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        para.append(raw)
        i += 1

    flush()
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="知乎 Markdown→语义 HTML（粘贴友好）")
    ap.add_argument("--in", dest="infile", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    md = open(args.infile, encoding="utf-8").read() if args.infile else sys.stdin.read()
    out = convert(md)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"[zhihu] 已写入 {args.out}（粘贴进知乎编辑器保留结构）", file=sys.stderr)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
