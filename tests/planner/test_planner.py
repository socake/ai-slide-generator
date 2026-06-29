from __future__ import annotations

from packages.benchmark import BenchmarkCollector
from packages.core import Card, CardsSlide, ClosingSlide, CoverSlide, SectionSlide
from packages.core.narrative import NarrativeSpec
from packages.llm import MockLLMProvider
from packages.planner import (
    ComposedSection,
    DeckOutline,
    DeckSpecValidator,
    GenerationInput,
    Planner,
    SectionPlan,
    SlidePlan,
)

INPUT = GenerationInput(topic="Python 入门", brief="讲清变量/循环/函数", audience="零基础")


def test_full_offline_fallback_yields_valid_deck() -> None:
    # 空 Mock:plan/compose 的 structured 都会抛 → 全程确定性兜底(离线路径)
    planner = Planner(MockLLMProvider())
    collector = BenchmarkCollector("offline")
    deck = planner.generate(INPUT, collector=collector)

    assert 25 <= len(deck.slides) <= 30
    assert deck.slides[0].type == "cover"
    assert deck.slides[-1].type == "closing"
    assert deck.id == planner.generate(INPUT).id  # 确定性 id
    assert DeckSpecValidator().validate(deck) == []
    # 全部失败 → 没有成功的 LLM 调用被记账
    assert collector.report(slide_count=len(deck.slides)).llm_calls == []


def test_canned_llm_path_records_calls() -> None:
    outline = DeckOutline(
        title="Python 入门",
        deck_type="teaching",
        purpose="教学",
        narrative=NarrativeSpec(hook="h", conflict="c", progression=["S1"], resolution="r"),
        sections=[SectionPlan(id=1, heading="S1")],
        # 喂满 25 页,使「页数不足补章」不触发,专注测调用记账(plan+compose)。
        slides=[
            SlidePlan(type="cards", title=f"要点{i}", key_points=["a", "b"], section_id=1)
            for i in range(25)
        ],
    )
    composed = ComposedSection(
        slides=[
            CoverSlide(id="c", index=0, title="封面"),
            SectionSlide(id="s", index=1, title="S1", section_number=1),
            CardsSlide(
                id="k",
                index=2,
                title="要点",
                cards=[Card(title="a", body=""), Card(title="b", body="")],
            ),
            ClosingSlide(id="e", index=3, title="", cta="谢谢"),
        ]
    )
    provider = MockLLMProvider(responses=[outline, composed])
    collector = BenchmarkCollector("canned")
    deck = Planner(provider).generate(INPUT, collector=collector)

    # validator 不再塞占位页凑 25-30(去"待补充"垃圾后),canned 只喂 4 页就是 4 页
    assert deck.slides[0].type == "cover"
    assert deck.slides[-1].type == "closing"
    report = collector.report(slide_count=len(deck.slides))
    assert len(report.llm_calls) == 2
    assert {c.step for c in report.llm_calls} == {"plan", "compose"}


def test_short_plan_triggers_expansion() -> None:
    # 首版大纲不足 25 页 → 带「还差几页」反馈补章,取更长者(真实内容,非占位)。
    from packages.planner.plan import run_plan

    def _outline(n: int) -> DeckOutline:
        return DeckOutline(
            title="T",
            deck_type="teaching",
            purpose="p",
            narrative=NarrativeSpec(hook="h", conflict="c", progression=["S1"], resolution="r"),
            sections=[SectionPlan(id=1, heading="S1")],
            slides=[
                SlidePlan(type="cards", title=f"P{i}", key_points=["a", "b"], section_id=1)
                for i in range(n)
            ],
        )

    short, full = _outline(10), _outline(26)
    provider = MockLLMProvider(responses=[short, full])
    collector = BenchmarkCollector("expand")
    outline = run_plan(provider, INPUT, collector=collector)

    assert len(outline.slides) >= 25  # 补章后达标
    # plan 首调 + 1 次补章 = 2 次记账(都记为 plan 步)
    assert [c.step for c in collector.report(slide_count=26).llm_calls] == ["plan", "plan"]
