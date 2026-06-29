from __future__ import annotations

from packages.theme_engine import ThemeEngine, load_themes
from packages.theme_engine.engine import DEFAULT_THEMES_DIR


def test_new_presets_load_and_valid() -> None:
    themes = load_themes(DEFAULT_THEMES_DIR)
    for stem in ("tech_dark", "pitch_bold", "travel_warm", "review_warm"):
        assert stem in themes
        assert themes[stem].id == stem


def test_review_uses_dedicated_warm_theme() -> None:
    assert ThemeEngine().select("review").id == "review_warm"


def test_deck_type_maps_to_variant() -> None:
    engine = ThemeEngine()
    assert engine.select("tech").id == "tech_dark"
    assert engine.select("pitch").id == "pitch_bold"
    assert engine.select("travel").id == "travel_warm"
