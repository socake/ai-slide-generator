"""主题预设加载:读 templates/themes/*.json → ThemeSpec。坏文件跳过并告警,绝不整盘崩。"""

from __future__ import annotations

import warnings
from pathlib import Path

from pydantic import ValidationError

from packages.core import ThemeSpec


def load_themes(themes_dir: Path) -> dict[str, ThemeSpec]:
    """加载目录下所有合法预设,返回 {文件名stem: ThemeSpec}。"""
    out: dict[str, ThemeSpec] = {}
    for path in sorted(themes_dir.glob("*.json")):
        try:
            out[path.stem] = ThemeSpec.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            warnings.warn(f"跳过坏主题预设 {path.name}: {exc}", stacklevel=2)
    return out
