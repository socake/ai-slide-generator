"""Compose 步:按 section 批量扩写 typed content;每段失败重试 ≤2 次,再失败用 key_points 兜底。

(见 GENERATION_PIPELINE §2.2 / §5。Mock 下顺序执行;真实 provider 可并行,wall-clock≈最慢段。)
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from packages.benchmark import BenchmarkCollector
from packages.core.slides import SlideSpec
from packages.llm.provider import LLMProvider
from packages.planner.fallback import slide_from_plan
from packages.planner.prompts import build_compose_messages
from packages.planner.schemas import ComposedSection, DeckOutline, SectionPlan, SlidePlan

logger = logging.getLogger("aippt.planner")

# 逐页扩写回调:(已完成页数, 总页数, 刚扩写好的 SlideSpec, 所属章节 id) —— 供流式逐页回调。
# section_id 让调用方按章分组(SlideSpec 本身不带章号,故由 compose 循环现场传出)。
SlideProgressFn = Callable[[int, int, SlideSpec, int], None]


def run_compose(
    provider: LLMProvider,
    outline: DeckOutline,
    *,
    collector: BenchmarkCollector | None = None,
    max_retries: int = 2,
    on_slide: SlideProgressFn | None = None,
) -> list[SlideSpec]:
    """按 section 逐段扩写,拼成整套 typed SlideSpec;每段失败重试后兜底,保证覆盖全部页。

    每扩写好一页就回调 on_slide(已完成, 总数, slide),让调用方逐页消费
    (结构化场景的最优流式:推已校验通过的完整页,逐张呈现,不闪烁不假)。
    """
    headings = {s.id: s.heading for s in outline.sections}
    out: list[SlideSpec] = []
    total = len(outline.slides)
    # 按 slides 中出现的 section_id 顺序成段,确保每页都被覆盖
    for section_id in dict.fromkeys(p.section_id for p in outline.slides):
        plans = [p for p in outline.slides if p.section_id == section_id]
        section = SectionPlan(id=section_id, heading=headings.get(section_id, ""))
        for slide in _compose_section(provider, outline, section, plans, collector, max_retries):
            out.append(slide)
            if on_slide is not None:
                on_slide(len(out), total, slide, section_id)
    return out


def _compose_section(
    provider: LLMProvider,
    outline: DeckOutline,
    section: SectionPlan,
    plans: list[SlidePlan],
    collector: BenchmarkCollector | None,
    max_retries: int,
) -> list[SlideSpec]:
    system, user = build_compose_messages(outline, section, plans)
    last_exc: Exception | None = None
    for _ in range(max_retries + 1):
        try:
            result = provider.structured(system, user, ComposedSection)
        except Exception as exc:  # noqa: BLE001 — 单段失败可重试/兜底,但要留住最后一次异常
            last_exc = exc
            continue
        if collector is not None:
            collector.record("compose", result.usage)
        if result.value.slides:
            return list(result.value.slides)
    # 降级:用骨架确定性兜底,保住该段页数(并留痕:区分"LLM 一直报错"与"质量差")
    logger.warning(
        "Compose 段 %s 扩写失败,用骨架兜底%s",
        section.id, f"(末次异常: {last_exc})" if last_exc else "",
    )
    return [slide_from_plan(p, i) for i, p in enumerate(plans)]
