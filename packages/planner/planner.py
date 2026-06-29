"""Planner 编排:input → Plan → Compose → 组装 DeckSpec → Validator 兜底修复。

theme 先用中性占位(neutral_theme),由后续 ThemeEngine 替换。benchmark collector 可选注入。
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from packages.benchmark import BenchmarkCollector
from packages.core import DeckSpec
from packages.llm.provider import LLMProvider
from packages.planner._defaults import neutral_theme
from packages.planner.compose import SlideProgressFn, run_compose
from packages.planner.plan import run_plan
from packages.planner.schemas import DeckOutline, GenerationInput
from packages.planner.validator import DeckSpecValidator


class Planner:
    def __init__(
        self, provider: LLMProvider, *, validator: DeckSpecValidator | None = None
    ) -> None:
        self.provider = provider
        self.validator = validator or DeckSpecValidator()

    def plan(
        self, inp: GenerationInput, *, collector: BenchmarkCollector | None = None
    ) -> DeckOutline:
        """Plan 步:只出叙事大纲(供两阶段生成的「大纲确认」环节)。"""
        return run_plan(self.provider, inp, collector=collector)

    def compose(
        self,
        inp: GenerationInput,
        outline: DeckOutline,
        *,
        collector: BenchmarkCollector | None = None,
        on_slide: SlideProgressFn | None = None,
        constraints: Mapping[str, int] | None = None,
    ) -> DeckSpec:
        """Compose 步:按(可能已被用户编辑的)大纲扩写正文,组装并兜底成 DeckSpec。

        on_slide 逐页回调透传给 run_compose,供调用方流式逐页消费。
        constraints(来自选定模板 slot_map)透传给 validator,实现模板级数量约束。
        """
        slides = run_compose(self.provider, outline, collector=collector, on_slide=on_slide)
        # id 取 topic+brief+audience 的哈希:同输入确定复现,不同输入(即便 topic 相同)不撞 id
        fingerprint = "\x00".join((inp.topic, inp.brief, inp.audience))
        deck = DeckSpec(
            id="deck-" + hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:8],
            title=outline.title,
            topic=inp.topic,
            brief=inp.brief,
            audience=inp.audience,
            purpose=outline.purpose,
            deck_type=outline.deck_type,
            narrative=outline.narrative,
            theme=neutral_theme(),
            slides=slides,
        )
        return self.validator.repair(deck, constraints)

    def generate(
        self, inp: GenerationInput, *, collector: BenchmarkCollector | None = None
    ) -> DeckSpec:
        """一步到位:Plan → Compose(供 CLI / 快捷直出路径复用)。"""
        return self.compose(inp, self.plan(inp, collector=collector), collector=collector)
