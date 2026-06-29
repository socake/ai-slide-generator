"""素材索引加载:assets/asset_index.json → AssetIndex。坏文件回退空索引并告警。"""

from __future__ import annotations

import warnings
from pathlib import Path

from pydantic import ValidationError

from packages.asset_engine.models import AssetIndex


def load_index(path: Path) -> AssetIndex:
    """读素材索引 JSON → AssetIndex;文件缺失或损坏则回退空索引并告警。"""
    try:
        return AssetIndex.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        warnings.warn(f"跳过坏素材索引 {path.name}: {exc}", stacklevel=2)
        return AssetIndex()
