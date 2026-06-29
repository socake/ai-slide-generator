"""确定性兜底:把 SlidePlan 映射成合法 typed SlideSpec(graceful 降级 + 离线生成路径)。

Compose 失败时用本模块从 key_points 直接造内容,保住页数与连贯(见 GENERATION_PIPELINE §5);
同时让全流程在无真实 LLM 时也能离线产出可用 deck。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TypeVar

from packages.core import (
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
    SlideSpec,
    SummarySlide,
    TimelineEvent,
    TimelineSlide,
)
from packages.planner.schemas import SlidePlan

T = TypeVar("T")


def ensure_len(items: list[T], lo: int, hi: int, fill: Callable[[int], T]) -> list[T]:
    """把列表夹到 [lo, hi]:超出截断,不足用 fill(i) 补。"""
    out = list(items[:hi])
    while len(out) < lo:
        out.append(fill(len(out)))
    return out


_CN_ORD = "一二三四五六七八九十"
# 数值识别:支持 78% / 3.2x / 1.2万 / ¥1.5亿 等;无数字时不造假(见红线 #data)
_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?\s*(?:%|％|‰|倍|万|亿|[KkMmBb]|[xX])?")

_BODY_PAIR = (
    "{p}与{ref}相互呼应,是本页需要重点把握的一环。",
    "围绕{p},可结合{ref}一起理解,落到具体行动更见成效。",
    "{p}是关键,配合{ref}推进能让效果事半功倍。",
)
_BODY_SOLO = (
    "{p}是「{title}」的核心所在,需结合具体场景理解并落地执行。",
    "把{p}讲透,是这一页要传达的重点,建议结合实例逐步展开。",
)


def _nonempty(items: list[str]) -> list[str]:
    """去空白、去前后空格后的要点列表。"""
    return [p.strip() for p in items if p and p.strip()]


def _elaborate(point: str, title: str, siblings: list[str], i: int) -> str:
    """从要点派生一句具体说明:≥12 字、不复述 title;优先借相邻要点互为佐证。"""
    others = [s for s in siblings if s.strip() and s.strip() != point.strip()]
    if others:
        ref = others[i % len(others)]
        return _BODY_PAIR[i % len(_BODY_PAIR)].format(p=point, ref=ref)
    return _BODY_SOLO[i % len(_BODY_SOLO)].format(p=point, title=title)


def _ordinal(i: int) -> str:
    return _CN_ORD[i] if i < len(_CN_ORD) else str(i + 1)


# 离线卡片图标:从标题/正文里的常见中文词派生英文语义关键词(AssetEngine.resolve_icon 可解析);
# 无明显语义时按序轮换一组中性图标,保证内容页都有图标、不再「白纸黑字」。
_ICON_HINTS: tuple[tuple[str, str], ...] = (
    ("目标", "goal"), ("背景", "compass"), ("概念", "idea"), ("核心", "target"),
    ("示例", "code"), ("误区", "risk"), ("风险", "risk"), ("挑战", "risk"),
    ("进阶", "trending-up"), ("增长", "growth"), ("提升", "growth"), ("数据", "data"),
    ("指标", "data"), ("对比", "compare"), ("方案", "idea"), ("设计", "idea"),
    ("架构", "架构"), ("实现", "code"), ("技术", "tech"), ("落地", "完成"),
    ("验证", "完成"), ("规划", "compass"), ("战略", "compass"), ("团队", "team"),
    ("用户", "team"), ("市场", "市场"), ("机会", "idea"), ("成本", "cost"),
    ("预算", "预算"), ("商业", "business"), ("流程", "process"), ("步骤", "process"),
    ("时间", "time"), ("进度", "time"), ("计划", "calendar"), ("安全", "security"),
    ("质量", "quality"), ("效率", "speed"), ("速度", "speed"), ("亮点", "idea"),
    ("功能", "puzzle"), ("上线", "launch"), ("发布", "launch"), ("总结", "完成"),
)
_ICON_ROTATION: tuple[str, ...] = ("target", "idea", "layers", "compass", "完成", "sparkles")


def _derive_icon(point: str, title: str, i: int) -> str:
    """派生语义图标:先看卡片自身要点(更具区分度),再看页标题,都不中则按序轮换(确定性)。"""
    for text in (point, title):
        for cue, keyword in _ICON_HINTS:
            if cue in text:
                return keyword
    return _ICON_ROTATION[i % len(_ICON_ROTATION)]


def _metric_from_point(point: str) -> Metric:
    """要点里有数字才做成指标(surface 真实数值);无数字不编造,value 给「—」、信息落 label。"""
    m = _NUM_RE.search(point)
    if m and any(ch.isdigit() for ch in m.group()):
        value = m.group().strip()
        label = (point[: m.start()] + point[m.end() :]).strip(" ,，、:：·-—") or point
        return Metric(value=value, label=label)
    return Metric(value="—", label=point)


def slide_from_plan(plan: SlidePlan, idx: int) -> SlideSpec:
    """造一张合法 slide,并给内容页附一行简单演讲者备注(从标题/要点派生)。"""
    slide = _build_slide(plan, idx)
    if plan.key_points and plan.type not in ("cover", "section", "closing", "agenda"):
        notes = f"讲解「{plan.title}」:" + "、".join(plan.key_points[:3])
        return slide.model_copy(update={"speaker_notes": notes})
    return slide


def _build_slide(plan: SlidePlan, idx: int) -> SlideSpec:
    """按 type 造一张合法的最小幻灯片。id/index 后续会被 Planner 统一重排。

    纪律:不产空字段、不补「要点N/说明N」占位、不编造数字 —— 无文案时从要点/标题派生
    一句具体内容(见 GENERATION_PIPELINE §5 与内容质量红线)。
    """
    sid = f"{plan.type}-{idx}"
    pts = _nonempty(plan.key_points)
    first = pts[0] if pts else ""

    if plan.type == "cover":
        return CoverSlide(id=sid, index=idx, title=plan.title, subtitle=first or None)
    if plan.type == "agenda":
        return AgendaSlide(id=sid, index=idx, title=plan.title, items=(pts or [plan.title])[:8])
    if plan.type == "section":
        # subtitle 必填:一句点出本章要回答什么(不空)
        subtitle = first or f"本章聚焦「{plan.title}」,看清其中的关键与取舍"
        return SectionSlide(
            id=sid, index=idx, title=plan.title,
            section_number=plan.section_id, subtitle=subtitle,
        )
    if plan.type == "big_idea":
        # statement 是一句主张(≠标题);support 一行论据,二要素都不空
        head = first or plan.title
        statement = f"{head},是不容忽视的关键" if len(head) < 10 and head != plan.title else head
        if statement.strip() == plan.title.strip():
            statement = f"{plan.title}:抓住关键,才能事半功倍"
        rest = pts[1:]
        support = (
            "、".join(rest[:2])
            if rest
            else f"围绕「{plan.title}」展开论证,可逐步推进并落到实处"
        )
        return BigIdeaSlide(id=sid, index=idx, title=plan.title, statement=statement, support=support)
    if plan.type == "cards":
        base = pts or [plan.title]
        cards = [
            Card(
                title=p,
                body=_elaborate(p, plan.title, base, i),
                icon=_derive_icon(p, plan.title, i),
            )
            for i, p in enumerate(base[:4])
        ]
        while len(cards) < 2:  # 维持 2-4 张;不足从标题派生(非「要点N」占位)
            j = len(cards)
            facet = f"{plan.title}·关键点{_ordinal(j)}"
            cards.append(
                Card(
                    title=facet,
                    body=_elaborate(facet, plan.title, base, j),
                    icon=_derive_icon(facet, plan.title, j),
                )
            )
        return CardsSlide(id=sid, index=idx, title=plan.title, cards=cards)
    if plan.type == "timeline":
        evpts = list(pts)
        while len(evpts) < 3:  # 维持 3-6 节点;time 用相对阶段、每节点给 desc(非纯序号/占位)
            evpts.append(f"{plan.title}·第{_ordinal(len(evpts))}步")
        events = [
            TimelineEvent(time=f"第{_ordinal(i)}阶段", title=p, desc=f"聚焦{p},稳步推进与落实")
            for i, p in enumerate(evpts[:6])
        ]
        return TimelineSlide(id=sid, index=idx, title=plan.title, events=events)
    if plan.type == "comparison":
        cpts = pts or [plan.title]
        mid = max(1, len(cpts) // 2)
        return ComparisonSlide(
            id=sid, index=idx, title=plan.title,
            left=ComparisonColumn(heading="一种思路", points=cpts[:mid]),
            right=ComparisonColumn(heading="另一种思路", points=cpts[mid:] or [cpts[0]]),
        )
    if plan.type == "process":
        spts = list(pts)
        while len(spts) < 3:  # 维持 3-5 步;不足从标题派生(非「步骤N」占位)
            spts.append(f"{plan.title}·第{_ordinal(len(spts))}步")
        steps = [ProcessStep(title=p) for p in spts[:5]]
        return ProcessSlide(id=sid, index=idx, title=plan.title, steps=steps)
    if plan.type == "data":
        dpts = pts or [plan.title]
        metrics = [_metric_from_point(p) for p in dpts[:4]]
        return DataSlide(id=sid, index=idx, title=plan.title, metrics=metrics)
    if plan.type == "quote":
        return QuoteSlide(id=sid, index=idx, title="", quote=plan.title or first)
    if plan.type == "summary":
        spts = pts or [plan.title]
        points = [f"{p}——这是本部分需要记住的关键收获之一" for p in spts[:5]]
        return SummarySlide(id=sid, index=idx, title=plan.title, points=points)
    # closing
    return ClosingSlide(id=sid, index=idx, title="", subtitle=plan.title or None, cta=first or None)
