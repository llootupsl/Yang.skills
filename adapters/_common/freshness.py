# 作者: 阿洋
"""时效锁（Freshness / Time-Lock）通用工具。

设计目标
--------
全系统在抓取、分析对标视频、竞品快照、热点选题时，必须以"运行那一刻的真实日期"为锚，
对一切外部数据做新鲜度判定，防止把旧时间的内容当成当下有效信号。

三档语义
--------
- fresh   ：发布时间落在新鲜窗口内（默认 90 天），可直接作为当下信号使用。
- aging   ：超过新鲜窗口但未超过硬上限（默认 365 天），可用但必须显式标注"偏旧"。
- stale   ：超过硬上限，默认从分析中剔除（或强制人工确认后降权使用）。

锚点
----
`now_anchor()` 永远返回"运行此刻"的 UTC 时间，绝不硬编码任何固定日期；所有相对天数
都基于这个锚点计算。这保证了"最新时间"随每次运行自动推进。

本模块零第三方依赖，可被任何 adapter / 脚本直接导入：
    from adapters._common import freshness
也可被 cwd 在 adapters 目录下的脚本以 `from _common import freshness` 方式导入。
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta

# 默认窗口；可被 shared-protocols/constants.md 中的 FRESHNESS_WINDOW_DAYS 覆盖，
# 也可由调用方在运行时显式传参覆盖。
DEFAULT_FRESHNESS_WINDOW_DAYS = 90
DEFAULT_STALE_HARD_LIMIT_DAYS = 365


def now_anchor() -> datetime:
    """运行此刻的 UTC 时间（带时区）。所有新鲜度判定的唯一锚点。"""
    return datetime.now(timezone.utc)


def _coerce_tz(dt: datetime) -> datetime:
    """无时区的 datetime 统一按 UTC 处理，避免 naive/aware 比较报错。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_publish_date(value) -> datetime | None:
    """把各平台五花八门的发布时间统一解析为带时区的 datetime。

    支持：
    - datetime 对象
    - Unix 时间戳（int/float，秒级或毫秒级自动识别）
    - ISO8601 字符串（含/不含 Z、含/不含时区）
    - 常见日期串："2026-06-01"、"2026/06/01"、"2026.06.01"、"2026年6月1日"
    - 相对中文时间："3天前"、"昨天"、"刚刚"、"2小时前"、"上周"
    解析失败返回 None（调用方应将其视为"无法判定新鲜度"，从严处理）。
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return _coerce_tz(value)

    # 数值时间戳
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        try:
            num = float(value)
            # 13 位 ≈ 毫秒
            if num > 1e12:
                num /= 1000.0
            return datetime.fromtimestamp(num, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None

    s = str(value).strip()

    # 相对中文时间
    rel = _parse_relative_cn(s)
    if rel is not None:
        return rel

    # ISO8601
    iso = s.replace("Z", "+00:00")
    try:
        return _coerce_tz(datetime.fromisoformat(iso))
    except ValueError:
        pass

    # 中文 / 分隔符日期
    m = re.search(r"(\d{4})\s*[-/.\u5e74]\s*(\d{1,2})\s*[-/.\u6708]\s*(\d{1,2})", s)
    if m:
        y, mo, d = (int(g) for g in m.groups())
        try:
            return datetime(y, mo, d, tzinfo=timezone.utc)
        except ValueError:
            return None

    # 仅年月
    m = re.search(r"(\d{4})\s*[-/.\u5e74]\s*(\d{1,2})", s)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        try:
            return datetime(y, mo, 1, tzinfo=timezone.utc)
        except ValueError:
            return None

    return None


def _parse_relative_cn(s: str) -> datetime | None:
    now = now_anchor()
    if s in ("\u521a\u521a", "\u521a\u521a\u53d1\u5e03", "\u73b0\u5728", "\u4eca\u5929"):  # 刚刚/现在/今天
        return now
    if s in ("\u6628\u5929",):  # 昨天
        return now - timedelta(days=1)
    if s in ("\u524d\u5929",):  # 前天
        return now - timedelta(days=2)
    if s in ("\u4e0a\u5468", "\u4e0a\u4e2a\u661f\u671f"):  # 上周
        return now - timedelta(days=7)
    if s in ("\u4e0a\u4e2a\u6708", "\u4e0a\u6708"):  # 上个月
        return now - timedelta(days=30)
    m = re.match(r"(\d+)\s*\u5206\u949f\u524d", s)  # N分钟前
    if m:
        return now - timedelta(minutes=int(m.group(1)))
    m = re.match(r"(\d+)\s*\u5c0f\u65f6\u524d", s)  # N小时前
    if m:
        return now - timedelta(hours=int(m.group(1)))
    m = re.match(r"(\d+)\s*\u5929\u524d", s)  # N天前
    if m:
        return now - timedelta(days=int(m.group(1)))
    m = re.match(r"(\d+)\s*\u5468\u524d", s)  # N周前
    if m:
        return now - timedelta(weeks=int(m.group(1)))
    m = re.match(r"(\d+)\s*\u4e2a?\u6708\u524d", s)  # N个月前 / N月前
    if m:
        return now - timedelta(days=int(m.group(1)) * 30)
    return None


def days_since(publish_date, anchor: datetime | None = None) -> float | None:
    """距今天数（基于运行此刻锚点）。无法解析返回 None。"""
    dt = parse_publish_date(publish_date)
    if dt is None:
        return None
    anchor = anchor or now_anchor()
    return (anchor - dt).total_seconds() / 86400.0


def freshness_label(
    publish_date,
    window_days: int = DEFAULT_FRESHNESS_WINDOW_DAYS,
    hard_limit_days: int = DEFAULT_STALE_HARD_LIMIT_DAYS,
    anchor: datetime | None = None,
) -> str:
    """返回 'fresh' | 'aging' | 'stale' | 'unknown'。"""
    d = days_since(publish_date, anchor=anchor)
    if d is None:
        return "unknown"
    if d < 0:
        # 未来时间（时区/解析异常），按 fresh 处理但调用方可另行警示
        return "fresh"
    if d <= window_days:
        return "fresh"
    if d <= hard_limit_days:
        return "aging"
    return "stale"


def is_stale(publish_date, hard_limit_days: int = DEFAULT_STALE_HARD_LIMIT_DAYS, anchor: datetime | None = None) -> bool:
    d = days_since(publish_date, anchor=anchor)
    if d is None:
        # 无法判定新鲜度：从严，视为可疑（不直接剔除，交由调用方决定）
        return False
    return d > hard_limit_days


def annotate(record: dict, date_field: str = "publish_date",
             window_days: int = DEFAULT_FRESHNESS_WINDOW_DAYS,
             hard_limit_days: int = DEFAULT_STALE_HARD_LIMIT_DAYS) -> dict:
    """给一条记录补充新鲜度元数据，原地修改并返回。

    写入字段：
      _freshness        : fresh|aging|stale|unknown
      _days_since       : float|None
      _checked_at       : 判定时刻（运行锚点 ISO）
    """
    anchor = now_anchor()
    label = freshness_label(record.get(date_field), window_days, hard_limit_days, anchor=anchor)
    record["_freshness"] = label
    record["_days_since"] = days_since(record.get(date_field), anchor=anchor)
    record["_checked_at"] = anchor.isoformat()
    return record


def filter_recent(records, date_field: str = "publish_date",
                  window_days: int = DEFAULT_FRESHNESS_WINDOW_DAYS,
                  keep_unknown: bool = True):
    """保留新鲜窗口内的记录。

    keep_unknown=True：无法解析日期的记录保留（但会被 annotate 标为 unknown，
    由上层显式提示用户核对），避免因解析失败误删真实新内容。
    """
    out = []
    anchor = now_anchor()
    for r in records:
        label = freshness_label(r.get(date_field), window_days, anchor=anchor)
        if label == "fresh" or (label == "unknown" and keep_unknown):
            out.append(r)
    return out


def sort_by_recency(records, date_field: str = "publish_date", reverse: bool = True):
    """按发布时间排序（默认最新在前）。无法解析的排到最后。"""
    def _key(r):
        d = parse_publish_date(r.get(date_field))
        return d or datetime.min.replace(tzinfo=timezone.utc)
    return sorted(records, key=_key, reverse=reverse)


if __name__ == "__main__":
    # 自检
    samples = ["2026-06-01", "3\u5929\u524d", "\u6628\u5929", 1717200000, "2024-01-01", "garbage"]
    print("anchor:", now_anchor().isoformat())
    for s in samples:
        print(f"  {s!r:>16} -> {freshness_label(s):8} (days={days_since(s)})")
