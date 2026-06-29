"""GenerationResult:统一生成产物(见 DATA_MODEL §6)。

一次生成 = 一个 GenerationResult,落地位置由调用方决定(如写文件系统)。
内核只产出本对象,字节如何落盘由调用方处理。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from packages.core.benchmark_models import BenchmarkReport
from packages.core.deck import DeckSpec


class GenerationResult(BaseModel):
    deck_spec: DeckSpec
    pptx_bytes: bytes | None = None
    pdf_bytes: bytes | None = None
    preview_png: list[bytes] = Field(default_factory=list)
    benchmark: BenchmarkReport
