from __future__ import annotations

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
    DeckSpec,
    Fonts,
    Metric,
    NarrativeSpec,
    Palette,
    ProcessSlide,
    ProcessStep,
    QuoteSlide,
    SectionSlide,
    SlideSpec,
    SummarySlide,
    ThemeSpec,
    TimelineEvent,
    TimelineSlide,
)


def _theme() -> ThemeSpec:
    return ThemeSpec(
        id="teaching_clean",
        name="Teaching Clean",
        mood=["clean", "friendly"],
        palette=Palette(
            primary="#2563eb",
            secondary="#1e40af",
            accent="#f59e0b",
            background="#ffffff",
            surface="#f8fafc",
            text="#0f172a",
            text_muted="#64748b",
            border="#e2e8f0",
        ),
        fonts=Fonts(heading="Inter", body="Inter"),
    )


def _make_slides() -> list[SlideSpec]:
    slides: list[SlideSpec] = [
        CoverSlide(id="c0", index=0, title="封面", subtitle="副标题", kicker="2026"),
        AgendaSlide(id="a1", index=1, title="目录", items=["一", "二", "三"]),
    ]
    idx = 2
    for sec in range(1, 4):
        slides.append(
            SectionSlide(id=f"sec{sec}", index=idx, title=f"第{sec}章", section_number=sec)
        )
        idx += 1
        slides.append(BigIdeaSlide(id=f"big{sec}", index=idx, title="主张", statement="一句话"))
        idx += 1
        slides.append(
            CardsSlide(
                id=f"card{sec}",
                index=idx,
                title="卡片",
                cards=[Card(title="A", body="a"), Card(title="B", body="b")],
            )
        )
        idx += 1
        slides.append(
            TimelineSlide(
                id=f"tl{sec}",
                index=idx,
                title="时间轴",
                events=[TimelineEvent(time="Q1", title="e1"), TimelineEvent(time="Q2", title="e2")],
            )
        )
        idx += 1
        slides.append(
            ComparisonSlide(
                id=f"cmp{sec}",
                index=idx,
                title="对比",
                left=ComparisonColumn(heading="旧", points=["x"]),
                right=ComparisonColumn(heading="新", points=["y"]),
            )
        )
        idx += 1
        slides.append(
            ProcessSlide(
                id=f"proc{sec}",
                index=idx,
                title="流程",
                steps=[ProcessStep(title="s1"), ProcessStep(title="s2")],
            )
        )
        idx += 1
        slides.append(
            DataSlide(
                id=f"data{sec}",
                index=idx,
                title="数据",
                metrics=[Metric(value="78%", label="覆盖"), Metric(value="3.2x", label="提速")],
            )
        )
        idx += 1
    slides.append(QuoteSlide(id="q", index=idx, title="", quote="引用"))
    idx += 1
    slides.append(SummarySlide(id="sum", index=idx, title="小结", points=["a", "b"]))
    idx += 1
    slides.append(ClosingSlide(id="end", index=idx, title="", cta="谢谢"))
    return slides


def _make_deck() -> DeckSpec:
    return DeckSpec(
        id="deck-1",
        title="演示稿",
        topic="主题",
        brief="简介",
        audience="受众",
        purpose="teaching",
        deck_type="teaching",
        narrative=NarrativeSpec(
            hook="钩子", conflict="问题", progression=["一", "二", "三"], resolution="行动"
        ),
        theme=_theme(),
        slides=_make_slides(),
    )


def test_deck_has_expected_slide_count() -> None:
    deck = _make_deck()
    assert 25 <= len(deck.slides) <= 30


def test_deck_json_roundtrip_preserves_union_subtypes() -> None:
    deck = _make_deck()
    payload = deck.model_dump_json()
    restored = DeckSpec.model_validate_json(payload)
    assert restored == deck
    # 判别联合在反序列化后仍还原为具体子类
    assert isinstance(restored.slides[0], CoverSlide)
    assert isinstance(restored.slides[-1], ClosingSlide)
    assert any(isinstance(s, CardsSlide) for s in restored.slides)
