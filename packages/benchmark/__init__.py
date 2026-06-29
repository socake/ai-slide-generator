"""packages.benchmark —— 成本/延迟采集。被动追踪每次 LLM 调用,聚合成 BenchmarkReport。

数据模型(LLMCall/BenchmarkReport)在 packages.core;此处只放采集器逻辑。
"""

from __future__ import annotations

from packages.benchmark.collector import BenchmarkCollector
from packages.benchmark.quality import QualityReport, evaluate_quality

__all__ = ["BenchmarkCollector", "QualityReport", "evaluate_quality"]
