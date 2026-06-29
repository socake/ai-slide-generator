"""迭代59 代码审查确认的真实问题修复回归测试。"""

from __future__ import annotations

from packages.core import SectionSlide
from packages.layout_engine import LayoutEngine, map_slots
from packages.pipeline import generate
from packages.planner import GenerationInput


def test_deck_id_differs_for_same_topic_different_brief() -> None:
    a = generate(GenerationInput(topic="Python", brief="初级入门", audience="新手"), with_preview=False)
    b = generate(GenerationInput(topic="Python", brief="高级进阶", audience="专家"), with_preview=False)
    assert a.deck_spec.id != b.deck_spec.id  # 同 topic、不同 brief/audience 不撞 id


def test_deck_id_deterministic_for_same_input() -> None:
    inp = GenerationInput(topic="Rust", brief="所有权", audience="后端")
    assert generate(inp, with_preview=False).deck_spec.id == generate(inp, with_preview=False).deck_spec.id


def test_section_subtitle_now_renders() -> None:
    slide = SectionSlide(id="s", index=1, title="第一章", section_number=1, subtitle="开场说明")
    slots = map_slots(slide, LayoutEngine().select("section"))
    subs = [s for s in slots if s.name == "subtitle"]
    assert len(subs) == 1
    assert subs[0].value == "开场说明"
