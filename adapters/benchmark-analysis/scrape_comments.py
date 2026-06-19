# 作者: 阿洋
"""Yang.skills v4 评论区爬虫 - 基于 Playwright"""
import argparse
import asyncio
import json
import sys
import os
from datetime import datetime, timezone


COMMENT_SELECTORS = [
    "[class*='comment']",
    "[class*='Comment']",
    "[class*='reply']",
    "[class*='Reply']",
    "[data-e2e*='comment']",
    "[data-e2e*='Comment']",
    "[class*='message']",
    "[class*='Message']",
    "[id*='comment']",
    "[id*='Comment']",
    ".comment-item",
    ".commentItem",
    ".comment-list > *",
    ".CommentList > *",
]


def _make_video_id(url: str) -> str:
    import hashlib
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]


async def scrape_comments(url: str, output_path: str, limit: int = 200) -> dict:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("请先安装 playwright: pip install playwright && playwright install chromium")
        sys.exit(1)

    video_id = _make_video_id(url)
    comments = []
    scraped_texts = set()
    temp_path = output_path + ".tmp"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"页面加载超时或失败: {e}")
            await browser.close()
            return {
                "video_id": video_id,
                "total_comments": 0,
                "comments": [],
            }

        await page.wait_for_timeout(3000)

        for scroll_idx in range(10):
            if len(comments) >= limit:
                break

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            for selector in COMMENT_SELECTORS:
                try:
                    elements = await page.query_selector_all(selector)
                    for el in elements:
                        try:
                            text_content = await el.inner_text()
                            text_content = text_content.strip()
                            if not text_content or len(text_content) < 2:
                                continue
                            text_hash = text_content[:120]
                            if text_hash in scraped_texts:
                                continue
                            scraped_texts.add(text_hash)

                            likes = 0
                            reply_count = 0

                            like_els = await el.query_selector_all("[class*='like'], [class*='Like'], [class*='digg'], [class*='Digg'], [class*='up']")
                            for lel in like_els:
                                try:
                                    t = await lel.inner_text()
                                    t = t.strip()
                                    for word in t.split():
                                        try:
                                            likes = max(likes, int(word))
                                        except ValueError:
                                            pass
                                except Exception:
                                    pass

                            comment = {
                                "content": text_content,
                                "likes": likes,
                                "reply_count": reply_count,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                            comments.append(comment)

                            if len(comments) >= limit:
                                break
                        except Exception:
                            continue
                except Exception:
                    continue

                if len(comments) >= limit:
                    break

            result_snapshot = {
                "video_id": video_id,
                "total_comments": len(comments),
                "comments": comments,
            }
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(result_snapshot, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        await browser.close()

    if len(comments) > limit:
        comments = comments[:limit]

    result = {
        "video_id": video_id,
        "total_comments": len(comments),
        "comments": comments,
    }

    try:
        os.rename(temp_path, output_path)
    except Exception:
        pass

    return result


def main():
    parser = argparse.ArgumentParser(description="评论区爬虫")
    parser.add_argument("url", type=str, help="视频 URL")
    parser.add_argument("--output", type=str, required=True, help="输出 JSON 路径")
    parser.add_argument("--limit", type=int, default=200, help="最大评论数")
    args = parser.parse_args()

    try:
        result = asyncio.run(scrape_comments(args.url, args.output, args.limit))
        print(f"抓取完成: {result.get('total_comments', 0)} 条评论 → {args.output}")
    except Exception as e:
        print(f"抓取失败: {e}")
        temp_path = args.output + ".tmp"
        if os.path.exists(temp_path):
            try:
                with open(temp_path, 'r', encoding='utf-8') as f:
                    partial = json.load(f)
                os.rename(temp_path, args.output)
                print(f"超时恢复: 已从中间文件恢复 {partial.get('total_comments', 0)} 条评论 → {args.output}")
                sys.exit(0)
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()