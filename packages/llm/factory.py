"""Provider 工厂:按名字构造 LLMProvider。

默认 `mock`(离线、零成本、可复现);真实 provider 懒加载,key 从环境变量读,只有真正调用
时才联网。DeepSeek/Qwen 走 OpenAI 兼容端点(换 base_url)。
"""

from __future__ import annotations

import os

from packages.llm.anthropic_provider import AnthropicProvider
from packages.llm.mock import MockLLMProvider
from packages.llm.openai_provider import OpenAIProvider
from packages.llm.provider import LLMProvider

_DEEPSEEK_BASE = "https://api.deepseek.com"


def make_provider(name: str = "mock", model: str | None = None) -> LLMProvider:
    """name ∈ {mock, openai, deepseek, anthropic};未知则 ValueError。"""
    key = name.lower()
    if key == "mock":
        return MockLLMProvider()
    if key == "openai":
        return OpenAIProvider(model or "gpt-4o-mini")
    if key == "deepseek":
        return OpenAIProvider(
            model or "deepseek-chat",
            api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", _DEEPSEEK_BASE),
        )
    if key == "anthropic":
        return AnthropicProvider(model or "claude-3-5-haiku-latest")
    raise ValueError(f"未知 provider: {name!r}（支持 mock/openai/deepseek/anthropic）")
