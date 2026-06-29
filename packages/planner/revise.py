"""单页改写(revise):离线确定性版本——按指令换页型/裁内容,保留 id/index/标题。

对齐「预览修改页」与 ARCHITECTURE 的 revise 一致性:只动该页,全局 theme/其它页
不变。真实 LLM 接入后,把本函数换成"定点 Compose"(只对该页发单页 prompt)。
"""

from __future__ import annotations

from packages.core import (
    AgendaSlide,
    BigIdeaSlide,
    CardsSlide,
    ClosingSlide,
    ComparisonSlide,
    CoverSlide,
    DataSlide,
    ProcessSlide,
    QuoteSlide,
    SectionSlide,
    SlideSpec,
    SummarySlide,
    TimelineSlide,
)
from packages.core.enums import SlideType
from packages.planner.fallback import slide_from_plan
from packages.planner.schemas import SlidePlan

# 指令关键词 → 目标页型(显式意图优先)
_TARGET_BY_KEYWORD: list[tuple[tuple[str, ...], SlideType]] = [
    (("对比", "compare"), "comparison"),
    (("数据", "指标", "data"), "data"),
    (("步骤", "流程", "process"), "process"),
    (("时间", "脉络", "timeline"), "timeline"),
    (("卡片", "要点", "card"), "cards"),
]
# 无明确意图时,内容页在此环上轮换到下一型
_ROTATION: list[SlideType] = [
    "cards",
    "comparison",
    "data",
    "process",
    "timeline",
    "big_idea",
    "summary",
]
_STRUCTURE: tuple[SlideType, ...] = ("cover", "section", "closing", "agenda", "quote")
_SIMPLIFY = ("简洁", "压缩", "精简", "简化")


def _extract_points(slide: SlideSpec) -> list[str]:
    """从任意页提取可复用的要点文本,供改写成其它页型。"""
    if isinstance(slide, CardsSlide):
        return [c.title for c in slide.cards]
    if isinstance(slide, SummarySlide):
        return list(slide.points)
    if isinstance(slide, AgendaSlide):
        return list(slide.items)
    if isinstance(slide, ProcessSlide):
        return [s.title for s in slide.steps]
    if isinstance(slide, TimelineSlide):
        return [e.title for e in slide.events]
    if isinstance(slide, ComparisonSlide):
        return [*slide.left.points, *slide.right.points]
    if isinstance(slide, DataSlide):
        return [m.label for m in slide.metrics]
    if isinstance(slide, BigIdeaSlide):
        return [p for p in (slide.statement, slide.support) if p]
    if isinstance(slide, CoverSlide | SectionSlide | ClosingSlide):
        return [slide.subtitle] if slide.subtitle else [slide.title]
    if isinstance(slide, QuoteSlide):
        return [slide.quote]
    return [slide.title]


def _target_type(slide: SlideSpec, instruction: str) -> SlideType:
    text = instruction.lower()
    for keys, target in _TARGET_BY_KEYWORD:
        if any(k in text for k in keys):
            return target
    if slide.type in _STRUCTURE or any(k in instruction for k in _SIMPLIFY):
        return slide.type  # 结构页不换型;"简洁"只裁内容
    if slide.type in _ROTATION:
        return _ROTATION[(_ROTATION.index(slide.type) + 1) % len(_ROTATION)]
    return "cards"


def revise_offline(slide: SlideSpec, instruction: str = "") -> SlideSpec:
    """离线确定性单页改写,保留 id/index/标题。"""
    points = _extract_points(slide)
    if any(k in instruction for k in _SIMPLIFY):
        points = points[:2] or points
    target = _target_type(slide, instruction)
    plan = SlidePlan(
        type=target, title=slide.title, key_points=points or [slide.title], section_id=0
    )
    revised = slide_from_plan(plan, slide.index)
    revised.id = slide.id
    revised.index = slide.index
    return revised
