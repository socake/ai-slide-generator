"""LayoutSpec + SlotSpec:打通"内容 → 槽位 → 坐标"(见 DATA_MODEL §4)。

布局是 slide_type 的版式定义:一组命名槽位,每个槽位有归一化位置 + 渲染约束。
slot_mapper 把 typed content 字段塞进同名槽位,renderer 把槽位画出来。
"""

from __future__ import annotations

from pydantic import BaseModel

from packages.core.enums import Align, ColorRole, FontRole, SlideType, SlotKind, VAlign
from packages.core.geometry import Rect


class SlotSpec(BaseModel):
    name: str  # 约定命名,见 DATA_MODEL §4.1
    kind: SlotKind
    rect: Rect  # 归一化位置
    font_role: FontRole | None = None
    color_role: ColorRole = "text"
    align: Align = "left"
    valign: VAlign = "top"
    max_lines: int | None = None  # 超出触发缩字号/截断
    z: int = 0  # 叠放次序(背景图在底层)


class LayoutSpec(BaseModel):
    id: str
    slide_type: SlideType
    name: str
    slots: dict[str, SlotSpec]  # key == SlotSpec.name
    repeat_slot: str | None = None  # 可重复槽位前缀(如 "card_"),供动态展开
