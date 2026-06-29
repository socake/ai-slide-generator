from __future__ import annotations

import pytest

from packages.planner import GenerationInput
from packages.planner.offline import brief_points, build_offline_outline

_INPUT = GenerationInput(
    topic="远程协作", brief="第一点很重要。第二点也关键；第三点补充,第四点收尾。", audience="团队"
)


@pytest.mark.parametrize("deck_type", ["teaching", "exec_report", "pitch", "consumer", "generic"])
def test_offline_outline_shape(deck_type: str) -> None:
    outline = build_offline_outline(_INPUT, deck_type)  # type: ignore[arg-type]
    assert 25 <= len(outline.slides) <= 30
    assert outline.slides[0].type == "cover"
    assert outline.slides[-1].type == "closing"
    types = {s.type for s in outline.slides}
    assert "agenda" in types
    assert "summary" in types
    assert outline.deck_type == deck_type
    assert len(outline.sections) >= 1


def test_offline_is_deterministic() -> None:
    a = build_offline_outline(_INPUT, "teaching")  # type: ignore[arg-type]
    b = build_offline_outline(_INPUT, "teaching")  # type: ignore[arg-type]
    assert a.model_dump() == b.model_dump()


def test_brief_points_splits_and_counts() -> None:
    pts = brief_points("甲很好。乙也行；丙凑数,丁结尾。", 3)
    assert len(pts) == 3
    assert all(p for p in pts)
