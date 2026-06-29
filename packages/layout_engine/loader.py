"""布局预设加载:读 templates/layouts/*.json → LayoutSpec。坏文件跳过并告警。"""

from __future__ import annotations

import warnings
from pathlib import Path

from pydantic import ValidationError

from packages.core import LayoutSpec


def load_layouts(layouts_dir: Path) -> dict[str, LayoutSpec]:
    """加载目录下所有合法布局,返回 {文件名stem: LayoutSpec}。"""
    out: dict[str, LayoutSpec] = {}
    for path in sorted(layouts_dir.glob("*.json")):
        try:
            out[path.stem] = LayoutSpec.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            warnings.warn(f"跳过坏布局预设 {path.name}: {exc}", stacklevel=2)
    return out
