"""packages.planner —— LLM 只在此出现(Plan/Compose)。

两段式编排 + 确定性兜底 + 结构校验修复,产出合法 DeckSpec。下游 Theme/Layout/Asset/
Render 全是确定性程序。
"""

from __future__ import annotations

from packages.planner.compose import run_compose
from packages.planner.fallback import slide_from_plan
from packages.planner.plan import fallback_outline, run_plan
from packages.planner.planner import Planner
from packages.planner.schemas import (
    ComposedSection,
    DeckOutline,
    GenerationInput,
    SectionPlan,
    SlidePlan,
)
from packages.planner.validator import DeckSpecValidator, ValidationIssue

__all__ = [
    "Planner",
    "DeckSpecValidator",
    "ValidationIssue",
    "GenerationInput",
    "DeckOutline",
    "ComposedSection",
    "SectionPlan",
    "SlidePlan",
    "run_plan",
    "run_compose",
    "fallback_outline",
    "slide_from_plan",
]
