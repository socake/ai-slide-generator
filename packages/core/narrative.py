"""叙事线:保证产出是"一套"而非"一堆"(见 DATA_MODEL §1.2)。"""

from __future__ import annotations

from pydantic import BaseModel


class NarrativeSpec(BaseModel):
    """开头—展开—收尾的内在线索。`progression` 长度 ≈ 章节数。"""

    hook: str  # 开场钩子
    conflict: str  # 张力/问题
    progression: list[str]  # 章节推进,每项对应一个 section 主旨
    resolution: str  # 收束/行动
