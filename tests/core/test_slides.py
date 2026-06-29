from __future__ import annotations

from pydantic import TypeAdapter

from packages.core import (
    AgendaSlide,
    BigIdeaSlide,
    Card,
    CardsSlide,
    ClosingSlide,
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

_adapter: TypeAdapter[object] = TypeAdapter(SlideSpec)


def test_construct_all_twelve_types() -> None:
    slides = [
        CoverSlide(id="s", index=0, title="t", subtitle="x", kicker="k"),
        AgendaSlide(id="s", index=1, title="t", items=["a", "b"]),
        SectionSlide(id="s", index=2, title="t", section_number=1),
        BigIdeaSlide(id="s", index=3, title="t", statement="big"),
        CardsSlide(id="s", index=4, title="t", cards=[Card(title="c", body="b")]),
        TimelineSlide(id="s", index=5, title="t", events=[TimelineEvent(time="2024", title="e")]),
        ComparisonSlide(
            id="s",
            index=6,
            title="t",
            left=ComparisonColumn(heading="L", points=["1"]),
            right=ComparisonColumn(heading="R", points=["2"]),
        ),
        ProcessSlide(id="s", index=7, title="t", steps=[ProcessStep(title="p1")]),
        DataSlide(id="s", index=8, title="t", metrics=[Metric(value="78%", label="x")]),
        QuoteSlide(id="s", index=9, title="", quote="q"),
        SummarySlide(id="s", index=10, title="t", points=["a"]),
        ClosingSlide(id="s", index=11, title="", cta="bye"),
    ]
    assert len(slides) == 12
    assert {s.type for s in slides} == {
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
    }


def test_union_discriminates_by_type() -> None:
    cover = _adapter.validate_python(
        {"id": "s1", "index": 0, "type": "cover", "title": "T", "subtitle": "sub"}
    )
    assert isinstance(cover, CoverSlide)
    assert cover.subtitle == "sub"

    cards = _adapter.validate_python(
        {
            "id": "s2",
            "index": 1,
            "type": "cards",
            "title": "T",
            "cards": [{"title": "a", "body": "b"}],
        }
    )
    assert isinstance(cards, CardsSlide)
    assert cards.cards[0].title == "a"


def test_defaults_applied() -> None:
    s = SectionSlide(id="x", index=0, title="t", section_number=2)
    assert s.emphasis == "normal"
    assert s.speaker_notes is None
