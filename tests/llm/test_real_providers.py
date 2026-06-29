"""真实 provider 适配器单测:用假 client 替换懒加载,不联网地验证映射逻辑。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from packages.llm import openai_provider as openai_mod
from packages.llm.anthropic_provider import AnthropicProvider
from packages.llm.openai_provider import OpenAIProvider


class _Plan(BaseModel):
    title: str
    n: int


def _fake_openai(content: str, prompt_tokens: int = 10, completion_tokens: int = 20) -> object:
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: resp))
    )


def _fake_anthropic(
    *,
    texts: list[str] | None = None,
    tool_input: dict | None = None,
    input_tokens: int = 5,
    output_tokens: int = 15,
) -> object:
    content = [SimpleNamespace(type="text", text=t) for t in (texts or [])]
    if tool_input is not None:
        content.append(SimpleNamespace(type="tool_use", input=tool_input))
    resp = SimpleNamespace(
        content=content,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: resp))


def test_openai_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    p = OpenAIProvider("gpt-4o-mini")
    monkeypatch.setattr(p, "_ensure_client", lambda: _fake_openai("hello", 10, 20))
    r = p.complete("sys", "user")
    assert r.text == "hello"
    assert r.usage.model == "gpt-4o-mini"
    assert (r.usage.input_tokens, r.usage.output_tokens) == (10, 20)


def test_openai_structured(monkeypatch: pytest.MonkeyPatch) -> None:
    p = OpenAIProvider("gpt-4o-mini")
    monkeypatch.setattr(p, "_ensure_client", lambda: _fake_openai('{"title": "T", "n": 3}'))
    r = p.structured("sys", "user", _Plan)
    assert isinstance(r.value, _Plan)
    assert (r.value.title, r.value.n) == ("T", 3)


def test_anthropic_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    p = AnthropicProvider("claude-3-5-haiku-latest")
    monkeypatch.setattr(p, "_ensure_client", lambda: _fake_anthropic(texts=["foo", "bar"]))
    r = p.complete("sys", "user")
    assert r.text == "foobar"
    assert r.usage.input_tokens == 5


def test_anthropic_structured(monkeypatch: pytest.MonkeyPatch) -> None:
    p = AnthropicProvider("claude-3-5-haiku-latest")
    monkeypatch.setattr(
        p, "_ensure_client", lambda: _fake_anthropic(tool_input={"title": "X", "n": 7})
    )
    r = p.structured("sys", "user", _Plan)
    assert isinstance(r.value, _Plan)
    assert r.value.n == 7


def test_structured_stream_retry_jitter_then_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """C9:流式连续失败 → 退避带抖动(uniform[0,cap],封顶)→ 回落非流式;不增加重试次数。"""
    calls = {"stream": 0, "nonstream": 0}

    def _create(**kw):  # noqa: ANN003, ANN202
        if kw.get("stream"):
            calls["stream"] += 1
            raise RuntimeError("APIConnectionError: reset")
        calls["nonstream"] += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"title": "T", "n": 1}'))],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4),
        )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_create)))
    p = OpenAIProvider("gpt-4o-mini")
    monkeypatch.setattr(p, "_ensure_client", lambda: fake)

    sleeps: list[float] = []
    monkeypatch.setattr(openai_mod.time, "sleep", lambda s: sleeps.append(s))
    # 取抖动上界(确定化),便于断言"退避封顶 = base*2**attempt 与 CAP 取小"
    monkeypatch.setattr(openai_mod.random, "uniform", lambda lo, hi: hi)

    r = p.structured_stream("sys", "user", _Plan)
    assert isinstance(r.value, _Plan) and r.value.n == 1
    assert calls["stream"] == openai_mod._STREAM_RETRIES  # 重试次数未上调
    assert calls["nonstream"] == 1  # 耗尽后回落非流式
    # 两次流式之间睡一次,退避 = min(CAP, BASE*2**0) = BASE,且封顶不超 CAP
    assert sleeps == [min(openai_mod._RETRY_BACKOFF_CAP, openai_mod._RETRY_BACKOFF_BASE)]
    assert all(0.0 <= s <= openai_mod._RETRY_BACKOFF_CAP for s in sleeps)
