"""模型定价表 + 成本计算(USD / 1M tokens)。

数值为指示性整理(按各家公开价),仅用于成本对比与 benchmark;真实计费以厂商为准。
未知模型按 0 计(如 mock),不阻塞流程。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_1m: float
    output_per_1m: float


PRICING: dict[str, ModelPricing] = {
    "mock": ModelPricing(0.0, 0.0),
    "gpt-4o-mini": ModelPricing(0.15, 0.60),
    "deepseek-chat": ModelPricing(0.27, 1.10),
    "claude-3-5-haiku-latest": ModelPricing(0.80, 4.00),
    "claude-3-5-sonnet-latest": ModelPricing(3.00, 15.00),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """按 token 数算美元成本;未知模型返回 0.0。"""
    p = PRICING.get(model)
    if p is None:
        return 0.0
    return input_tokens / 1_000_000 * p.input_per_1m + output_tokens / 1_000_000 * p.output_per_1m
