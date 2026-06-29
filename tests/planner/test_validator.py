from __future__ import annotations

from packages.core import (
    Card,
    CardsSlide,
    DeckSpec,
    NarrativeSpec,
    SectionSlide,
)
from packages.planner._defaults import neutral_theme
from packages.planner.validator import DeckSpecValidator


def _deck(slides: list) -> DeckSpec:
    return DeckSpec(
        id="d",
        title="T",
        topic="t",
        brief="b",
        audience="a",
        purpose="p",
        deck_type="generic",
        narrative=NarrativeSpec(hook="h", conflict="c", progression=["x"], resolution="r"),
        theme=neutral_theme(),
        slides=slides,
    )


def test_validate_flags_problems() -> None:
    bad = _deck([SectionSlide(id="s", index=5, title="S", section_number=1)])
    codes = {i.code for i in DeckSpecValidator().validate(bad)}
    assert {"page_count", "cover", "closing", "index"} <= codes


def test_repair_produces_valid_deck() -> None:
    bad = _deck([SectionSlide(id="s", index=5, title="S", section_number=1)])
    repaired = DeckSpecValidator().repair(bad)
    assert len(repaired.slides) <= 30
    assert repaired.slides[0].type == "cover"
    assert repaired.slides[-1].type == "closing"
    assert [s.index for s in repaired.slides] == list(range(len(repaired.slides)))
    # 结构性问题全修好;页数不足只剩 page_count(不再塞垃圾补齐)
    assert {i.code for i in DeckSpecValidator().validate(repaired)} <= {"page_count"}


def test_repair_clamps_typed_counts() -> None:
    one_card = CardsSlide(id="c", index=1, title="卡片", cards=[Card(title="只有一个", body="")])
    deck = _deck([SectionSlide(id="s", index=0, title="S", section_number=1), one_card])
    repaired = DeckSpecValidator().repair(deck)
    cards = [s for s in repaired.slides if s.type == "cards"]
    assert cards and 2 <= len(cards[0].cards) <= 4  # type: ignore[union-attr]
