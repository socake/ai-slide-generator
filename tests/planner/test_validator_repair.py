from __future__ import annotations

from packages.core import (
    Card,
    CardsSlide,
    ClosingSlide,
    ComparisonColumn,
    ComparisonSlide,
    CoverSlide,
    DataSlide,
    DeckSpec,
    NarrativeSpec,
    SectionSlide,
    SlideSpec,
    SummarySlide,
)
from packages.planner import DeckSpecValidator
from packages.planner._defaults import neutral_theme


def _deck(slides: list[SlideSpec]) -> DeckSpec:
    return DeckSpec(
        id="d", title="标题", topic="t", brief="b", audience="a", purpose="p",
        deck_type="generic",
        narrative=NarrativeSpec(hook="h", conflict="c", progression=["x"], resolution="r"),
        theme=neutral_theme(),
        slides=slides,
    )


def test_repair_normalizes_short_deck_without_padding() -> None:
    slides: list[SlideSpec] = [
        CoverSlide(id="c", index=0, title="封面"),
        SectionSlide(id="s", index=1, title="章", section_number=1),
        ClosingSlide(id="z", index=2, title="", cta="谢谢"),
    ]
    fixed = DeckSpecValidator().repair(_deck(slides))
    n = len(fixed.slides)
    assert n == 3  # 不塞占位页凑数(去"待补充"垃圾);页数不足靠 plan 解决
    assert fixed.slides[0].type == "cover"
    assert fixed.slides[-1].type == "closing"
    assert [s.index for s in fixed.slides] == list(range(n))
    assert [s.id for s in fixed.slides] == [f"slide-{i}" for i in range(n)]
    codes = {i.code for i in DeckSpecValidator().validate(fixed)}
    assert {"cover", "closing", "index"} & codes == set()  # 结构修好;page_count 允许


def test_repair_clamps_long_deck_to_max() -> None:
    # 上限为 MAX_SLIDES(60);超过才裁,保留首封面/尾结束页。
    mid: list[SlideSpec] = [
        SectionSlide(id=f"s{i}", index=i, title=f"章{i}", section_number=i) for i in range(70)
    ]
    slides = [CoverSlide(id="c", index=0, title="封面"), *mid, ClosingSlide(id="z", index=0, title="", cta="t")]
    fixed = DeckSpecValidator().repair(_deck(slides))
    assert len(fixed.slides) == 60
    assert fixed.slides[0].type == "cover"
    assert fixed.slides[-1].type == "closing"


def test_repair_fixes_card_count() -> None:
    cards = CardsSlide(id="x", index=1, title="卡片", cards=[Card(title="A", body="a")])
    slides: list[SlideSpec] = [
        CoverSlide(id="c", index=0, title="封面"), cards, ClosingSlide(id="z", index=2, title="", cta="t")
    ]
    fixed = DeckSpecValidator().repair(_deck(slides))
    cards_slides = [s for s in fixed.slides if isinstance(s, CardsSlide)]
    assert cards_slides
    assert all(2 <= len(s.cards) <= 4 for s in cards_slides)


def test_validate_reports_structural_problems() -> None:
    slides: list[SlideSpec] = [
        SummarySlide(id="a", index=0, title="总结", points=["p"]),
        ClosingSlide(id="z", index=1, title="", cta="t"),
    ]
    codes = {i.code for i in DeckSpecValidator().validate(_deck(slides))}
    assert "page_count" in codes  # 2 页 < 25
    assert "cover" in codes  # 无 cover
    assert "section" in codes  # 无 section


def test_validate_reports_count_and_empty_title() -> None:
    bad = CardsSlide(id="x", index=1, title="", cards=[Card(title="A", body="a")])  # 1 张 + 空标题
    slides: list[SlideSpec] = [
        CoverSlide(id="c", index=0, title="封面"), bad, ClosingSlide(id="z", index=2, title="", cta="t")
    ]
    codes = {i.code for i in DeckSpecValidator().validate(_deck(slides))}
    assert "count" in codes  # cards 1 < 2
    assert "title" in codes  # cards 空标题(非 quote/closing)


def test_repair_fills_empty_comparison_and_data() -> None:
    comp = ComparisonSlide(
        id="c1", index=1, title="对比",
        left=ComparisonColumn(heading="L", points=[]),
        right=ComparisonColumn(heading="R", points=[]),
    )
    data = DataSlide(id="d1", index=2, title="数据", metrics=[])
    slides: list[SlideSpec] = [
        CoverSlide(id="c", index=0, title="封面"), comp, data, ClosingSlide(id="z", index=3, title="", cta="t")
    ]
    fixed = DeckSpecValidator().repair(_deck(slides))
    comps = [s for s in fixed.slides if isinstance(s, ComparisonSlide)]
    datas = [s for s in fixed.slides if isinstance(s, DataSlide)]
    assert comps and all(s.left.points and s.right.points for s in comps)  # 空列补 "—"
    assert datas and all(s.metrics for s in datas)  # 空 metrics 补占位
