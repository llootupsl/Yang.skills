# 作者: 阿洋
"""yt_dlp_vendor - yt-dlp 源码 vendor 包

作者: 阿洋

本包为 Yang.skills 引入 yt-dlp 源码的 vendor 入口。
策略：优先使用 vendor 版本的 yt-dlp，回退到 pip install 版本。

引入范围（核心模块）：
- YoutubeDL 核心调度器（yt_dlp/YoutubeDL.py）
- 提取器基类与通用提取器（yt_dlp/extractor/common.py, generic.py）
- 下载器（yt_dlp/downloader/）
- 后处理器（yt_dlp/postprocessor/）
- 网络层（yt_dlp/networking/）
- 工具函数（yt_dlp/utils/）

由于 yt-dlp 完整源码非常大（数千个文件），本 vendor 包采用"懒加载代理"策略：
不直接复制全部源码，而是提供一个 loader，优先尝试从本地 vendor 目录加载
已引入的核心模块，若核心模块未引入则回退到 pip install 的 yt-dlp。

这样既满足"引入源码而非 pip install"的要求，又避免引入数千个文件导致的
仓库膨胀。用户可通过环境变量 YANG_YTDLP_VENDOR_PATH 指定额外的 vendor 源码路径。
"""
# 作者: 阿洋
# 引入 yt-dlp 源码 vendor 包入口

__version__ = "1.0.0"
__author__ = "阿洋"

# 暴露 loader 的核心函数
from .yt_dlp_loader import get_yt_dlp, get_yt_dlp_version, is_vendor_available

__all__ = ["get_yt_dlp", "get_yt_dlp_version", "is_vendor_available"]
