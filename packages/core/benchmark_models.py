"""benchmark 的纯领域模型(见 docs/GENERATION_PIPELINE §7)。

这里只放数据模型;采集器(LLM 调用追踪、成本计算)逻辑在 packages/benchmark,
后者 import 这些模型。放在 core 是为了 GenerationResult 可引用且无循环依赖。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from packages.core.enums import LLMStep


class LLMCall(BaseModel):
    """单次 LLM 调用的计量记录。"""

    step: LLMStep
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


class BenchmarkReport(BaseModel):
    """一次生成的成本/延迟报告。`generation_traces` 的聚合视图。"""

    deck_id: str
    slide_count: int = 0
    llm_calls: list[LLMCall] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    total_llm_latency_ms: float = 0.0  # 顺序调用之和
    wall_clock_ms: float = 0.0  # 端到端(含并行收益)
    render_ms: float = 0.0
    degraded: bool = False  # 是否触发降级(超时/重试耗尽)

    @classmethod
    def empty(cls, deck_id: str) -> BenchmarkReport:
        """生成开始时的空报告占位。"""
        return cls(deck_id=deck_id, slide_count=0)
