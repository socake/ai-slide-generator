from __future__ import annotations

import pytest
from pydantic import BaseModel

from packages.llm import LLMProvider, MockLLMProvider


class _Plan(BaseModel):
    title: str
    sections: list[str]


def test_mock_satisfies_protocol() -> None:
    assert isinstance(MockLLMProvider(), LLMProvider)


def test_complete_is_deterministic() -> None:
    p = MockLLMProvider()
    a = p.complete("sys", "hello world")
    b = MockLLMProvider().complete("sys", "hello world")
    assert a.text == b.text
    assert a.usage.model == "mock"
    assert a.usage.input_tokens > 0


def test_complete_consumes_queue_in_order() -> None:
    p = MockLLMProvider(responses=["one", "two"])
    assert p.complete("s", "u").text == "one"
    assert p.complete("s", "u").text == "two"
    # 队列空后回落到确定性默认值
    assert p.complete("s", "u").text.startswith("[mock]")


def test_structured_coerces_dict_json_and_model() -> None:
    payload = {"title": "T", "sections": ["a", "b"]}
    p = MockLLMProvider(
        responses=[payload, '{"title":"J","sections":["x"]}', _Plan(title="M", sections=[])]
    )
    r1 = p.structured("s", "u", _Plan)
    assert isinstance(r1.value, _Plan)
    assert r1.value.title == "T"
    assert p.structured("s", "u", _Plan).value.title == "J"
    assert p.structured("s", "u", _Plan).value.title == "M"


def test_structured_requires_canned() -> None:
    with pytest.raises(ValueError, match="canned"):
        MockLLMProvider().structured("s", "u", _Plan)
