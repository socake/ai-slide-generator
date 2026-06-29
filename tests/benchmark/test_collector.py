from __future__ import annotations

from collections.abc import Callable

from packages.benchmark import BenchmarkCollector
from packages.llm.provider import LLMUsage
from packages.pipeline import generate
from packages.planner import GenerationInput


def _fake_clock(values: list[float]) -> Callable[[], float]:
    it = iter(values)
    return lambda: next(it)


def test_record_and_report_aggregates() -> None:
    # clock: 第一次取 t0=1.0, report 时取 2.5 → wall = 1500ms
    collector = BenchmarkCollector("deck-1", clock=_fake_clock([1.0, 2.5]))
    collector.record("plan", LLMUsage("gpt-4o-mini", 1_000_000, 0, latency_ms=300.0))
    collector.record("compose", LLMUsage("gpt-4o-mini", 0, 1_000_000, latency_ms=700.0))
    report = collector.report(slide_count=26, render_ms=120.0)

    assert report.deck_id == "deck-1"
    assert report.slide_count == 26
    assert len(report.llm_calls) == 2
    # 成本: 0.15(input 1M) + 0.60(output 1M)
    assert abs(report.total_cost_usd - 0.75) < 1e-9
    assert report.total_llm_latency_ms == 1000.0
    assert report.wall_clock_ms == 1500.0
    assert report.render_ms == 120.0
    assert report.degraded is False


def test_empty_report() -> None:
    report = BenchmarkCollector("d", clock=_fake_clock([0.0, 0.0])).report(slide_count=0)
    assert report.total_cost_usd == 0.0
    assert report.llm_calls == []


def test_mock_pipeline_benchmark_is_free() -> None:
    res = generate(
        GenerationInput(topic="主题", brief="简介", audience="受众"), with_preview=False
    )
    assert res.benchmark.total_cost_usd == 0.0  # MockLLMProvider 零成本
    assert res.benchmark.slide_count == len(res.deck_spec.slides)
