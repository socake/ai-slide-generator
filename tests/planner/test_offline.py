from __future__ import annotations

from packages.planner import GenerationInput
from packages.planner.offline import brief_points, build_offline_outline


def test_brief_points_from_clauses() -> None:
    assert brief_points("变量、循环、函数、列表、字典", 3, seed="x") == ["变量", "循环", "函数"]


def test_brief_points_pads_when_short() -> None:
    pts = brief_points("只有一句", 3, seed="主题")
    assert len(pts) == 3
    assert pts[0] == "只有一句"


def test_offline_outline_topic_aware_and_varied() -> None:
    inp = GenerationInput(
        topic="Python 入门 30 分钟", brief="变量、循环、函数、列表、字典", audience="零基础"
    )
    outline = build_offline_outline(inp, "teaching")
    assert outline.deck_type == "teaching"
    assert 25 <= len(outline.slides) <= 30
    assert outline.sections[0].heading == "背景与目标"  # 用 teaching 模板
    all_points = [p for s in outline.slides for p in s.key_points]
    assert any("变量" in p for p in all_points)  # 内容含 brief 派生词
    types = {s.type for s in outline.slides}
    assert len(types & {"cards", "comparison", "data", "process", "timeline", "big_idea"}) >= 4


def test_offline_is_deterministic() -> None:
    inp = GenerationInput(topic="同主题", brief="一,二,三", audience="受众")
    a = build_offline_outline(inp, "generic")
    b = build_offline_outline(inp, "generic")
    assert a.model_dump() == b.model_dump()
