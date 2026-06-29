from __future__ import annotations

from pathlib import Path

import pytest

from packages.asset_engine.loader import load_index
from packages.asset_engine.models import AssetIndex
from packages.layout_engine.loader import load_layouts
from packages.planner._defaults import neutral_theme
from packages.theme_engine.loader import load_themes

_REPO = Path(__file__).resolve().parents[1]


def test_load_themes_skips_bad_file(tmp_path: Path) -> None:
    (tmp_path / "good.json").write_text(neutral_theme().model_dump_json(), encoding="utf-8")
    (tmp_path / "bad.json").write_text("{ not valid json", encoding="utf-8")
    with pytest.warns(UserWarning):
        themes = load_themes(tmp_path)
    assert set(themes) == {"good"}  # 坏文件跳过,好的照常加载


def test_load_layouts_skips_bad_file(tmp_path: Path) -> None:
    good = (_REPO / "templates" / "layouts" / "quote.json").read_text(encoding="utf-8")
    (tmp_path / "quote.json").write_text(good, encoding="utf-8")
    (tmp_path / "broken.json").write_text("{ oops", encoding="utf-8")
    with pytest.warns(UserWarning):
        layouts = load_layouts(tmp_path)
    assert set(layouts) == {"quote"}


def test_load_index_missing_returns_empty(tmp_path: Path) -> None:
    with pytest.warns(UserWarning):
        idx = load_index(tmp_path / "nope.json")
    assert isinstance(idx, AssetIndex)  # 缺文件 → 空索引,不崩
