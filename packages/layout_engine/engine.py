"""LayoutEngine:按 slide_type 选布局预设,**不调 LLM**。

可变数量内容(cards/timeline…)用 repeat_slot + slot_mapper 的网格逻辑展开,
不为每个数量写死模板。坐标全归一化,EMU 只在 renderer 末端。
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from packages.core import LayoutSpec, Rect, SlotSpec
from packages.core.enums import SlideType
from packages.layout_engine.loader import load_layouts

DEFAULT_LAYOUTS_DIR = Path(__file__).resolve().parents[2] / "templates" / "layouts"

# 模板 preset 的抽象版式名(presets.json 的 layout 值)→ 真实 layout JSON 的 id(==文件名 stem)。
# 仅列「非主布局」的变体;其余名字(如 cover:left_aligned / cards:grid_3 / data:metric_row /
# section:left_number / agenda:numbered_list …)→ 解析为 None,回落该 SlideType 的主布局
# (id==slide_type)。这样模板里写默认变体名也等价于「不覆盖」,只有真正的变体才换 JSON。
_PRESET_VARIANT_ALIASES: dict[tuple[str, str], str] = {
    ("cover", "centered"): "cover_centered",
    ("cards", "grid_2"): "cards_2up",
    ("data", "big_number"): "data_big_number",
}


def _fallback_layout(slide_type: SlideType) -> LayoutSpec:
    """无对应布局时的兜底:仅一个标题槽。"""
    return LayoutSpec(
        id=f"{slide_type}_fallback",
        slide_type=slide_type,
        name="Fallback",
        slots={
            "title": SlotSpec(
                name="title",
                kind="text",
                rect=Rect(left=0.06, top=0.08, width=0.88, height=0.14),
                font_role="h1",
            )
        },
    )


class LayoutEngine:
    def __init__(self, layouts_dir: Path | None = None) -> None:
        layouts = load_layouts(layouts_dir or DEFAULT_LAYOUTS_DIR)
        self._by_id: dict[str, LayoutSpec] = dict(layouts)  # stem(==id) → 布局
        self._by_type: dict[str, list[LayoutSpec]] = {}  # slide_type → 多布局(主 + 变体)
        for layout in layouts.values():
            self._by_type.setdefault(layout.slide_type, []).append(layout)

    def select(
        self, slide_type: SlideType, content_count: int = 0, variant: str | None = None
    ) -> LayoutSpec:
        """选布局:variant 名优先;否则取该 type 的主布局(id==slide_type),按 content_count 选变体;缺失回落兜底。"""
        if variant is not None and variant in self._by_id:
            return self._by_id[variant]
        candidates = self._by_type.get(slide_type)
        if not candidates:
            return _fallback_layout(slide_type)
        if slide_type == "cards" and 0 < content_count <= 2 and "cards_2up" in self._by_id:
            return self._by_id["cards_2up"]
        return next((lay for lay in candidates if lay.id == slide_type), candidates[0])

    def resolve_override(
        self, slide_type: SlideType, layout_overrides: Mapping[str, str] | None
    ) -> tuple[str | None, bool]:
        """模板 layout 映射对该页型的版式选择 →(真实 layout id 或 None=主布局, 是否由模板显式指定)。

        模板显式指定即优先(即便落到主布局,也据此抑制 deck_type 启发式);未指定则交回兜底。
        变体名经 _PRESET_VARIANT_ALIASES 解析到真实 layout id;默认/未知名 → None。
        """
        if layout_overrides and slide_type in layout_overrides:
            return _PRESET_VARIANT_ALIASES.get((slide_type, layout_overrides[slide_type])), True
        return None, False

    def pick(
        self,
        slide_type: SlideType,
        *,
        content_count: int = 0,
        layout_overrides: Mapping[str, str] | None = None,
        default_variant: str | None = None,
    ) -> LayoutSpec:
        """按「模板版式映射 → deck_type 兜底 → 主布局」三级选布局,实现「换模板换版式变体」。

        layout_overrides(选定模板 preset 的 layout)优先,覆盖 deck_type 默认;模板未指定该
        页型 → 回落 default_variant(调用方按 deck_type 给的启发式变体,如正式封面居中);
        再无 → 该 SlideType 主布局 / 按 content_count 的变体(见 select)。
        """
        variant, by_template = self.resolve_override(slide_type, layout_overrides)
        if not by_template:
            variant = default_variant
        return self.select(slide_type, content_count, variant)
