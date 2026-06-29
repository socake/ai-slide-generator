"""归一化几何。规格层只用 Rect;EMU 只在 renderer 末端出现(见 docs/DATA_MODEL §0)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Rect(BaseModel):
    """相对画布的归一化矩形,各分量 ∈ [0,1]。画布固定 16:9。"""

    left: float = Field(ge=0.0, le=1.0)
    top: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)
