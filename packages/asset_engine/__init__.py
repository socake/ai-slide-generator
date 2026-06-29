"""packages.asset_engine —— 规则匹配素材 + safe_area(零 LLM)。索引见 assets/asset_index.json。"""

from __future__ import annotations

from packages.asset_engine.engine import AssetEngine
from packages.asset_engine.loader import load_index
from packages.asset_engine.models import AssetIndex, AssetIndexEntry

__all__ = ["AssetEngine", "load_index", "AssetIndex", "AssetIndexEntry"]
