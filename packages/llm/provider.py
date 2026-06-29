"""LLMProvider 抽象:内核只依赖这个协议,不绑定具体厂商(见 docs/GENERATION_PIPELINE)。

LLM 只在 Plan/Compose 出现。Provider 返回内容 + 计量(usage),成本由 pricing 计算、
由 benchmark 聚合 —— provider 自身不关心成本与追踪。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class LLMUsage:
    """单次调用的计量。"""

    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float = 0.0


@dataclass(frozen=True)
class LLMResponse:
    text: str
    usage: LLMUsage


@dataclass(frozen=True)
class StructuredResponse(Generic[ModelT]):
    """结构化产出:已校验为目标 schema 的实例 + 计量。"""

    value: ModelT
    usage: LLMUsage


@runtime_checkable
class LLMProvider(Protocol):
    """所有适配器实现的统一协议。`structured` 是事前约束的结构化输出。"""

    model: str

    def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResponse: ...

    def structured(
        self, system: str, user: str, schema: type[ModelT], *, max_tokens: int = 2048
    ) -> StructuredResponse[ModelT]: ...


@runtime_checkable
class SupportsStructuredStream(Protocol):
    """**可选**能力:边生成边把累积文本回调给 on_delta(务实流式)。

    与 `LLMProvider` 解耦:只有真支持流式的 provider 才实现它(如 OpenAIProvider);
    Mock 等不实现也不影响 `LLMProvider` 一致性。调用方用 `isinstance(p, SupportsStructuredStream)`
    探测,没有就回落非流式 `structured`。
    """

    def structured_stream(
        self,
        system: str,
        user: str,
        schema: type[ModelT],
        *,
        max_tokens: int = 2048,
        on_delta: Callable[[str], None] | None = None,
    ) -> StructuredResponse[ModelT]: ...
