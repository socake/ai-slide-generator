"""素材索引模型(见 docs/DATA_MODEL §5)。索引是数据(assets/asset_index.json),匹配是规则。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from packages.core import Rect
from packages.core.enums import AssetRole, SlideType


class AssetIndexEntry(BaseModel):
    object_key: str  # assets/ 相对路径(asset 引用)
    asset_type: AssetRole = "background"
    domain_tags: list[str] = Field(default_factory=list)
    mood_tags: list[str] = Field(default_factory=list)
    color_tags: list[str] = Field(default_factory=list)
    best_slide_types: list[SlideType] = Field(default_factory=list)
    safe_area: Rect | None = None  # 文字应落在此区域内
    needs_overlay: bool = False
    overlay_opacity: float = 0.0


class AssetIndex(BaseModel):
    assets: list[AssetIndexEntry] = Field(default_factory=list)
