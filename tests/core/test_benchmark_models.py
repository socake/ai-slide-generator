from __future__ import annotations

from packages.core import BenchmarkReport, LLMCall


def test_llm_call() -> None:
    call = LLMCall(
        step="plan",
        model="mock",
        input_tokens=100,
        output_tokens=200,
        cost_usd=0.001,
        latency_ms=320.0,
    )
    assert call.step == "plan"
    assert call.output_tokens == 200


def test_benchmark_empty_factory() -> None:
    report = BenchmarkReport.empty("deck-1")
    assert report.deck_id == "deck-1"
    assert report.slide_count == 0
    assert report.llm_calls == []
    assert report.degraded is False


def test_benchmark_aggregation_fields() -> None:
    report = BenchmarkReport(
        deck_id="d",
        slide_count=26,
        llm_calls=[
            LLMCall(
                step="compose",
                model="mock",
                input_tokens=1,
                output_tokens=1,
                cost_usd=0.5,
                latency_ms=10.0,
            )
        ],
        total_cost_usd=0.5,
    )
    assert report.slide_count == 26
    assert len(report.llm_calls) == 1
