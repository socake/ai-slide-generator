"""packages.core —— 领域模型地基。以 docs/DATA_MODEL.md 为准。

下游统一从这里导入:`from packages.core import DeckSpec, SlideSpec, ThemeSpec, ...`。
"""

from __future__ import annotations

from packages.core.asset import AssetBinding, AssetSpec
from packages.core.benchmark_models import BenchmarkReport, LLMCall
from packages.core.deck import DeckSpec
from packages.core.enums import (
    Align,
    AssetRole,
    BackgroundStyle,
    ColorRole,
    DeckType,
    Emphasis,
    FontRole,
    FooterStyle,
    LLMStep,
    ShapeStyle,
    SlideType,
    SlotKind,
    VAlign,
)
from packages.core.geometry import Rect
from packages.core.layout import LayoutSpec, SlotSpec
from packages.core.narrative import NarrativeSpec
from packages.core.result import GenerationResult
from packages.core.slides import (
    AgendaSlide,
    BigIdeaSlide,
    Card,
    CardsSlide,
    ClosingSlide,
    ComparisonColumn,
    ComparisonSlide,
    CoverSlide,
    DataSlide,
    Metric,
    ProcessSlide,
    ProcessStep,
    QuoteSlide,
    SectionSlide,
    SlideBase,
    SlideSpec,
    SummarySlide,
    TimelineEvent,
    TimelineSlide,
)
from packages.core.theme import Fonts, Grid, Palette, Spacing, ThemeSpec, TypeScale

__all__ = [
    # geometry
    "Rect",
    # enums
    "DeckType",
    "SlideType",
    "SlotKind",
    "Emphasis",
    "FontRole",
    "ColorRole",
    "Align",
    "VAlign",
    "ShapeStyle",
    "BackgroundStyle",
    "FooterStyle",
    "AssetRole",
    "LLMStep",
    # narrative
    "NarrativeSpec",
    # slides
    "SlideBase",
    "SlideSpec",
    "Card",
    "TimelineEvent",
    "ComparisonColumn",
    "ProcessStep",
    "Metric",
    "CoverSlide",
    "AgendaSlide",
    "SectionSlide",
    "BigIdeaSlide",
    "CardsSlide",
    "TimelineSlide",
    "ComparisonSlide",
    "ProcessSlide",
    "DataSlide",
    "QuoteSlide",
    "SummarySlide",
    "ClosingSlide",
    # theme
    "Palette",
    "TypeScale",
    "Fonts",
    "Spacing",
    "Grid",
    "ThemeSpec",
    # layout
    "SlotSpec",
    "LayoutSpec",
    # asset
    "AssetBinding",
    "AssetSpec",
    # benchmark
    "LLMCall",
    "BenchmarkReport",
    # deck / result
    "DeckSpec",
    "GenerationResult",
]
