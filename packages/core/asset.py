"""AssetSpec:素材绑定 + 安全区(见 DATA_MODEL §5)。

renderer 必须读 safe_area 收窄文字槽位、按 needs_overlay 叠遮罩 —— 这是"图上有字
也清楚"的保证。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from packages.core.enums import AssetRole
from packages.core.geometry import Rect


class AssetBinding(BaseModel):
    slide_id: str
    role: AssetRole
    object_key: str  # assets/ 相对路径(asset 引用)
    safe_area: Rect | None = None  # 文字应落在此区域内
    needs_overlay: bool = False  # 是否压半透明遮罩以保证对比度
    overlay_opacity: float = 0.0


class AssetSpec(BaseModel):
    bindings: list[AssetBinding] = Field(default_factory=list)
