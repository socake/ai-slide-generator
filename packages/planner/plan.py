"""Plan 步:1 次结构化调用产出 DeckOutline;失败则确定性兜底(见 GENERATION_PIPELINE §2.1)。"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable

from packages.benchmark import BenchmarkCollector
from packages.core.enums import DeckType
from packages.llm.provider import LLMProvider, SupportsStructuredStream
from packages.planner.offline import build_offline_outline
from packages.planner.prompts import (
    _clamp_target,
    build_expand_messages,
    build_optimize_messages,
    build_plan_messages,
    build_skeleton_messages,
)
from packages.planner.schemas import (
    CoverageDim,
    DeckOutline,
    GenerationInput,
    OutlineAnalysis,
    OutlineSkeleton,
    SlidePlan,
)
from packages.planner.validator import MIN_SLIDES

logger = logging.getLogger("aippt.planner")

# 页数不足时最多补章次数(每次一次真实 LLM 调用,只在短缺时触发)。
_MAX_EXPAND = 2
# Plan 整体重试次数(间歇性网络/端点失败 → 重试再回退离线,避免占位垃圾)。
_PLAN_RETRIES = 3

# 离线兜底用的关键词 → deck_type 启发式(真实 LLM 由 Plan 自己判定 deck_type)。
# 顺序优先:先匹配到的胜出。
_DECK_TYPE_HINTS: list[tuple[DeckType, tuple[str, ...]]] = [
    ("teaching", ("入门", "教程", "教学", "课", "学习", "基础", "tutorial", "intro", "learn")),
    ("review", ("复盘", "回顾", "年度", "总结", "review", "retro")),
    ("consumer", ("挑选", "选购", "购买", "咖啡", "美食", "好物", "测评", "guide")),
    ("travel", ("旅行", "攻略", "旅游", "周末", "行程", "玩", "游", "trip", "travel")),
    ("tech", ("架构", "系统", "重写", "重构", "代码", "技术方案", "rust", "api")),
    ("exec_report", ("业绩", "汇报", "季度", "财报", "经营", "board", "financial")),
    ("product", ("发布", "上线", "新品", "launch", "release")),
    ("pitch", ("融资", "路演", "投资", "pitch")),
]


def _infer_deck_type(inp: GenerationInput) -> DeckType:
    """从 topic/brief/audience 关键词推断演示类型;无命中回落 generic。"""
    text = f"{inp.topic} {inp.brief} {inp.audience}".lower()
    for deck_type, hints in _DECK_TYPE_HINTS:
        if any(h.lower() in text for h in hints):
            return deck_type
    return "generic"


def run_plan(
    provider: LLMProvider,
    inp: GenerationInput,
    *,
    collector: BenchmarkCollector | None = None,
    on_heading: Callable[[str], None] | None = None,
    on_thinking: Callable[[str], None] | None = None,
    on_page: Callable[[int, str], None] | None = None,
) -> DeckOutline:
    """产出 DeckOutline;页数不足时带「还差几页」反馈补章(≤2 次,真实内容)。

    页数稳定由 Plan 保证(validator 不塞占位,守红线 #4):首版若 < 25 页,带具体缺口
    再向 LLM 要加长版,取更长者;补满或补不动即止(补不动则 validate 会如实报 page_count)。

    传 on_heading 且 provider 支持流式时,首版 Plan 走流式:章节标题在 LLM 边写边逐条回调
    (去重),供 UI 让标题逐条浮现;最终仍返回完整解析后的 DeckOutline(权威)。
    on_thinking:流式期间逐条回调"阶段思考文案"(主题→划分章节→叙事→规划页),供 UI 思考区。
    """
    target = _clamp_target(inp)  # 用户选的页数(收口 [25,60])
    explicit = inp.page_count is not None  # 用户显式选了页数 → 精确收口;否则只保证下限 ≥25
    floor = target if explicit else MIN_SLIDES

    # ── 第一跳:快速骨架(标题+章节标题,**非流式、输出小、出得快**)→ 立即逐条发标题 ──
    # 代理端点的流式 token 不稳(常 APIConnectionError),不能靠它喂标题;小的非流式骨架调用稳。
    skeleton: list[str] = []
    if on_heading is not None or on_thinking is not None:
        if on_thinking is not None:
            on_thinking("分析主题与受众,确定整体结构…")
        try:
            # 流式时章节标题在 _plan_skeleton 内逐条 token 浮现;拿到结果后再补一遍
            # (覆盖非流式回退路径),调用方按累积文本去重,重复无害。
            sk = _plan_skeleton(provider, inp, collector, on_heading)
            for h in sk.sections:
                skeleton.append(h)
                if on_heading is not None:
                    on_heading(h)
            if on_thinking is not None:
                on_thinking("章节已划分,正在细化每页要点…")
        except Exception:
            logger.warning("骨架调用失败,跳过标题预览(不影响完整大纲)", exc_info=True)

    # ── 第二跳:完整大纲(沿用骨架章节保证"预览=最终";间歇失败重试再回退离线)──
    outline = None
    for attempt in range(_PLAN_RETRIES):
        try:
            outline = _plan_full(provider, inp, skeleton or None, collector, on_page)
            break
        except Exception:
            logger.warning("Plan LLM 第 %d/%d 次失败", attempt + 1, _PLAN_RETRIES, exc_info=True)
    if outline is None:
        logger.warning("Plan LLM 多次失败,回退离线大纲(降级有意为之,但要可观测)")
        return fallback_outline(inp)

    attempts = 0
    # 不足下限就带「还差几页」反馈向 LLM 要加长版(真实内容,优先)。
    while len(outline.slides) < floor and attempts < _MAX_EXPAND:
        attempts += 1
        bigger = _expand_once(provider, inp, outline, target, collector)
        if bigger is None or len(bigger.slides) <= len(outline.slides):
            break  # 补不动就停,不空转
        outline = bigger
    # 收口:显式选了页数 → 精确补/截到该数(「选多少就多少」);默认只补到 ≥25 下限、不截。
    outline = _fit_outline_to_target(outline, floor, exact=explicit)
    return _ensure_analysis(outline, inp)


def _fit_outline_to_target(outline: DeckOutline, target: int, *, exact: bool = True) -> DeckOutline:
    """把大纲页数收口到 target。

    不足→按章轮流补内容页占位(标题带章节上下文,**compose 会扩写成真实内容,非空占位**)。
    过多→`exact` 时(用户显式选了页数)从尾部截内容页到 target;`exact=False`(默认页数)不截,
    保留 LLM 自然产出的更多真实内容。结构页(cover/agenda/section/summary/closing)始终保留。
    优先靠 LLM 扩写命中;本函数是确定性兜底,保证「用户选多少页就生成多少页」。
    """
    structural = {"cover", "agenda", "section", "summary", "closing"}
    content_n = sum(1 for s in outline.slides if s.type not in structural)
    struct_n = len(outline.slides) - content_n
    want = max(0, target - struct_n)  # 目标内容页数
    secs = outline.sections or []
    if content_n < want and secs:
        for k in range(want - content_n):
            sec = secs[k % len(secs)]
            idxs = [i for i, s in enumerate(outline.slides) if s.section_id == sec.id]
            at = (idxs[-1] + 1) if idxs else max(1, len(outline.slides) - 1)
            outline.slides.insert(
                at,
                SlidePlan(type="cards", title=f"{sec.heading}:延伸要点", key_points=[], section_id=sec.id),
            )
    elif exact and content_n > want:
        drop, kept = content_n - want, []
        dropped = 0
        for s in reversed(outline.slides):  # 从尾部截内容页,保留结构页(summary/closing 在尾)
            if dropped < drop and s.type not in structural:
                dropped += 1
                continue
            kept.append(s)
        outline.slides = list(reversed(kept))
    return outline


def optimize_outline(
    provider: LLMProvider, inp: GenerationInput, outline: DeckOutline
) -> DeckOutline:
    """智能优化:LLM 据当前大纲 + 分析产出改进版(补覆盖缺口/再平衡/收紧标题)。

    失败则原样返回(不破坏用户已有大纲);成功后过 analysis 兜底。
    """
    system, user = build_optimize_messages(inp, outline)
    try:
        improved = provider.structured(system, user, DeckOutline).value
    except Exception:
        logger.warning("智能优化失败,保留原大纲(降级有意为之)", exc_info=True)
        return outline
    return _ensure_analysis(improved, inp)


def reestimate_pages(outline: DeckOutline, *, lo: int = 3) -> DeckOutline:
    """确定性重估页数:把内容页过少(< lo)的章补占位内容页到 lo,使各章不过于单薄。

    非破坏(只加不删),即时无 LLM。占位页 title 留待用户改写或后续 compose 填。
    """
    o = outline.model_copy(deep=True)
    for sec in o.sections:
        content = [s for s in o.slides if s.section_id == sec.id and s.type != "section"]
        deficit = lo - len(content)
        if deficit <= 0:
            continue
        idxs = [i for i, s in enumerate(o.slides) if s.section_id == sec.id]
        at = (idxs[-1] + 1) if idxs else len(o.slides)
        for _ in range(deficit):
            o.slides.insert(
                at, SlidePlan(type="cards", title="补充要点", key_points=[], section_id=sec.id)
            )
    return o


def _ensure_analysis(outline: DeckOutline, inp: GenerationInput) -> DeckOutline:
    """大纲分析数据的兜底:LLM 没填 analysis 时按章节启发式生成。

    LLM 填了就用 LLM 的(更有判断力);没填则覆盖维度=各章节(均已覆盖)、受众取输入,
    保证面板永远有内容、不空着。
    """
    if outline.analysis is not None and outline.analysis.coverage:
        return outline
    base = outline.analysis or OutlineAnalysis()
    if not base.audience_note:
        base.audience_note = inp.audience
    if not base.coverage:
        base.coverage = [CoverageDim(name=s.heading, status="covered") for s in outline.sections]
    outline.analysis = base
    return outline


def _plan_skeleton(
    provider: LLMProvider,
    inp: GenerationInput,
    collector: BenchmarkCollector | None,
    on_heading: Callable[[str], None] | None = None,
) -> OutlineSkeleton:
    """两跳第一跳:出 标题 + 章节标题列表。输出小,**端点支持流式时逐条 token 流**(章节标题
    一个个"写出来",真·流式),否则非流式一次性返回(同样可靠)——两条路都稳。
    """
    system, user = build_skeleton_messages(inp)
    if on_heading is not None and isinstance(provider, SupportsStructuredStream):
        seen: set[str] = set()

        def _on_delta(acc: str) -> None:
            # OutlineSkeleton JSON: {"title":"…","sections":["s1","s2",…]}。
            # 从 "sections" 之后逐个抽**已闭合**的引号串(未写完的串无闭合引号不匹配),
            # 跳过键名 "sections",新串去重后即 on_heading → 标题逐条浮现。
            idx = acc.find('"sections"')
            if idx < 0:
                return
            for m in re.finditer(r'"([^"]+)"', acc[idx:]):
                s = m.group(1)
                if s != "sections" and s not in seen:
                    seen.add(s)
                    on_heading(s)

        result = provider.structured_stream(system, user, OutlineSkeleton, on_delta=_on_delta)
    else:
        result = provider.structured(system, user, OutlineSkeleton)
    if collector is not None:
        collector.record("plan", result.usage)
    return result.value


# 完整大纲 JSON 里 slides[].title 是页标题(SlidePlan 用 "title";章节用 "heading",故只命中页);
# 只在 "slides" 出现之后抽,跳过 deck 标题/章节标题,未闭合的串不匹配 → 只发完整页标题。
_PAGE_TITLE_RE = re.compile(r'"title"\s*:\s*"([^"]+)"')


def _plan_full(
    provider: LLMProvider,
    inp: GenerationInput,
    sections: list[str] | None,
    collector: BenchmarkCollector | None,
    on_page: Callable[[int, str], None] | None = None,
) -> DeckOutline:
    """两跳第二跳:完整 DeckOutline(权威);sections 传入则沿用骨架章节保证一致。

    on_page 且 provider 支持流式时,**完整大纲走流式**:每个页标题(slides[].title)边写边逐条
    回调(去重,带序号),供 UI 在"细化每页"的 ~30s 里让页标题渐进浮现(占位等待→可见进度);
    端点不支持/失败则回落非流式(行为不变)。
    """
    system, user = build_plan_messages(inp, sections)
    if on_page is not None and isinstance(provider, SupportsStructuredStream):
        seen: set[str] = set()

        def _on_delta(acc: str) -> None:
            idx = acc.find('"slides"')
            if idx < 0:
                return
            for m in _PAGE_TITLE_RE.finditer(acc[idx:]):
                title = m.group(1)
                if title and title not in seen:
                    seen.add(title)
                    on_page(len(seen), title)

        result = provider.structured_stream(system, user, DeckOutline, on_delta=_on_delta)
    else:
        result = provider.structured(system, user, DeckOutline)
    if collector is not None:
        collector.record("plan", result.usage)
    return result.value


def _expand_once(
    provider: LLMProvider,
    inp: GenerationInput,
    outline: DeckOutline,
    target: int,
    collector: BenchmarkCollector | None,
) -> DeckOutline | None:
    system, user = build_expand_messages(inp, outline, target)
    try:
        result = provider.structured(system, user, DeckOutline)
    except Exception:
        return None
    if collector is not None:
        collector.record("plan", result.usage)
    return result.value


def fallback_outline(inp: GenerationInput) -> DeckOutline:
    """无 LLM 时的确定性骨架:推断 deck_type → 按模板成章、从 brief 派生要点(见 offline)。"""
    return build_offline_outline(inp, _infer_deck_type(inp))
