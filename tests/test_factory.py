from __future__ import annotations

import pytest

from packages.llm import LLMProvider, MockLLMProvider, make_provider
from packages.llm.anthropic_provider import AnthropicProvider
from packages.llm.openai_provider import OpenAIProvider


def test_make_mock_satisfies_protocol() -> None:
    p = make_provider("mock")
    assert isinstance(p, MockLLMProvider)
    assert isinstance(p, LLMProvider)


def test_make_real_constructs_without_network() -> None:
    # 只构造(懒加载 client),不联网
    assert isinstance(make_provider("openai", "gpt-4o-mini"), OpenAIProvider)
    assert isinstance(make_provider("deepseek"), OpenAIProvider)
    assert isinstance(make_provider("anthropic"), AnthropicProvider)


def test_unknown_provider_raises() -> None:
    with pytest.raises(ValueError, match="未知 provider"):
        make_provider("nope")
