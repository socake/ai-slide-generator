"""预制图标解析(resolve_icon)+ slot_mapper 图标槽与回退。

图标库由 scripts/build_icons.py 产出;库存在时解析真实图标 PNG,否则/无命中时回退徽章。
"""

from __future__ import annotations

from pathlib import Path

from packages.asset_engine import AssetEngine
from packages.asset_engine.engine import DEFAULT_INDEX_PATH
from packages.core import Card, CardsSlide, ProcessSlide, ProcessStep
from packages.layout_engine import LayoutEngine, map_slots

_ICON_DIR = DEFAULT_INDEX_PATH.parent / "icons" / "lucide"
_LIB_BUILT = (_ICON_DIR / "manifest.json").exists()


def test_resolve_icon_english_keyword() -> None:
    ae = AssetEngine()
    key = ae.resolve_icon("growth", "#ffffff")
    if not _LIB_BUILT:
        assert key is None  # 未构建图标库 → 安全 None
        return
    assert key == "icons/lucide/trending-up__ffffff.png"
    assert (DEFAULT_INDEX_PATH.parent / key).exists()


def test_resolve_icon_chinese_substring() -> None:
    ae = AssetEngine()
    key = ae.resolve_icon("数据安全防护体系", "#ffffff")
    if not _LIB_BUILT:
        assert key is None
        return
    # 中文整段 token 走别名子串:命中「安全」→ shield(长别名优先于「数据」更靠后无所谓,取首个出现)
    assert key is not None and key.startswith("icons/lucide/")
    assert (DEFAULT_INDEX_PATH.parent / key).exists()


def test_resolve_icon_unbuilt_color_returns_none() -> None:
    ae = AssetEngine()
    # 未预制的颜色 → None(渲染回退徽章)
    assert ae.resolve_icon("growth", "#abcdef") is None


def test_resolve_icon_no_match_returns_none() -> None:
    ae = AssetEngine()
    assert ae.resolve_icon("qqzzxx", "#ffffff") is None


def _cards_layout():  # noqa: ANN202
    le = LayoutEngine()
    slide = CardsSlide(
        id="k", index=0, title="标题",
        cards=[Card(title="用户增长", body="用户增长很重要", icon="growth")],
    )
    return slide, le.select("cards", 1)


def test_slot_mapper_emits_icon_when_resolver_hits() -> None:
    slide, layout = _cards_layout()
    slots = map_slots(slide, layout, lambda kw, role: "icons/lucide/trending-up__ffffff.png")
    image_slots = [s for s in slots if s.kind == "image"]
    assert len(image_slots) == 1
    assert image_slots[0].value == "icons/lucide/trending-up__ffffff.png"
    # 命中图标时不再产编号/字形文字槽
    assert not any(s.name.endswith(".badgetext") for s in slots)


def test_slot_mapper_falls_back_to_badge_without_resolver() -> None:
    slide, layout = _cards_layout()
    slots = map_slots(slide, layout)  # 无 resolver
    assert not any(s.kind == "image" for s in slots)
    assert any(s.name.endswith(".badgetext") for s in slots)


def test_slot_mapper_falls_back_when_resolver_misses() -> None:
    slide, layout = _cards_layout()
    slots = map_slots(slide, layout, lambda kw, role: None)  # resolver 恒 None
    assert not any(s.kind == "image" for s in slots)
    assert any(s.name.endswith(".badgetext") for s in slots)


def test_process_step_icon_and_number_fallback() -> None:
    le = LayoutEngine()
    slide = ProcessSlide(
        id="p", index=0, title="流程",
        steps=[ProcessStep(title="数据采集"), ProcessStep(title="执行落地")],
    )
    layout = le.select("process", 0)

    def resolver(kw: str, role: str) -> str | None:
        return "icons/lucide/database__000000.png" if "数据" in kw else None

    slots = map_slots(slide, layout, resolver)
    assert any(s.kind == "image" and s.name == "step_0.icon" for s in slots)
    # 第二步无命中 → 保留序号
    assert any(s.name == "step_1.num" for s in slots)
    assert not any(s.name == "step_0.num" for s in slots)


def test_path_helper_smoke(tmp_path: Path) -> None:
    # AssetEngine 指向无图标库的目录 → resolve 恒 None,不抛异常
    (tmp_path / "asset_index.json").write_text('{"assets": []}', encoding="utf-8")
    ae = AssetEngine(tmp_path / "asset_index.json")
    assert ae.resolve_icon("growth", "#ffffff") is None
