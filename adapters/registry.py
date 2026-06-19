# 作者: 阿洋
"""适配器注册 — 将所有适配器注册到统一接口

使用方式：
    from adapters.registry import AdapterRegistry

    # 拉取热点
    result = AdapterRegistry.collect("trends", sources=["weibo", "zhihu"], limit=30)

    # 搜索意图
    result = AdapterRegistry.collect("search-intent", keyword="AI工具", limit=20)

    # 竞品搜索
    result = AdapterRegistry.collect("competitor-search", keyword="AI博主", limit=10)

    # 检查所有适配器可用性
    status = AdapterRegistry.list_available()
"""

from adapters.adapter_base import BaseAdapter, AdapterRegistry


class TrendsAdapter(BaseAdapter):
    """热点趋势适配器 — 本地优先+网络增强"""
    name = "trends"
    requires_browser = False
    requires_api = True  # 需要网络请求

    def check_available(self):
        missing = []
        try:
            from adapters.trend_sources import fetch_trends
        except ImportError:
            missing.append("fetch_trends.py")
        return {"available": len(missing) == 0, "mode": "api", "missing": missing}

    def collect(self, sources=None, limit=30, keyword=None, **kwargs):
        from adapters.trend_sources.fetch_trends import collect as _collect
        return _collect(sources=sources or ["weibo", "zhihu", "bilibili", "baidu", "douyin", "toutiao"],
                       limit_per_source=limit, keyword=keyword)


class SearchIntentAdapter(BaseAdapter):
    """搜索意图适配器 — 本地优先+网络增强"""
    name = "search-intent"
    requires_browser = False
    requires_api = True

    def check_available(self):
        missing = []
        try:
            from adapters.search_intent import search_intent
        except ImportError:
            missing.append("search_intent.py")
        return {"available": len(missing) == 0, "mode": "api", "missing": missing}

    def collect(self, keyword="", sources=None, limit=20, depth=2, **kwargs):
        from adapters.search_intent.search_intent import collect_intent_signals
        return collect_intent_signals(keyword=keyword, sources=sources, limit_per_source=limit)


class CompetitorSearchAdapter(BaseAdapter):
    """竞品搜索适配器 — 本地优先+浏览器增强"""
    name = "competitor-search"
    requires_browser = True  # 可选浏览器增强
    requires_api = True

    def check_available(self):
        missing = []
        try:
            from adapters.competitor_search import search
        except ImportError:
            missing.append("search.py")
        return {"available": len(missing) == 0, "mode": "browser-enhanced", "missing": missing}

    def collect(self, keyword="", platforms=None, limit=20, **kwargs):
        # 本地优先
        try:
            from adapters.competitor_search.local_search import search_local
            result = search_local(keyword=keyword, limit=limit)
            if result:
                return {"meta": {"mode": "local"}, "competitors": result}
        except Exception:
            pass
        # 浏览器增强
        from adapters.competitor_search.search import search_bilibili
        return {"meta": {"mode": "browser-enhanced"}, "competitors": search_bilibili(keyword, limit)}


class LocalTrendsAdapter(BaseAdapter):
    """本地热点适配器 — 纯本地，零网络"""
    name = "trends-local"
    requires_browser = False
    requires_api = False

    def check_available(self):
        return {"available": True, "mode": "local", "missing": []}

    def collect(self, data_dir=".", **kwargs):
        from adapters.trend_sources.local_trends import load_from_local
        return load_from_local(data_dir)


# 注册所有适配器
AdapterRegistry.register("trends", TrendsAdapter())
AdapterRegistry.register("search-intent", SearchIntentAdapter())
AdapterRegistry.register("competitor-search", CompetitorSearchAdapter())
AdapterRegistry.register("trends-local", LocalTrendsAdapter())
