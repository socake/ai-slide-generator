from __future__ import annotations

from packages.layout_engine import LayoutEngine, load_layouts
from packages.layout_engine.engine import DEFAULT_LAYOUTS_DIR


def test_variants_loaded_under_same_type() -> None:
    layouts = load_layouts(DEFAULT_LAYOUTS_DIR)
    assert "cover_centered" in layouts
    assert layouts["cover_centered"].slide_type == "cover"
    assert layouts["cards_2up"].slide_type == "cards"


def test_select_default_is_main_layout() -> None:
    engine = LayoutEngine()
    assert engine.select("cover").id == "cover"  # 默认主布局,非变体
    assert engine.select("cards").id == "cards"


def test_select_variant_by_name() -> None:
    engine = LayoutEngine()
    assert engine.select("cover", variant="cover_centered").id == "cover_centered"
    # 未知变体名 → 回默认
    assert engine.select("cover", variant="does_not_exist").id == "cover"


def test_select_cards_two_up_by_count() -> None:
    engine = LayoutEngine()
    assert engine.select("cards", content_count=2).id == "cards_2up"
    assert engine.select("cards", content_count=4).id == "cards"  # 多卡用默认网格
