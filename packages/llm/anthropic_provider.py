"""Anthropic Claude 适配器。结构化输出走 tool-use(事前约束)。

client 懒加载:import/构造不联网;只有调用时才建连。默认不在自主循环里真实调用。
"""

from __future__ import annotations

import time
from typing import Any

from packages.llm.provider import LLMResponse, LLMUsage, ModelT, StructuredResponse


class AnthropicProvider:
    def __init__(
        self,
        model: str = "claude-3-5-haiku-latest",
        *,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            from anthropic import Anthropic  # 懒加载

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResponse:
        client = self._ensure_client()
        t0 = time.perf_counter()
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return LLMResponse(text=text, usage=self._usage(resp, latency_ms))

    def structured(
        self, system: str, user: str, schema: type[ModelT], *, max_tokens: int = 2048
    ) -> StructuredResponse[ModelT]:
        client = self._ensure_client()
        tool = {
            "name": "emit",
            "description": f"Return a {schema.__name__} object.",
            "input_schema": schema.model_json_schema(),
        }
        t0 = time.perf_counter()
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": "emit"},
            messages=[{"role": "user", "content": user}],
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        data = next(b.input for b in resp.content if getattr(b, "type", None) == "tool_use")
        return StructuredResponse(
            value=schema.model_validate(data), usage=self._usage(resp, latency_ms)
        )

    def _usage(self, resp: Any, latency_ms: float) -> LLMUsage:
        usage = resp.usage
        return LLMUsage(
            model=self.model,
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
            latency_ms=latency_ms,
        )
