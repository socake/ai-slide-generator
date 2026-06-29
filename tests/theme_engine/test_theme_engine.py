from __future__ import annotations

from pathlib import Path

import pytest

from packages.core import ThemeSpec
from packages.theme_engine import ThemeEngine, load_themes
from packages.theme_engine.engine import DEFAULT_THEMES_DIR

PRESETS = {"teaching", "exec_report", "consumer", "generic"}


def test_all_shipped_presets_are_valid() -> None:
    themes = load_themes(DEFAULT_THEMES_DIR)
    assert set(themes) >= PRESETS
    for stem, theme in themes.items():
        assert isinstance(theme, ThemeSpec)
        assert theme.id == stem  # 文件名 stem 与 preset id 一致


def test_loader_skips_bad_files(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{ not valid json", encoding="utf-8")
    (tmp_path / "empty.json").write_text("{}", encoding="utf-8")  # 缺必填 → 校验失败
    with pytest.warns(UserWarning):
        themes = load_themes(tmp_path)
    assert themes == {}


def test_select_maps_deck_type_to_preset() -> None:
    engine = ThemeEngine()
    assert engine.select("teaching").id == "teaching"
    assert engine.select("tech").id == "tech_dark"
    assert engine.select("pitch").id == "pitch_bold"
    assert engine.select("consumer").id == "consumer"
    assert engine.select("review").id == "review_warm"


def test_unknown_deck_type_falls_back_to_generic() -> None:
    assert ThemeEngine().select("does_not_exist").id == "generic"


def test_audience_hint_forces_exec_theme() -> None:
    engine = ThemeEngine()
    assert engine.select("teaching", audience="面向高管董事会").id == "exec_report"
    assert engine.select("teaching", audience="general public").id == "teaching"


def test_select_returns_independent_copy() -> None:
    engine = ThemeEngine()
    a = engine.select("teaching")
    a.palette.primary = "#000000"
    b = engine.select("teaching")
    assert b.palette.primary != "#000000"  # 改副本不污染缓存
