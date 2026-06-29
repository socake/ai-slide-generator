"""DeckSpec:系统核心中间产物(见 DATA_MODEL §1)。

可序列化为 deck_spec.json 持久化。含 schema_version 以支持演进。
"""

from __future__ import annotations

from pydantic import BaseModel

from packages.core.enums import DeckType
from packages.core.narrative import NarrativeSpec
from packages.core.slides import SlideSpec
from packages.core.theme import ThemeSpec


class DeckSpec(BaseModel):
    schema_version: str = "1.0"  # 演进必备,见 DATA_MODEL §7
    id: str
    title: str
    topic: str
    brief: str
    audience: str
    purpose: str  # IntentAnalyzer 推断的演示目的
    deck_type: DeckType  # 驱动主题与默认布局序列
    narrative: NarrativeSpec  # 整套叙事线
    theme: ThemeSpec  # 选定的视觉系统
    slides: list[SlideSpec]  # 25-30 张(数量等约束由 DeckSpecValidator 兜底)
