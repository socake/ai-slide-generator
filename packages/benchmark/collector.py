"""BenchmarkCollector:累计一次生成的 LLM 调用与耗时,产出 BenchmarkReport。

`clock` 可注入(默认 perf_counter)以便测试确定性。成本用 packages.llm.pricing 计算。
"""

from __future__ import annotations

import time
from collections.abc import Callable

from packages.core import BenchmarkReport, LLMCall
from packages.core.enums import LLMStep
from packages.llm.pricing import cost_usd
from packages.llm.provider import LLMUsage


class BenchmarkCollector:
    def __init__(self, deck_id: str, *, clock: Callable[[], float] = time.perf_counter) -> None:
        self.deck_id = deck_id
        self._clock = clock
        self._t0 = clock()
        self._calls: list[LLMCall] = []

    def record(self, step: LLMStep, usage: LLMUsage) -> LLMCall:
        """记一次 LLM 调用(算好成本),返回该条记录。"""
        call = LLMCall(
            step=step,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=cost_usd(usage.model, usage.input_tokens, usage.output_tokens),
            latency_ms=usage.latency_ms,
        )
        self._calls.append(call)
        return call

    def report(
        self, *, slide_count: int, render_ms: float = 0.0, degraded: bool = False
    ) -> BenchmarkReport:
        """收口:聚合总成本/总延迟/墙钟,产出报告。"""
        wall_clock_ms = (self._clock() - self._t0) * 1000
        return BenchmarkReport(
            deck_id=self.deck_id,
            slide_count=slide_count,
            llm_calls=list(self._calls),
            total_cost_usd=sum(c.cost_usd for c in self._calls),
            total_llm_latency_ms=sum(c.latency_ms for c in self._calls),
            wall_clock_ms=wall_clock_ms,
            render_ms=render_ms,
            degraded=degraded,
        )
