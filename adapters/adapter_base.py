# 作者: 阿洋
"""统一适配器接口 — 双架构设计（借鉴 LocoAgent）

所有适配器遵循统一接口：
- local_first：优先使用本地数据/文件
- browser_enhanced：浏览器增强（需Playwright，可选）
- api_fallback：API降级（需网络，可选）

调用方无需知道底层是哪种实现，统一调用 adapter.collect() 即可。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import json
from pathlib import Path


class BaseAdapter(ABC):
    """统一适配器基类"""

    name: str = "base"
    requires_browser: bool = False
    requires_api: bool = False

    @abstractmethod
    def collect(self, **kwargs) -> dict:
        """主入口：收集数据，返回统一格式"""
        ...

    @abstractmethod
    def check_available(self) -> dict:
        """检查可用性：返回 {available: bool, mode: str, missing: list}"""
        ...

    def _load_local_file(self, path: str, format: str = "auto") -> Any:
        """从本地文件加载数据"""
        p = Path(path)
        if not p.exists():
            return None
        if format == "auto":
            suffix = p.suffix.lower()
            if suffix == ".json":
                return json.loads(p.read_text(encoding="utf-8"))
            elif suffix == ".md":
                return p.read_text(encoding="utf-8")
            elif suffix == ".csv":
                import csv
                with open(p) as f:
                    return list(csv.DictReader(f))
        return p.read_text(encoding="utf-8")

    def _save_output(self, data: Any, path: str) -> None:
        """保存输出数据"""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, (dict, list)):
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            p.write_text(str(data), encoding="utf-8")


class AdapterRegistry:
    """适配器注册中心"""

    _adapters: dict[str, BaseAdapter] = {}

    @classmethod
    def register(cls, name: str, adapter: BaseAdapter):
        cls._adapters[name] = adapter

    @classmethod
    def get(cls, name: str) -> Optional[BaseAdapter]:
        return cls._adapters.get(name)

    @classmethod
    def list_available(cls) -> dict:
        """列出所有适配器及其可用性"""
        result = {}
        for name, adapter in cls._adapters.items():
            result[name] = adapter.check_available()
        return result

    @classmethod
    def collect(cls, name: str, **kwargs) -> dict:
        """统一调用入口"""
        adapter = cls.get(name)
        if adapter is None:
            return {"error": f"适配器 '{name}' 未注册", "data": None}
        avail = adapter.check_available()
        if not avail["available"]:
            return {"error": f"适配器 '{name}' 不可用: {avail['missing']}", "data": None}
        return adapter.collect(**kwargs)
