from __future__ import annotations

from pathlib import Path

from packages.asset_engine import AssetEngine
from packages.asset_engine.models import AssetIndex, AssetIndexEntry
from packages.core import CoverSlide, DeckSpec, NarrativeSpec
from packages.planner._defaults import neutral_theme


def _index(tmp_path: Path) -> Path:
    idx = AssetIndex(
        assets=[
            AssetIndexEntry(object_key="weak.jpg", mood_tags=["warm"]),
            AssetIndexEntry(object_key="strong.jpg", mood_tags=["warm", "calm", "bright"]),
        ]
    )
    p = tmp_path / "index.json"
    p.write_text(idx.model_dump_json(), encoding="utf-8")
    return p


def _deck_with_mood(mood: list[str]) -> DeckSpec:
    theme = neutral_theme().model_copy(update={"mood": mood})
    return DeckSpec(
        id="d", title="T", topic="主题", brief="b", audience="a", purpose="p",
        deck_type="generic",
        narrative=NarrativeSpec(hook="h", conflict="c", progression=["x"], resolution="r"),
        theme=theme,
        slides=[CoverSlide(id="cov", index=0, title="封面")],
    )


def test_bind_picks_highest_mood_overlap(tmp_path: Path) -> None:
    spec = AssetEngine(_index(tmp_path)).bind(_deck_with_mood(["warm", "calm", "bright"]))
    assert len(spec.bindings) == 1
    assert spec.bindings[0].object_key == "strong.jpg"  # 交集 3 胜过 1
    assert spec.bindings[0].slide_id == "cov"


def test_bind_empty_when_no_overlap(tmp_path: Path) -> None:
    spec = AssetEngine(_index(tmp_path)).bind(_deck_with_mood(["cyber", "neon"]))
    assert spec.bindings == []  # 无任何交集 → 不强绑
