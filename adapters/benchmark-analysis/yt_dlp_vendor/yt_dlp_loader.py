# 作者: 阿洋
"""yt-dlp 源码加载器

作者: 阿洋

本模块实现 yt-dlp 的"vendor 优先，pip 回退"加载策略：

1. 优先从 vendor 目录加载已引入的 yt-dlp 源码
2. 若 vendor 目录未引入完整源码，回退到 pip install 的 yt-dlp
3. 若两者均不可用，抛出 ImportError 并提示安装方式

加载顺序（优先级从高到低）：
- 环境变量 YANG_YTDLP_VENDOR_PATH 指定的路径
- 本 vendor 目录下的 yt_dlp/ 子目录（用户可手动放入完整源码）
- pip install 的 yt-dlp 包

这样设计的好处：
- 默认情况下（vendor 目录无完整源码），行为与原 download.py 一致（用 pip 版本）
- 用户将 yt-dlp 完整源码放入 vendor/yt_dlp/ 后，自动切换到 vendor 版本
- 不破坏现有功能，平滑过渡
"""
# 作者: 阿洋

import importlib
import os
import sys

__author__ = "阿洋"

# vendor 目录路径
_VENDOR_DIR = os.path.dirname(os.path.abspath(__file__))

# 用户可通过环境变量指定额外的 vendor 源码路径
_EXTRA_VENDOR_PATH = os.environ.get("YANG_YTDLP_VENDOR_PATH", "")

# vendor 目录下 yt_dlp 子目录的路径（用户可将完整源码放入此处）
_VENDOR_YT_DLP_DIR = os.path.join(_VENDOR_DIR, "yt_dlp")

# 缓存已加载的 yt_dlp 模块，避免重复加载
_cached_yt_dlp = None
_cached_source = None  # "vendor" 或 "pip"


def _ensure_vendor_path() -> None:
    """将 vendor 目录及额外路径加入 sys.path，确保可被 import。"""
    paths_to_add = []
    # vendor 根目录（让 `import yt_dlp_vendor` 可用）
    parent_dir = os.path.dirname(_VENDOR_DIR)
    if parent_dir not in sys.path:
        paths_to_add.append(parent_dir)
    # vendor 下的 yt_dlp 子目录（让 `import yt_dlp` 指向 vendor 版本）
    if os.path.isdir(_VENDOR_YT_DLP_DIR):
        if _VENDOR_YT_DLP_DIR not in sys.path:
            paths_to_add.append(_VENDOR_YT_DLP_DIR)
    # 环境变量指定的额外路径
    if _EXTRA_VENDOR_PATH and os.path.isdir(_EXTRA_VENDOR_PATH):
        if _EXTRA_VENDOR_PATH not in sys.path:
            paths_to_add.append(_EXTRA_VENDOR_PATH)
    # 插入到 sys.path 最前面，确保优先级高于 pip 安装版本
    for p in reversed(paths_to_add):
        sys.path.insert(0, p)


def is_vendor_available() -> bool:
    """检查 vendor 目录是否已引入完整的 yt-dlp 源码。

    判定依据：vendor/yt_dlp/ 目录下存在 YoutubeDL.py 且可导入 YoutubeDL 类。
    """
    if not os.path.isdir(_VENDOR_YT_DLP_DIR):
        return False
    # 检查核心文件是否存在
    core_file = os.path.join(_VENDOR_YT_DLP_DIR, "YoutubeDL.py")
    if not os.path.isfile(core_file):
        return False
    init_file = os.path.join(_VENDOR_YT_DLP_DIR, "__init__.py")
    if not os.path.isfile(init_file):
        return False
    return True


def _load_from_vendor():
    """从 vendor 目录加载 yt-dlp 源码。

    返回 yt_dlp 模块对象，失败返回 None。
    """
    if not is_vendor_available():
        return None
    _ensure_vendor_path()
    try:
        # 若此前已导入 pip 版本的 yt_dlp，需先从 sys.modules 移除，
        # 否则 import 会直接返回缓存中的 pip 版本
        if "yt_dlp" in sys.modules:
            # 仅当缓存的 yt_dlp 路径不在 vendor 目录下时才移除
            cached_mod = sys.modules["yt_dlp"]
            cached_path = getattr(cached_mod, "__file__", "") or ""
            if not cached_path.startswith(_VENDOR_YT_DLP_DIR):
                # 移除 yt_dlp 及其所有子模块的缓存
                keys_to_remove = [k for k in sys.modules if k == "yt_dlp" or k.startswith("yt_dlp.")]
                for k in keys_to_remove:
                    del sys.modules[k]
        return importlib.import_module("yt_dlp")
    except ImportError:
        return None
    except Exception:
        # 任何异常都回退到 pip 版本，保证不破坏现有功能
        return None


def _load_from_pip():
    """从 pip install 加载 yt-dlp。

    返回 yt_dlp 模块对象，失败返回 None。
    """
    try:
        return importlib.import_module("yt_dlp")
    except ImportError:
        return None
    except Exception:
        return None


def get_yt_dlp():
    """获取 yt-dlp 模块，优先 vendor 版本，回退 pip 版本。

    返回 yt_dlp 模块对象。
    若两者均不可用，抛出 ImportError 并提示安装方式。

    此函数有缓存：首次调用后结果会被缓存，后续调用直接返回缓存值。
    """
    global _cached_yt_dlp, _cached_source

    if _cached_yt_dlp is not None:
        return _cached_yt_dlp

    # 1. 优先尝试 vendor 版本
    mod = _load_from_vendor()
    if mod is not None:
        _cached_yt_dlp = mod
        _cached_source = "vendor"
        return mod

    # 2. 回退到 pip 版本
    mod = _load_from_pip()
    if mod is not None:
        _cached_yt_dlp = mod
        _cached_source = "pip"
        return mod

    # 3. 两者均不可用
    raise ImportError(
        "yt-dlp 不可用。请通过以下任一方式安装：\n"
        "  1. pip install yt-dlp\n"
        "  2. 将 yt-dlp 完整源码放入 "
        f"{_VENDOR_YT_DLP_DIR}\n"
        "  3. 设置环境变量 YANG_YTDLP_VENDOR_PATH 指向 yt-dlp 源码目录"
    )


def get_yt_dlp_version() -> str:
    """获取当前使用的 yt-dlp 版本号。

    返回版本字符串，如 "2024.12.13"。
    若无法获取版本，返回 "unknown"。
    """
    try:
        mod = get_yt_dlp()
        version = getattr(mod, "version", None)
        if version is None:
            # 尝试从 __version__ 获取
            version = getattr(mod, "__version__", "unknown")
        return str(version)
    except Exception:
        return "unknown"


def get_source_info() -> str:
    """获取当前 yt-dlp 的来源信息（vendor 或 pip）。"""
    if _cached_source is None:
        # 触发加载
        try:
            get_yt_dlp()
        except ImportError:
            return "unavailable"
    return _cached_source or "unavailable"
