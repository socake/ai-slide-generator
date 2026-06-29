"""MockLLMProvider:确定性 LLM 桩 —— 不联网、可复现,离线驱动整条流程与测试。

用法:用 `responses` 预置一队 canned 响应(dict / JSON 串 / BaseModel 实例 / 文本),
provider 按调用顺序取用。结构化调用必须有预置(无法凭空造出合法内容)。
"""

from __future__ import annotations

from collections import deque
from typing import Any

from pydantic import BaseModel

from packages.llm.provider import LLMResponse, LLMUsage, ModelT, StructuredResponse


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class MockLLMProvider:
    model = "mock"

    def __init__(self, *, responses: list[Any] | None = None, latency_ms: float = 0.0) -> None:
        self._queue: deque[Any] = deque(responses or [])
        self._latency = latency_ms

    def _usage(self, prompt: str, output: str) -> LLMUsage:
        return LLMUsage(
            model=self.model,
            input_tokens=_approx_tokens(prompt),
            output_tokens=_approx_tokens(output),
            latency_ms=self._latency,
        )

    def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResponse:
        raw = self._queue.popleft() if self._queue else f"[mock] {user[:80]}"
        text = raw if isinstance(raw, str) else str(raw)
        return LLMResponse(text=text, usage=self._usage(system + user, text))

    def structured(
        self, system: str, user: str, schema: type[ModelT], *, max_tokens: int = 2048
    ) -> StructuredResponse[ModelT]:
        if not self._queue:
            raise ValueError("MockLLMProvider.structured 需要预置 canned 响应(responses=...)")
        raw = self._queue.popleft()
        value = self._coerce(raw, schema)
        return StructuredResponse(
            value=value, usage=self._usage(system + user, value.model_dump_json())
        )

    @staticmethod
    def _coerce(raw: Any, schema: type[ModelT]) -> ModelT:
        if isinstance(raw, schema):
            return raw
        if isinstance(raw, BaseModel):
            return schema.model_validate(raw.model_dump())
        if isinstance(raw, dict):
            return schema.model_validate(raw)
        if isinstance(raw, str):
            return schema.model_validate_json(raw)
        raise TypeError(f"不支持的 mock 响应类型: {type(raw)!r}")
