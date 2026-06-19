# 作者: 阿洋
"""Yang.skills v4 浏览器通用提取器 - 基于 Playwright"""
from __future__ import annotations

import sys
import asyncio
import argparse
from typing import Optional

_PLAYWRIGHT_MISSING = False
try:
    from playwright.async_api import async_playwright
except ImportError:
    _PLAYWRIGHT_MISSING = True


async def extract_page_content(url: str) -> str:
    if _PLAYWRIGHT_MISSING:
        return (
            "[collector] Playwright 未安装。请执行: pip install playwright && playwright install chromium"
        )
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            text = await page.inner_text("body")
            await browser.close()
            return text.strip()
    except Exception as e:
        return f"[collector] extract_page_content error: {e}"


async def scroll_and_extract(url: str, scroll_count: int = 10) -> list[str]:
    if _PLAYWRIGHT_MISSING:
        return [
            "[collector] Playwright 未安装。请执行: pip install playwright && playwright install chromium"
        ]
    results: list[str] = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            for i in range(scroll_count):
                body_text = await page.inner_text("body")
                results.append(body_text.strip())
                await page.evaluate(
                    "window.scrollBy(0, window.innerHeight * 0.8)"
                )
                await page.wait_for_timeout(1500)

            await browser.close()
    except Exception as e:
        results.append(f"[collector] scroll_and_extract error: {e}")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Yang.skills v4 浏览器通用提取器"
    )
    parser.add_argument("url", help="目标网页 URL")
    parser.add_argument(
        "--scroll", "-s",
        type=int,
        default=0,
        help="滚动提取模式，指定滚动次数（默认 0 即只提取 body 文本）",
    )

    if _PLAYWRIGHT_MISSING:
        print(
            "[collector] Playwright 未安装。\n"
            "请执行: pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    args = parser.parse_args()

    if args.scroll > 0:
        results = asyncio.run(scroll_and_extract(args.url, args.scroll))
        for idx, chunk in enumerate(results):
            print(f"--- scroll {idx} ---")
            print(chunk[:2000])
            if len(chunk) > 2000:
                print(f"... (truncated, total {len(chunk)} chars)")
    else:
        text = asyncio.run(extract_page_content(args.url))
        print(text[:5000])
        if len(text) > 5000:
            print(f"\n... (truncated, total {len(text)} chars)")


if __name__ == "__main__":
    main()