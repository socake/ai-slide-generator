from __future__ import annotations

from packages.core.enums import SlideType
from packages.planner.fallback import ensure_len, slide_from_plan
from packages.planner.schemas import SlidePlan

ALL_TYPES: list[SlideType] = [
    "cover",
    "agenda",
    "section",
    "big_idea",
    "cards",
    "timeline",
    "comparison",
    "process",
    "data",
    "quote",
    "summary",
    "closing",
]


def test_ensure_len_pads_and_truncates() -> None:
    assert ensure_len([1, 2], 3, 5, lambda i: 0) == [1, 2, 0]
    assert ensure_len([1, 2, 3, 4, 5, 6], 1, 3, lambda i: 0) == [1, 2, 3]


def test_slide_from_plan_every_type_valid() -> None:
    for i, t in enumerate(ALL_TYPES):
        plan = SlidePlan(type=t, title=f"标题{t}", key_points=["甲", "乙", "丙"], section_id=1)
        slide = slide_from_plan(plan, i)
        assert slide.type == t
        assert slide.index == i


def test_fallback_respects_count_bounds() -> None:
    cards = slide_from_plan(SlidePlan(type="cards", title="c", key_points=["a"], section_id=1), 0)
    assert 2 <= len(cards.cards) <= 4  # type: ignore[union-attr]
    timeline = slide_from_plan(
        SlidePlan(type="timeline", title="t", key_points=[], section_id=1), 1
    )
    assert 3 <= len(timeline.events) <= 6  # type: ignore[union-attr]
    process = slide_from_plan(
        SlidePlan(type="process", title="p", key_points=["x"], section_id=1), 2
    )
    assert 3 <= len(process.steps) <= 5  # type: ignore[union-attr]
