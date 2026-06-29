"""SlideSpec —— 按 `type` 的可辨识联合(discriminated union),见 DATA_MODEL §2。

渲染器拿到的是强类型数据,不靠 `if type==...` 猜内容。判别字段 `type` 只声明在各
具体子类上(Literal),公共字段放 `SlideBase`;这样既是单一判别,又避免基类字段被
窄化覆盖带来的类型噪声。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from packages.core.enums import Emphasis


class SlideBase(BaseModel):
    """所有幻灯片共有字段(不含判别字段 `type`)。"""

    id: str
    index: int  # 0-based 顺序
    title: str  # 顶部标题(closing/quote 可空串)
    speaker_notes: str | None = None
    layout_id: str | None = None  # 显式布局,否则 LayoutEngine 按 type 选默认
    asset_hint: str | None = None  # 给 AssetEngine 的检索提示
    emphasis: Emphasis = "normal"  # 影响留白/字号


# ── 可重复内容子模型 ─────────────────────────────────────────────
class Card(BaseModel):
    title: str
    body: str
    icon: str | None = None  # 语义图标名,AssetEngine 解析


class TimelineEvent(BaseModel):
    time: str
    title: str
    desc: str | None = None


class ComparisonColumn(BaseModel):
    heading: str
    points: list[str]


class ProcessStep(BaseModel):
    title: str
    desc: str | None = None


class Metric(BaseModel):
    value: str  # "78%" / "3.2x" / "¥1.2M"
    label: str
    delta: str | None = None  # "+12%" 同比/环比


# ── 12 种 typed slide ────────────────────────────────────────────
class CoverSlide(SlideBase):
    type: Literal["cover"] = "cover"
    subtitle: str | None = None
    kicker: str | None = None  # 标题上方小字(主题/日期/作者)


class AgendaSlide(SlideBase):
    type: Literal["agenda"] = "agenda"
    items: list[str]  # 通常等于各 section 标题


class SectionSlide(SlideBase):
    type: Literal["section"] = "section"
    section_number: int
    subtitle: str | None = None


class BigIdeaSlide(SlideBase):
    type: Literal["big_idea"] = "big_idea"
    statement: str  # 一句大字主张
    support: str | None = None  # 一行支撑


class CardsSlide(SlideBase):
    type: Literal["cards"] = "cards"
    cards: list[Card]  # 2-4 张,LayoutEngine 按数量选列数


class TimelineSlide(SlideBase):
    type: Literal["timeline"] = "timeline"
    events: list[TimelineEvent]  # 3-6 个节点


class ComparisonSlide(SlideBase):
    type: Literal["comparison"] = "comparison"
    left: ComparisonColumn
    right: ComparisonColumn


class ProcessSlide(SlideBase):
    type: Literal["process"] = "process"
    steps: list[ProcessStep]  # 3-5 步


class DataSlide(SlideBase):
    type: Literal["data"] = "data"
    metrics: list[Metric]  # 数字卡;图表是后续扩展
    note: str | None = None


class QuoteSlide(SlideBase):
    type: Literal["quote"] = "quote"
    quote: str
    attribution: str | None = None


class SummarySlide(SlideBase):
    type: Literal["summary"] = "summary"
    points: list[str]


class ClosingSlide(SlideBase):
    type: Literal["closing"] = "closing"
    subtitle: str | None = None
    cta: str | None = None  # 行动号召/联系方式


# 可辨识联合:按 `type` 判别。list[SlideSpec] 由 pydantic 逐项判别解析。
SlideSpec = Annotated[
    CoverSlide
    | AgendaSlide
    | SectionSlide
    | BigIdeaSlide
    | CardsSlide
    | TimelineSlide
    | ComparisonSlide
    | ProcessSlide
    | DataSlide
    | QuoteSlide
    | SummarySlide
    | ClosingSlide,
    Field(discriminator="type"),
]
