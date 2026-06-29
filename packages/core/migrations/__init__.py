"""schema_version 链式迁移注册表(见 DATA_MODEL §7)。

读取已持久化的旧 deck_spec(dict)时,按 version 链式升级到当前版本再 parse,保证老演示稿
可重新渲染。新增可选字段(带默认值)不升主版本,不需要迁移。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

CURRENT_SCHEMA_VERSION = "1.0"

Migration = Callable[[dict[str, Any]], dict[str, Any]]

# (from_version, to_version) -> migrate(dict) -> dict
MIGRATIONS: dict[tuple[str, str], Migration] = {}


def register(from_version: str, to_version: str) -> Callable[[Migration], Migration]:
    """装饰器:注册一条 from→to 的迁移函数。"""

    def deco(fn: Migration) -> Migration:
        MIGRATIONS[(from_version, to_version)] = fn
        return fn

    return deco


def apply(
    spec: dict[str, Any],
    target: str = CURRENT_SCHEMA_VERSION,
    registry: dict[tuple[str, str], Migration] | None = None,
) -> dict[str, Any]:
    """把旧 deck_spec dict 链式升级到 target 版本。

    `registry` 默认用全局 MIGRATIONS;传入局部表便于测试,不污染全局。
    """
    reg = MIGRATIONS if registry is None else registry
    out = dict(spec)
    current = str(out.get("schema_version", "1.0"))
    seen: set[str] = set()
    while current != target:
        if current in seen:
            raise ValueError(f"migration cycle detected at {current}")
        seen.add(current)
        for (frm, to), fn in reg.items():
            if frm == current:
                out = fn(out)
                out["schema_version"] = to
                current = to
                break
        else:
            raise ValueError(f"no migration path from {current} to {target}")
    return out
