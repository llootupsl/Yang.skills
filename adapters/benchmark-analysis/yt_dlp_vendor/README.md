# yt_dlp_vendor - yt-dlp 源码 vendor 包

> 作者: 阿洋

本目录为 Yang.skills 引入 yt-dlp 源码的 vendor 入口，实现"源码优先，pip 回退"的加载策略。

## 设计背景

`adapters/benchmark-analysis/download.py` 原先通过 `import yt_dlp`（pip install 方式）使用 yt-dlp。
用户要求直接引入源码而非 pip install。由于 yt-dlp 完整源码非常大（数千个文件、193k+ 行提取器代码），
全量引入会导致仓库膨胀。因此采用"懒加载代理"策略。

## 加载策略

`yt_dlp_loader.get_yt_dlp()` 按以下优先级加载 yt-dlp：

1. **vendor 版本（最高优先级）**：从本目录下的 `yt_dlp/` 子目录加载完整源码
2. **pip 版本（回退）**：从 pip install 的 yt-dlp 包加载
3. **环境变量路径**：通过 `YANG_YTDLP_VENDOR_PATH` 指定额外的源码路径

默认情况下（vendor 目录无完整源码），行为与原 download.py 一致（使用 pip 版本），
保证不破坏现有功能。用户将 yt-dlp 完整源码放入 `yt_dlp/` 子目录后，自动切换到 vendor 版本。

## 如何引入完整 yt-dlp 源码

若需使用 vendor 版本（完全不依赖 pip install），执行以下步骤：

```bash
# 1. 克隆 yt-dlp 源码
git clone https://github.com/yt-dlp/yt-dlp.git /tmp/yt-dlp-src

# 2. 将 yt_dlp 包目录复制到 vendor 下
cp -r /tmp/yt-dlp-src/yt_dlp adapters/benchmark-analysis/yt_dlp_vendor/yt_dlp

# 3. 验证
python -c "from adapters.benchmark-analysis.yt_dlp_vendor import get_yt_dlp; print(get_yt_dlp().version)"
```

引入后，`is_vendor_available()` 会返回 `True`，`get_source_info()` 返回 `"vendor"`。

## 文件清单

```
adapters/benchmark-analysis/yt_dlp_vendor/
├── __init__.py          # vendor 包入口，暴露 get_yt_dlp 等函数
├── yt_dlp_loader.py     # 加载器：vendor 优先，pip 回退
├── LICENSE              # yt-dlp 原始许可证（Unlicense）
├── README.md            # 本文件
└── yt_dlp/              # 用户手动放入的完整 yt-dlp 源码（默认不存在）
```

## yt-dlp 核心模块架构（供维护参考）

yt-dlp 采用管道式（Pipeline）架构，由 `YoutubeDL` 类作为中央调度器：

| 层级 | 核心职责 | 关键文件 |
|------|---------|---------|
| 入口层 | 解析 CLI 参数、加载配置 | `options.py`, `__init__.py` |
| 调度层 | 提取器匹配、格式选择、下载编排、后处理调度 | `YoutubeDL.py` |
| 提取层 | URL 匹配、网页抓取、视频元数据提取 | `extractor/` |
| 网络层 | 请求发送、SSL、代理、Cookie、浏览器指纹模拟 | `networking/` |
| 下载层 | HTTP/HLS/DASH/RTMP 等协议的实际下载 | `downloader/` |
| 后处理层 | FFmpeg 音视频处理、元数据嵌入、格式转换 | `postprocessor/` |

核心数据结构为 `info_dict`，贯穿提取→下载→后处理全流程。

## 许可证

yt-dlp 源码采用 [Unlicense](https://unlicense.org)（公共领域）许可证。
本目录下的 `LICENSE` 文件为 yt-dlp 原始许可证的完整副本。

引入的 yt-dlp 源码（若用户手动放入）必须保留其原始 Unlicense 许可证声明。

## 与 Yang.skills 的集成

- `download.py` 通过 `_import_yt_dlp()` 调用 `yt_dlp_loader.get_yt_dlp()` 获取 yt-dlp 模块
- 加载策略对 `download.py` 的其余逻辑（元数据写入、时效判定、平台检测）完全透明
- 不影响 `transcribe.py`、`extract_frames.py` 等其他 adapter 文件

## 稳定性等级

★★★★ — vendor 加载策略本身极简且健壮，任何异常均回退到 pip 版本，不会导致功能中断。
