"""DeckSpecValidator:结构校验 + 确定性修复(见 DATA_MODEL 校验清单 / GENERATION_PIPELINE §5)。

`validate` 报告问题;`repair` 做确定性兜底(永不整盘崩),保证产出落在约束内。
事前结构化已避免大部分问题,这里是最后一道兜底。
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel

from packages.core import (
    AgendaSlide,
    BigIdeaSlide,
    Card,
    CardsSlide,
    ClosingSlide,
    ComparisonSlide,
    CoverSlide,
    DataSlide,
    DeckSpec,
    Metric,
    ProcessSlide,
    ProcessStep,
    SectionSlide,
    SlideSpec,
    TimelineEvent,
    TimelineSlide,
)
from packages.planner.fallback import _elaborate, ensure_len

MIN_SLIDES = 25
MAX_SLIDES = 60
# typed content 数量约束(lo, hi)
_COUNTS: dict[str, tuple[int, int]] = {
    "cards": (2, 4),
    "timeline": (3, 6),
    "process": (3, 5),
}


class ValidationIssue(BaseModel):
    code: str
    message: str
    slide_index: int | None = None


class DeckSpecValidator:
    def validate(self, deck: DeckSpec) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        slides = deck.slides
        n = len(slides)

        if not (MIN_SLIDES <= n <= MAX_SLIDES):
            issues.append(
                ValidationIssue(code="page_count", message=f"页数 {n} 不在 [{MIN_SLIDES},{MAX_SLIDES}]")
            )

        covers = [s for s in slides if s.type == "cover"]
        closings = [s for s in slides if s.type == "closing"]
        if len(covers) != 1:
            issues.append(ValidationIssue(code="cover", message=f"cover 数量={len(covers)},应为 1"))
        if len(closings) != 1:
            issues.append(
                ValidationIssue(code="closing", message=f"closing 数量={len(closings)},应为 1")
            )
        if not any(s.type == "section" for s in slides):
            issues.append(ValidationIssue(code="section", message="缺少 section 页"))

        if [s.index for s in slides] != list(range(n)):
            issues.append(ValidationIssue(code="index", message="index 非 0..n-1 连续"))

        for s in slides:
            lo_hi = _COUNTS.get(s.type)
            if lo_hi and not (lo_hi[0] <= _content_len(s) <= lo_hi[1]):
                issues.append(
                    ValidationIssue(
                        code="count",
                        message=f"{s.type} 内容数={_content_len(s)} 越界 {lo_hi}",
                        slide_index=s.index,
                    )
                )
            if s.type not in ("quote", "closing") and not s.title.strip():
                issues.append(
                    ValidationIssue(code="title", message="标题为空", slide_index=s.index)
                )
        return issues

    def repair(self, deck: DeckSpec, constraints: Mapping[str, int] | None = None) -> DeckSpec:
        """确定性修复。constraints(来自选定模板 slot_map)覆盖默认数量上限,实现模板级密度约束。"""
        d = deck.model_copy(deep=True)
        slides = self._ensure_cover_closing(list(d.slides), d.title)
        slides = self._reorder_ends(slides)
        slides = [self._fix_counts(s, constraints) for s in slides]
        slides = [self._backfill_empty(s) for s in slides]
        slides = self._clamp_count(slides)
        for i, s in enumerate(slides):
            s.index = i
            s.id = f"slide-{i}"
        d.slides = slides
        return d

    # ── 内部确定性修复 ────────────────────────────────────────────
    @staticmethod
    def _ensure_cover_closing(slides: list[SlideSpec], title: str) -> list[SlideSpec]:
        if not any(s.type == "cover" for s in slides):
            slides.insert(0, CoverSlide(id="cover", index=0, title=title or "封面"))
        if not any(s.type == "closing" for s in slides):
            slides.append(ClosingSlide(id="closing", index=0, title="", cta="谢谢"))
        return slides

    @staticmethod
    def _reorder_ends(slides: list[SlideSpec]) -> list[SlideSpec]:
        """把首个 cover 提到最前、首个 closing 放到最后,保证 clamp/pad 的端点假设成立。"""
        cover = next((s for s in slides if s.type == "cover"), None)
        closing = next((s for s in slides if s.type == "closing"), None)
        if cover is not None:
            slides.remove(cover)
            slides.insert(0, cover)
        if closing is not None:
            slides.remove(closing)
            slides.append(closing)
        return slides

    @staticmethod
    def _fix_counts(s: SlideSpec, constraints: Mapping[str, int] | None = None) -> SlideSpec:
        def cap(key: str, default: int) -> int:
            return int(constraints[key]) if constraints and key in constraints else default

        if isinstance(s, CardsSlide):
            s.cards = ensure_len(s.cards, 2, cap("cards.max", 4), lambda i: Card(title=f"要点{i + 1}", body=""))
        elif isinstance(s, TimelineSlide):
            s.events = ensure_len(
                s.events, 3, 6, lambda i: TimelineEvent(time=f"{i + 1}", title=f"节点{i + 1}")
            )
        elif isinstance(s, ProcessSlide):
            s.steps = ensure_len(s.steps, 3, 5, lambda i: ProcessStep(title=f"步骤{i + 1}"))
        elif isinstance(s, AgendaSlide):
            s.items = s.items[: cap("agenda.items.max", len(s.items) or 1)]
        elif isinstance(s, DataSlide):
            if not s.metrics:
                s.metrics = [Metric(value="—", label="指标")]
            else:
                s.metrics = s.metrics[: cap("data.metrics.max", len(s.metrics))]
        elif isinstance(s, ComparisonSlide):
            if not s.left.points:
                s.left.points = ["—"]
            if not s.right.points:
                s.right.points = ["—"]
        return s

    @staticmethod
    def _backfill_empty(s: SlideSpec) -> SlideSpec:
        """兜底空字段:即便 LLM 漏填(compose 成功但留空),也确定性补一句具体内容,杜绝空白/一句话页。

        红线 #4「每页字段不得空或复述标题」的最后一道闸:不造数字,只从标题/相邻要点派生短句。
        """
        if isinstance(s, SectionSlide) and not (s.subtitle or "").strip():
            s.subtitle = f"本章聚焦「{s.title}」,看清其中的关键与取舍"
        elif isinstance(s, BigIdeaSlide):
            if not s.statement.strip() or s.statement.strip() == s.title.strip():
                s.statement = f"{s.title}:抓住关键,才能事半功倍"
            if not (s.support or "").strip():
                s.support = f"围绕「{s.title}」展开论证,可逐步推进并落到实处"
        elif isinstance(s, CardsSlide):
            base = [c.title.strip() for c in s.cards if c.title.strip()] or [s.title]
            for i, c in enumerate(s.cards):
                body = c.body.strip()
                if not body or body == c.title.strip():
                    c.body = _elaborate(c.title or s.title, s.title, base, i)
        elif isinstance(s, TimelineSlide):
            for e in s.events:
                if not (e.desc or "").strip():
                    e.desc = f"聚焦{e.title},稳步推进与落实"
        return s

    @staticmethod
    def _clamp_count(slides: list[SlideSpec]) -> list[SlideSpec]:
        # 仅截上限;**绝不塞占位页凑下限**(宁可少几页真实内容,也不要"待补充"垃圾)。
        # 25-30 页由 plan 提示保证;不足只在 validate() 里报 page_count。
        if len(slides) > MAX_SLIDES:
            return [slides[0], *slides[1:-1][: MAX_SLIDES - 2], slides[-1]]
        return slides


def _content_len(s: SlideSpec) -> int:
    if isinstance(s, CardsSlide):
        return len(s.cards)
    if isinstance(s, TimelineSlide):
        return len(s.events)
    if isinstance(s, ProcessSlide):
        return len(s.steps)
    return 0
