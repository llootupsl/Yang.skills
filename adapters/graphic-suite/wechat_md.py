# 作者: 阿洋
"""公众号图文排版：Markdown → 内联样式 HTML。

微信公众号编辑器会**剥离 `<style>` 标签与外部 CSS、class 选择器**，只保留写在元素
`style=""` 里的内联样式。因此本转换器把所有排版规则**逐元素内联**，产出可直接
"全选复制 → 粘贴进公众号编辑器"且保留样式的 HTML。

支持的 Markdown 子集（覆盖公众号 99% 排版需求）
-----------------------------------------------
- 标题 # / ## / ###（一级=大标题块，二级=带左竖条小标题，三级=加粗行）
- 段落、空行
- **加粗** / *斜体* / `行内代码`
- 无序列表 - / *，有序列表 1.
- > 引用块
- --- 分隔线
- 代码块 ```（等宽、灰底、可横滚）
- [链接文字](url)（公众号正文超链接受限，渲染为带色文字 + 末尾脚注 URL）

主题
----
default / warm / dark / green，对应主色与底色（与 render_card 主题呼应）。

用法
----
  python wechat_md.py --in article.md --theme warm --out article.html
  cat article.md | python wechat_md.py --theme default > article.html
"""
from __future__ import annotations

import argparse
import html as _html
import re
import sys


THEMES = {
    "default": {"accent": "#C8693B", "ink": "#2B2622", "sub": "#6F6457",
                "quote_bg": "#FBF6EE", "code_bg": "#F5F2EC", "line": "#E7DAC5"},
    "warm":    {"accent": "#E8623D", "ink": "#3A241B", "sub": "#7A5B49",
                "quote_bg": "#FFF1E8", "code_bg": "#FBEDE3", "line": "#F6D2BB"},
    "dark":    {"accent": "#FF7A59", "ink": "#1d1f24", "sub": "#5b6270",
                "quote_bg": "#F3F4F6", "code_bg": "#F0F1F3", "line": "#E2E4E8"},
    "green":   {"accent": "#2F9E66", "ink": "#1F2D24", "sub": "#5B6E60",
                "quote_bg": "#EFF7F0", "code_bg": "#EAF3EC", "line": "#CFE6D5"},
}

FONT = ('-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB",'
        '"Microsoft YaHei",sans-serif')


def _inline(s: str) -> str:
    """行内：转义 → 代码/加粗/斜体/链接。"""
    s = _html.escape(s)
    s = re.sub(r"`([^`]+)`",
               r'<code style="background:%CODE%;padding:2px 6px;border-radius:4px;'
               r'font-family:Consolas,Menlo,monospace;font-size:95%;">\1</code>', s)
    s = re.sub(r"\*\*([^*]+)\*\*",
               r'<strong style="color:%ACCENT%;font-weight:700;">\1</strong>', s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r'<em style="font-style:italic;">\1</em>', s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<span style="color:%ACCENT%;border-bottom:1px solid %ACCENT%;">\1</span>', s)
    return s


def convert(md: str, theme_key: str = "default") -> str:
    t = THEMES.get(theme_key, THEMES["default"])
    lines = md.replace("\r\n", "\n").split("\n")
    out = []
    footnotes = []
    i, n = 0, len(lines)

    def flush_para(buf):
        if not buf:
            return
        text = "<br/>".join(_inline(x) for x in buf)
        out.append(
            f'<p style="margin:18px 0;font-size:16px;line-height:1.9;color:{t["ink"]};'
            f'letter-spacing:.3px;">{text}</p>')

    para_buf = []
    while i < n:
        ln = lines[i]
        raw = ln.rstrip()
        stripped = raw.strip()

        # 收集链接脚注
        for m in re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", stripped):
            footnotes.append((m.group(1), m.group(2)))

        # 代码块
        if stripped.startswith("```"):
            flush_para(para_buf); para_buf = []
            code = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            i += 1
            esc = _html.escape("\n".join(code))
            out.append(
                f'<pre style="background:{t["code_bg"]};border-radius:8px;padding:16px 18px;'
                f'overflow-x:auto;font-size:14px;line-height:1.6;color:{t["ink"]};'
                f'font-family:Consolas,Menlo,monospace;margin:18px 0;">'
                f'<code>{esc}</code></pre>')
            continue

        if not stripped:
            flush_para(para_buf); para_buf = []
            i += 1
            continue

        # 分隔线
        if re.match(r"^-{3,}$", stripped):
            flush_para(para_buf); para_buf = []
            out.append(f'<hr style="border:none;border-top:1px solid {t["line"]};'
                       f'margin:30px 0;"/>')
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para(para_buf); para_buf = []
            level = len(m.group(1)); txt = _inline(m.group(2))
            if level == 1:
                out.append(
                    f'<h1 style="font-size:24px;font-weight:800;color:{t["ink"]};'
                    f'margin:34px 0 18px;line-height:1.4;text-align:center;">{txt}</h1>'
                    f'<div style="width:48px;height:4px;background:{t["accent"]};'
                    f'border-radius:3px;margin:0 auto 24px;"></div>')
            elif level == 2:
                out.append(
                    f'<h2 style="font-size:20px;font-weight:700;color:{t["ink"]};'
                    f'margin:30px 0 16px;padding-left:14px;line-height:1.5;'
                    f'border-left:5px solid {t["accent"]};">{txt}</h2>')
            else:
                out.append(
                    f'<h3 style="font-size:17px;font-weight:700;color:{t["accent"]};'
                    f'margin:24px 0 12px;line-height:1.5;">{txt}</h3>')
            i += 1
            continue

        # 引用
        if stripped.startswith(">"):
            flush_para(para_buf); para_buf = []
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            qtext = "<br/>".join(_inline(x) for x in quote)
            out.append(
                f'<blockquote style="margin:20px 0;padding:14px 20px;'
                f'background:{t["quote_bg"]};border-left:4px solid {t["accent"]};'
                f'border-radius:6px;color:{t["sub"]};font-size:15px;line-height:1.8;">'
                f'{qtext}</blockquote>')
            continue

        # 无序列表
        if re.match(r"^[-*]\s+", stripped):
            flush_para(para_buf); para_buf = []
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i].strip())); i += 1
            lis = "".join(
                f'<li style="margin:10px 0;font-size:16px;line-height:1.8;'
                f'color:{t["ink"]};">{_inline(x)}</li>' for x in items)
            out.append(f'<ul style="margin:16px 0;padding-left:24px;">{lis}</ul>')
            continue

        # 有序列表
        if re.match(r"^\d+\.\s+", stripped):
            flush_para(para_buf); para_buf = []
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i].strip())); i += 1
            lis = "".join(
                f'<li style="margin:10px 0;font-size:16px;line-height:1.8;'
                f'color:{t["ink"]};">{_inline(x)}</li>' for x in items)
            out.append(f'<ol style="margin:16px 0;padding-left:26px;">{lis}</ol>')
            continue

        # 普通段落
        para_buf.append(raw)
        i += 1

    flush_para(para_buf)

    # 链接脚注（公众号正文超链接受限，把 URL 落到文末）
    if footnotes:
        seen, refs = set(), []
        for label, url in footnotes:
            if url in seen:
                continue
            seen.add(url)
            refs.append(f'<li style="margin:6px 0;font-size:13px;line-height:1.7;'
                        f'color:{t["sub"]};word-break:break-all;">{_html.escape(label)}：{_html.escape(url)}</li>')
        out.append(f'<hr style="border:none;border-top:1px solid {t["line"]};margin:28px 0;"/>'
                   f'<p style="font-size:13px;color:{t["sub"]};margin:0 0 8px;">参考链接</p>'
                   f'<ol style="padding-left:22px;margin:0;">{"".join(refs)}</ol>')

    body = "\n".join(out)
    # 替换占位符（行内样式里的主色/代码底色）
    body = body.replace("%ACCENT%", t["accent"]).replace("%CODE%", t["code_bg"])

    wrapper = (f'<section style="font-family:{FONT};max-width:677px;margin:0 auto;'
               f'padding:24px 20px;color:{t["ink"]};background:#FFFFFF;">' + body + '</section>')
    return wrapper


def main():
    ap = argparse.ArgumentParser(description="公众号 Markdown→内联样式 HTML")
    ap.add_argument("--in", dest="infile", default=None, help="输入 Markdown（默认读 stdin）")
    ap.add_argument("--out", default=None, help="输出 HTML（默认 stdout）")
    ap.add_argument("--theme", default="default", choices=list(THEMES.keys()))
    args = ap.parse_args()

    md = open(args.infile, encoding="utf-8").read() if args.infile else sys.stdin.read()
    out_html = convert(md, args.theme)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_html)
        print(f"[wechat] 已写入 {args.out}（全选复制粘贴进公众号即保留排版）", file=sys.stderr)
    else:
        sys.stdout.write(out_html)


if __name__ == "__main__":
    main()
