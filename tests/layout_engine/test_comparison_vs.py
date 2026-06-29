from __future__ import annotations

from packages.core import ComparisonColumn, ComparisonSlide
from packages.layout_engine import LayoutEngine, map_slots


def test_comparison_emits_vs_divider() -> None:
    slide = ComparisonSlide(
        id="c", index=0, title="自研 vs 采购",
        left=ComparisonColumn(heading="自研", points=["可控"]),
        right=ComparisonColumn(heading="采购", points=["快"]),
    )
    slots = map_slots(slide, LayoutEngine().select("comparison"))
    vs = [s for s in slots if s.name == "vs"]
    assert len(vs) == 1
    assert vs[0].value == "VS"
    assert vs[0].color_role == "accent"
