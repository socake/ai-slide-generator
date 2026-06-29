from __future__ import annotations

from pathlib import Path

import pytest

from packages.asset_engine import AssetEngine, AssetIndexEntry, load_index
from packages.asset_engine.engine import DEFAULT_INDEX_PATH
from packages.core import (
    CardsSlide,
    CoverSlide,
    DeckSpec,
    Fonts,
    NarrativeSpec,
    Palette,
    SectionSlide,
    SlideSpec,
    ThemeSpec,
)
from packages.theme_engine import ThemeEngine


def _theme(mood: list[str]) -> ThemeSpec:
    return ThemeSpec(
        id="t",
        name="t",
        mood=mood,
        palette=Palette(
            primary="#1",
            secondary="#2",
            accent="#3",
            background="#4",
            surface="#5",
            text="#6",
            text_muted="#7",
            border="#8",
        ),
        fonts=Fonts(heading="A", body="B"),
    )


def _deck(
    theme: ThemeSpec, slides: list[SlideSpec], topic: str = "话题", deck_type: str = "generic"
) -> DeckSpec:
    return DeckSpec(
        id="d",
        title="T",
        topic=topic,
        brief="b",
        audience="a",
        purpose="p",
        deck_type=deck_type,
        narrative=NarrativeSpec(hook="h", conflict="c", progression=["x"], resolution="r"),
        theme=theme,
        slides=slides,
    )


def test_index_loads_backgrounds() -> None:
    index = load_index(DEFAULT_INDEX_PATH)
    assert len(index.assets) >= 4
    assert all(isinstance(a, AssetIndexEntry) for a in index.assets)
    assert any(a.asset_type == "background" for a in index.assets)


def test_loader_bad_file_returns_empty(tmp_path: Path) -> None:
    bad = tmp_path / "asset_index.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.warns(UserWarning):
        index = load_index(bad)
    assert index.assets == []


def test_binds_cover_and_section_by_mood() -> None:
    theme = ThemeEngine().select("teaching")  # mood: clean/friendly/approachable
    slides: list[SlideSpec] = [
        CoverSlide(id="c", index=0, title="封面"),
        SectionSlide(id="s", index=1, title="第一章", section_number=1),
        CardsSlide(id="k", index=2, title="卡片", cards=[]),  # 无 asset_hint → 不绑
    ]
    spec = AssetEngine().bind(_deck(theme, slides))
    bound_ids = {b.slide_id: b for b in spec.bindings}
    assert "c" in bound_ids and "s" in bound_ids
    assert "k" not in bound_ids
    assert bound_ids["c"].object_key == "backgrounds/clean_blue.jpg"
    assert bound_ids["c"].role == "background"
    assert bound_ids["c"].safe_area is not None


def test_no_thematic_match_no_binding() -> None:
    theme = _theme(["zzz_unmatched"])
    slides: list[SlideSpec] = [CoverSlide(id="c", index=0, title="封面")]
    spec = AssetEngine().bind(_deck(theme, slides, topic="qqqq"))
    assert spec.bindings == []  # 无情绪/提示关联 → 安全回退纯色


def test_asset_hint_triggers_binding() -> None:
    theme = _theme(["neutral"])
    card = CardsSlide(id="k", index=0, title="卡片", cards=[], asset_hint="python tech blue")
    spec = AssetEngine().bind(_deck(theme, [card]))
    assert any(b.slide_id == "k" for b in spec.bindings)
