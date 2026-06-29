"""packages.layout_engine —— 规则化选布局 + 槽位映射(零 LLM)。预设见 templates/layouts/*.json。"""

from __future__ import annotations

from packages.layout_engine.engine import LayoutEngine
from packages.layout_engine.loader import load_layouts
from packages.layout_engine.slot_mapper import RenderSlot, grid_rects, map_slots, row_rects

__all__ = ["LayoutEngine", "load_layouts", "map_slots", "RenderSlot", "row_rects", "grid_rects"]
