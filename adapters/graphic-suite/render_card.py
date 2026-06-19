# 作者: 阿洋
"""小红书图文卡片渲染器（HTML → PNG）。

把一组结构化内容渲染成小红书风格的竖版图卡（默认 1080×1440，3:4）：
首图（封面）+ 若干内容卡。封面承载"人群印记 + 速判性"的钩子标题，内容卡承载正文。

设计要点
--------
- **零额外服务**：用本地 Playwright(Chromium) 把 HTML 渲染成 PNG，排版可控、中文友好。
  Playwright 已是 media 档依赖（与逐帧分析共用）。若环境暂无 Chromium，脚本会**优雅降级**：
  把每张卡的 HTML 落盘并提示 `playwright install chromium`，用户可自行渲染或用浏览器另存。
- **自动分页**：正文过长时按"卡片可容纳的字数"自动拆成多张内容卡，避免溢出。
- **多主题**：内置 cream / dark / fresh / mono / sunset 五套配色（取自安先生"色彩=情绪、影调=氛围"思路）。
- **不依赖外网字体**：优先系统中文字体栈（PingFang / 苹方 / 思源 / 微软雅黑 等），离线可用。

输入
----
JSON（--in card.json）或命令行直传，结构：
  {
    "title": "封面大标题（建议含人群印记，<22字）",
    "subtitle": "封面副标题/钩子（可选）",
    "theme": "cream",                 # cream|dark|fresh|mono|sunset
    "size": "3:4",                    # 3:4(1080x1440) | 1:1(1080x1080)
    "badge": "干货|教程|避坑(可选，封面角标)",
    "cards": [
      {"heading": "小标题(可选)", "body": "正文段落，可用\\n分段"},
      ...
    ],
    "footer": "@账号名 · 关注不迷路(可选)"
  }

用法
----
  python render_card.py --in card.json --out out_dir/
  python render_card.py --title "三年存下20万" --subtitle "普通人也能做到" --body "第一步...\n第二步..." --theme cream --out out_dir/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys


# --------------------------- 主题 ---------------------------

FONT_STACK = ('-apple-system, BlinkMacSystemFont, "PingFang SC", "苹方", '
              '"Source Han Sans SC", "Noto Sans CJK SC", "Microsoft YaHei", "微软雅黑", '
              '"Hiragino Sans GB", sans-serif')

THEMES = {
    "cream":  {"bg": "#FBF6EE", "bg2": "#F3E9D7", "ink": "#2B2622", "sub": "#6F6457",
               "accent": "#C8693B", "card": "#FFFFFF", "line": "#E7DAC5"},
    "dark":   {"bg": "#15171C", "bg2": "#1E2128", "ink": "#F2F3F5", "sub": "#A7AEBA",
               "accent": "#FF7A59", "card": "#21242C", "line": "#2C313B"},
    "fresh":  {"bg": "#EFF7F0", "bg2": "#DDEEE0", "ink": "#1F2D24", "sub": "#5B6E60",
               "accent": "#2F9E66", "card": "#FFFFFF", "line": "#CFE6D5"},
    "mono":   {"bg": "#FFFFFF", "bg2": "#F4F4F5", "ink": "#18181B", "sub": "#6B6B70",
               "accent": "#111111", "card": "#FFFFFF", "line": "#E6E6E8"},
    "sunset": {"bg": "#FFF1E8", "bg2": "#FFE0CC", "ink": "#3A241B", "sub": "#7A5B49",
               "accent": "#E8623D", "card": "#FFFFFF", "line": "#F6D2BB"},
}

SIZES = {"3:4": (1080, 1440), "1:1": (1080, 1080)}


def _esc(s: str) -> str:
    return html.escape(s or "").replace("\n", "<br/>")


# --------------------------- 分页估算 ---------------------------

def _paginate(cards: list, size_key: str) -> list:
    """把内容卡按可容纳字数粗略分页，长段落拆到多张卡。"""
    # 经验阈值：3:4 内容卡正文约 240 字一屏，1:1 约 170 字一屏（含小标题时减半行）
    cap = 240 if size_key == "3:4" else 170
    out = []
    for c in cards or []:
        heading = (c.get("heading") or "").strip()
        body = (c.get("body") or "").strip()
        budget = cap - (len(heading) + 12 if heading else 0)
        if len(body) <= budget:
            out.append({"heading": heading, "body": body})
            continue
        # 按段落/句子切，贪心装箱
        chunks, cur = [], ""
        units = []
        for para in body.split("\n"):
            para = para.strip()
            if not para:
                continue
            if len(para) <= budget:
                units.append(para)
            else:
                # 长段落再按句号切
                seg = ""
                for ch in para:
                    seg += ch
                    if ch in "。！？!?" and len(seg) >= budget * 0.6:
                        units.append(seg); seg = ""
                if seg:
                    units.append(seg)
        for u in units:
            if len(cur) + len(u) + 1 > budget and cur:
                chunks.append(cur); cur = u
            else:
                cur = (cur + "\n" + u) if cur else u
        if cur:
            chunks.append(cur)
        for i, ch in enumerate(chunks):
            out.append({"heading": heading if i == 0 else (heading + " ·续" if heading else ""),
                        "body": ch})
    return out


# --------------------------- HTML 生成 ---------------------------

def _page_css(theme: dict, w: int, h: int) -> str:
    return f"""
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    html,body {{ width:{w}px; height:{h}px; }}
    body {{ font-family:{FONT_STACK}; -webkit-font-smoothing:antialiased; }}
    .page {{ width:{w}px; height:{h}px; position:relative; overflow:hidden;
             background:linear-gradient(160deg, {theme['bg']} 0%, {theme['bg2']} 100%);
             color:{theme['ink']}; padding:90px 84px; display:flex; flex-direction:column; }}
    .badge {{ align-self:flex-start; font-size:30px; font-weight:700; color:#fff;
              background:{theme['accent']}; padding:10px 26px; border-radius:999px;
              letter-spacing:2px; margin-bottom:40px; }}
    .cover-title {{ font-size:92px; line-height:1.22; font-weight:800; letter-spacing:1px;
                    word-break:break-word; }}
    .cover-title .hl {{ color:{theme['accent']}; }}
    .cover-sub {{ margin-top:40px; font-size:46px; line-height:1.5; color:{theme['sub']};
                  font-weight:500; }}
    .rule {{ width:120px; height:10px; border-radius:6px; background:{theme['accent']};
             margin:54px 0 0; }}
    .idx {{ position:absolute; right:84px; top:84px; font-size:34px; font-weight:700;
            color:{theme['sub']}; opacity:.8; }}
    .c-heading {{ font-size:56px; font-weight:800; line-height:1.3; margin-bottom:36px;
                  color:{theme['ink']}; }}
    .c-heading .dot {{ color:{theme['accent']}; }}
    .c-body {{ font-size:44px; line-height:1.74; color:{theme['ink']}; font-weight:450;
               word-break:break-word; }}
    .card-wrap {{ flex:1; background:{theme['card']}; border:3px solid {theme['line']};
                  border-radius:36px; padding:72px 64px; display:flex; flex-direction:column;
                  justify-content:flex-start; }}
    .footer {{ position:absolute; left:84px; bottom:64px; font-size:32px; color:{theme['sub']};
               font-weight:600; }}
    .spacer {{ flex:1; }}
    """


def _cover_html(d: dict, theme: dict, w: int, h: int) -> str:
    title = _esc(d.get("title", ""))
    sub = d.get("subtitle", "")
    badge = d.get("badge", "")
    footer = d.get("footer", "")
    badge_html = f'<div class="badge">{_esc(badge)}</div>' if badge else ""
    sub_html = f'<div class="cover-sub">{_esc(sub)}</div>' if sub else ""
    footer_html = f'<div class="footer">{_esc(footer)}</div>' if footer else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{_page_css(theme,w,h)}</style></head>
<body><div class="page">{badge_html}
<div class="spacer" style="flex:.18"></div>
<div class="cover-title">{title}</div>
<div class="rule"></div>
{sub_html}
<div class="spacer"></div>
{footer_html}
</div></body></html>"""


def _content_html(card: dict, idx: int, total: int, theme: dict, w: int, h: int,
                  footer: str) -> str:
    heading = card.get("heading", "")
    body = _esc(card.get("body", ""))
    heading_html = (f'<div class="c-heading"><span class="dot">▍</span>{_esc(heading)}</div>'
                    if heading else "")
    footer_html = f'<div class="footer">{_esc(footer)}</div>' if footer else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{_page_css(theme,w,h)}</style></head>
<body><div class="page">
<div class="idx">{idx}/{total}</div>
<div class="card-wrap">{heading_html}<div class="c-body">{body}</div></div>
{footer_html}
</div></body></html>"""


def build_pages(d: dict) -> list:
    theme = THEMES.get(d.get("theme", "cream"), THEMES["cream"])
    size_key = d.get("size", "3:4")
    w, h = SIZES.get(size_key, SIZES["3:4"])
    footer = d.get("footer", "")
    pages = []
    content_cards = _paginate(d.get("cards", []), size_key)
    total = len(content_cards) + 1  # +封面
    pages.append(("01_cover", _cover_html(d, theme, w, h)))
    for i, c in enumerate(content_cards, start=2):
        pages.append((f"{i:02d}_card", _content_html(c, i, total, theme, w, h, footer)))
    return pages, (w, h)


# --------------------------- 渲染 ---------------------------

def render(d: dict, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    pages, (w, h) = build_pages(d)

    # 始终落盘 HTML（降级兜底 + 可二次编辑）
    html_paths = []
    for name, h_src in pages:
        p = os.path.join(out_dir, name + ".html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(h_src)
        html_paths.append(p)

    png_paths, rendered = [], False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": w, "height": h},
                                    device_scale_factor=2)
            for name, h_src in pages:
                page.set_content(h_src, wait_until="networkidle")
                png = os.path.join(out_dir, name + ".png")
                page.screenshot(path=png, clip={"x": 0, "y": 0, "width": w, "height": h})
                png_paths.append(png)
            browser.close()
        rendered = True
    except Exception as exc:
        print(f"[graphic] Playwright 渲染不可用，已输出 HTML 供自行渲染：{exc}", file=sys.stderr)
        print("[graphic] 安装后即可出图：pip install playwright && playwright install chromium",
              file=sys.stderr)

    manifest = {"size": f"{w}x{h}", "theme": d.get("theme", "cream"),
                "page_count": len(pages), "rendered_png": rendered,
                "png": png_paths, "html": html_paths}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[graphic] {'PNG' if rendered else 'HTML'} 输出 {len(pages)} 页 → {out_dir}",
          file=sys.stderr)
    return manifest


def main():
    ap = argparse.ArgumentParser(description="小红书图文卡片渲染器（HTML→PNG）")
    ap.add_argument("--in", dest="infile", default=None, help="输入卡片 JSON")
    ap.add_argument("--out", default="graphic_out", help="输出目录")
    ap.add_argument("--title"); ap.add_argument("--subtitle"); ap.add_argument("--body")
    ap.add_argument("--theme", default="cream", choices=list(THEMES.keys()))
    ap.add_argument("--size", default="3:4", choices=list(SIZES.keys()))
    ap.add_argument("--badge"); ap.add_argument("--footer")
    args = ap.parse_args()

    if args.infile:
        with open(args.infile, encoding="utf-8") as f:
            d = json.load(f)
    else:
        if not args.title:
            ap.error("需要 --in 或至少 --title")
        cards = []
        if args.body:
            cards = [{"heading": "", "body": args.body.replace("\\n", "\n")}]
        d = {"title": args.title, "subtitle": args.subtitle or "",
             "theme": args.theme, "size": args.size,
             "badge": args.badge or "", "footer": args.footer or "", "cards": cards}
    d.setdefault("theme", args.theme); d.setdefault("size", args.size)
    render(d, args.out)


if __name__ == "__main__":
    main()
