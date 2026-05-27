# .opencode/scripts/publisher/adapters/__init__.py
"""平台适配器注册表。新增平台只需在此 import 模块。"""
from __future__ import annotations

from typing import Dict, Type

from publisher.base import BasePlatform

_registry: Dict[str, Type[BasePlatform]] = {}
_loaded = False


def _ensure_loaded():
    global _loaded
    if _loaded:
        return
    # 模块 import 时通过 register() 自动注册
    from publisher.adapters import fanqie  # noqa: F401
    from publisher.adapters import qimao  # noqa: F401
    _loaded = True


def register(name: str):
    def dec(cls):
        _registry[name] = cls
        return cls
    return dec


def get_adapter(name: str) -> BasePlatform:
    _ensure_loaded()
    cls = _registry.get(name)
    if cls is None:
        raise ValueError(f"未知平台 '{name}'。可用: {sorted(_registry.keys())}")
    return cls()


def list_platforms() -> list[str]:
    _ensure_loaded()
    return sorted(_registry.keys())
