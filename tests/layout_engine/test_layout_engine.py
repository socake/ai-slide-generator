from __future__ import annotations

from pathlib import Path

from packages.core import (
    AgendaSlide,
    Card,
    CardsSlide,
    ComparisonColumn,
    ComparisonSlide,
    CoverSlide,
    DataSlide,
    Metric,
    ProcessSlide,
    ProcessStep,
    Rect,
    TimelineEvent,
    TimelineSlide,
)
from packages.core.enums import SlideType
from packages.layout_engine import LayoutEngine, grid_rects, load_layouts, map_slots, row_rects
from packages.layout_engine.engine import DEFAULT_LAYOUTS_DIR

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


def test_all_shipped_layouts_valid_and_cover_every_type() -> None:
    layouts = load_layouts(DEFAULT_LAYOUTS_DIR)
    assert len(layouts) >= 12  # 12 主布局 + 变体
    covered = {lt.slide_type for lt in layouts.values()}
    assert covered == set(ALL_TYPES)
    for stem, layout in layouts.items():
        assert layout.id == stem


def test_select_returns_matching_type() -> None:
    engine = LayoutEngine()
    for t in ALL_TYPES:
        assert engine.select(t).slide_type == t


def test_select_falls_back_when_missing(tmp_path: Path) -> None:
    engine = LayoutEngine(layouts_dir=tmp_path)  # 空目录
    layout = engine.select("cards")
    assert layout.slide_type == "cards"
    assert "title" in layout.slots  # 兜底单标题布局


def _within_unit(r: Rect) -> bool:
    return (
        r.left >= 0.0 and r.top >= 0.0 and r.left + r.width <= 1.0001 and r.top + r.height <= 1.0001
    )


def test_row_rects_non_overlapping_within_region() -> None:
    region = Rect(left=0.06, top=0.3, width=0.88, height=0.4)
    rects = row_rects(region, 4)
    assert len(rects) == 4
    assert all(_within_unit(r) for r in rects)
    lefts = [r.left for r in rects]
    assert lefts == sorted(lefts)
    assert rects[0].left + rects[0].width <= rects[1].left + 1e-9


def test_grid_rects_two_rows_for_four_items() -> None:
    region = Rect(left=0.06, top=0.26, width=0.88, height=0.6)
    rects = grid_rects(region, 4, cols=2)
    assert len(rects) == 4
    assert all(_within_unit(r) for r in rects)
    assert rects[2].top > rects[0].top  # 第二行更低


def test_map_slots_fixed_cover() -> None:
    slide = CoverSlide(id="c", index=0, title="标题", subtitle="副标题", kicker="2026")
    slots = {s.name: s for s in map_slots(slide, LayoutEngine().select("cover"))}
    assert slots["title"].value == "标题"
    assert slots["subtitle"].value == "副标题"
    assert slots["kicker"].value == "2026"


def test_map_slots_list_and_comparison() -> None:
    engine = LayoutEngine()
    agenda = AgendaSlide(id="a", index=0, title="目录", items=["一", "二", "三"])
    aslots = {s.name: s for s in map_slots(agenda, engine.select("agenda"))}
    # items 展开为「卡片行 + 徽章 + 文本」(替代裸 bullet);每条文本进 row_{i}.text
    assert aslots["title"].value == "目录"
    row_texts = [aslots[f"row_{i}.text"].value for i in range(3)]
    assert row_texts == ["一", "二", "三"]
    assert all(f"row_{i}.bg" in aslots and f"row_{i}.badge" in aslots for i in range(3))

    cmp = ComparisonSlide(
        id="cm",
        index=0,
        title="对比",
        left=ComparisonColumn(heading="旧", points=["a"]),
        right=ComparisonColumn(heading="新", points=["b", "c"]),
    )
    cslots = {s.name: s for s in map_slots(cmp, engine.select("comparison"))}
    assert cslots["left.points"].value == ["a"]
    assert cslots["right.points"].value == ["b", "c"]


def test_map_slots_repeat_expansion() -> None:
    engine = LayoutEngine()
    cards = CardsSlide(
        id="k",
        index=0,
        title="卡片",
        cards=[Card(title=f"C{i}", body="b") for i in range(3)],
    )
    names = {s.name for s in map_slots(cards, engine.select("cards"))}
    assert {"title", "card_0.title", "card_0.body", "card_2.title", "card_2.body"} <= names
    assert all(_within_unit(s.rect) for s in map_slots(cards, engine.select("cards")))

    timeline = TimelineSlide(
        id="t",
        index=0,
        title="轴",
        events=[TimelineEvent(time=str(i), title=f"E{i}") for i in range(3)],
    )
    tnames = {s.name for s in map_slots(timeline, engine.select("timeline"))}
    assert {"event_0.time", "event_2.title"} <= tnames

    process = ProcessSlide(
        id="p", index=0, title="流程", steps=[ProcessStep(title=f"S{i}") for i in range(3)]
    )
    assert any(s.name == "step_0.title" for s in map_slots(process, engine.select("process")))

    data = DataSlide(
        id="d",
        index=0,
        title="数据",
        metrics=[Metric(value="78%", label="覆盖", delta="+5%"), Metric(value="3x", label="提速")],
    )
    dslots = {s.name: s for s in map_slots(data, engine.select("data"))}
    assert "metric_0.value" in dslots
    assert "(+5%)" in dslots["metric_0.value"].value  # delta 拼进数值
