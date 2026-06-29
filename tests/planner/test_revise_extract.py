"""revise_offline 从各种起始页型提取要点(_extract_points 全分支)。"""

from __future__ import annotations

import pytest

from packages.core import (
    AgendaSlide,
    BigIdeaSlide,
    ComparisonColumn,
    ComparisonSlide,
    CoverSlide,
    DataSlide,
    Metric,
    ProcessSlide,
    ProcessStep,
    QuoteSlide,
    SectionSlide,
    SlideSpec,
    SummarySlide,
    TimelineEvent,
    TimelineSlide,
)
from packages.planner.revise import revise_offline

_STARTS: list[SlideSpec] = [
    SummarySlide(id="a", index=2, title="总结", points=["p1", "p2"]),
    AgendaSlide(id="a", index=2, title="目录", items=["i1", "i2"]),
    ProcessSlide(
        id="a", index=2, title="流程",
        steps=[ProcessStep(title="s1"), ProcessStep(title="s2"), ProcessStep(title="s3")],
    ),
    TimelineSlide(
        id="a", index=2, title="时间线",
        events=[TimelineEvent(time="Q1", title="e1"), TimelineEvent(time="Q2", title="e2"),
                TimelineEvent(time="Q3", title="e3")],
    ),
    ComparisonSlide(
        id="a", index=2, title="对比",
        left=ComparisonColumn(heading="L", points=["l"]),
        right=ComparisonColumn(heading="R", points=["r"]),
    ),
    DataSlide(id="a", index=2, title="数据", metrics=[Metric(value="1", label="m1"), Metric(value="2", label="m2")]),
    BigIdeaSlide(id="a", index=2, title="主张", statement="少即是多", support="支撑"),
    CoverSlide(id="a", index=2, title="封面", subtitle="副标题"),
    SectionSlide(id="a", index=2, title="章节", section_number=1, subtitle="小标"),
    QuoteSlide(id="a", index=2, title="金句", quote="名言一句"),
]


@pytest.mark.parametrize("start", _STARTS, ids=lambda s: s.type)
def test_revise_extracts_from_any_type(start: SlideSpec) -> None:
    out = revise_offline(start, "换成卡片")  # 统一目标,走各起始型的 _extract_points 分支
    assert out.id == "a"
    assert out.index == 2
    assert out.type == "cards"  # "卡片" 关键词命中
