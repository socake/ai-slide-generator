"""packages.llm —— LLM provider 抽象与适配器。LLM 只在 Plan/Compose 使用。

内核依赖 `LLMProvider` 协议而非具体厂商;`MockLLMProvider` 让全流程离线可测。
"""

from __future__ import annotations

from packages.llm.anthropic_provider import AnthropicProvider
from packages.llm.factory import make_provider
from packages.llm.mock import MockLLMProvider
from packages.llm.openai_provider import OpenAIProvider
from packages.llm.pricing import PRICING, ModelPricing, cost_usd
from packages.llm.provider import (
    LLMProvider,
    LLMResponse,
    LLMUsage,
    StructuredResponse,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMUsage",
    "StructuredResponse",
    "MockLLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "make_provider",
    "PRICING",
    "ModelPricing",
    "cost_usd",
]
