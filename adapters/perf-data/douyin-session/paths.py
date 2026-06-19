# 作者: 阿洋
"""douyin-session shared path constants and URL endpoints."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).parent

AUTH_DIR = PACKAGE_DIR / ".auth"
DEBUG_DIR = PACKAGE_DIR / ".debug"
DATA_DIR = PACKAGE_DIR / "data"
OUTPUT_DIR = PACKAGE_DIR / "output"

CREATOR_HOME = "https://creator.douyin.com/creator-micro/home"
CREATOR_CONTENT = "https://creator.douyin.com/creator-micro/content/manage"
VIDEO_BASE_URL = "https://www.douyin.com/video"

DEFAULT_TIMEOUT_S = 300
DEFAULT_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_VIDEO_LIMIT = 50
DEFAULT_COMMENT_MAX_PAGES = 60

for _d in (AUTH_DIR, DEBUG_DIR, DATA_DIR, OUTPUT_DIR):
    _d.mkdir(exist_ok=True)