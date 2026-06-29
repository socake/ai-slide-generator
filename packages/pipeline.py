"""内核统一生成入口:input → GenerationResult。供 CLI 复用。

依赖倒置:LLM provider 可注入(默认 MockLLMProvider,离线不花钱);存储由
调用方处理,本函数只吃 spec/config、吐 GenerationResult,不碰任何基础设施。
进度回调 on_progress 也由调用方注入(用它驱动进度展示),pipeline 本身保持纯。

链路(LLM 只在 planner):Plan/Compose → ThemeEngine 选主题 → AssetEngine 绑素材 →
render → 预览(可选) → benchmark。
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from packages.asset_engine import AssetEngine
from packages.benchmark import BenchmarkCollector
from packages.core import DeckSpec, GenerationResult
from packages.core.theme import ThemeSpec
from packages.llm import MockLLMProvider
from packages.llm.provider import LLMProvider
from packages.planner import (
    DeckOutline,
    DeckSpecValidator,
    GenerationInput,
    Planner,
    run_plan,
)
from packages.planner.compose import SlideProgressFn
from packages.planner.revise import revise_offline
from packages.renderer import PPTXRenderer, to_png
from packages.theme_engine import ThemeEngine

# 进度回调:(当前步骤文案, 百分比 0-100)
ProgressFn = Callable[[str, int], None]


def _noop(step: str, pct: int) -> None:
    """默认无操作进度回调。"""


def generate(
    inp: GenerationInput,
    provider: LLMProvider | None = None,
    *,
    with_preview: bool = True,
    on_progress: ProgressFn | None = None,
) -> GenerationResult:
    """从输入生成一套演示稿。默认走 Mock(确定性、离线、零成本)。

    on_progress 在各阶段间被调用,便于调用方驱动「生成进度展示」。
    """
    report = on_progress or _noop
    provider = provider or MockLLMProvider()
    collector = BenchmarkCollector("pending")

    # 进度标签「领先」它描述的阶段:Planner(Plan+Compose)是最长的真实 LLM 阶段
    # (占整套时长 95%+),必须在它开始前就报准确文案,否则这一分钟 UI 会错标成上一步。
    report("策划大纲与扩写正文", 8)
    deck = Planner(provider).generate(inp, collector=collector)
    report("选主题与版式", 65)
    deck.theme = ThemeEngine().select(deck.deck_type, deck.audience)
    report("匹配素材", 78)
    assets = AssetEngine().bind(deck)

    report("渲染导出", 90)
    started = perf_counter()
    pptx = PPTXRenderer().render(deck, assets)
    render_ms = (perf_counter() - started) * 1000

    previews = to_png(pptx) if with_preview else []

    collector.deck_id = deck.id
    benchmark = collector.report(slide_count=len(deck.slides), render_ms=render_ms)
    report("完成", 100)
    return GenerationResult(
        deck_spec=deck, pptx_bytes=pptx, preview_png=previews, benchmark=benchmark
    )


def plan_outline(
    inp: GenerationInput,
    provider: LLMProvider | None = None,
    *,
    on_heading: Callable[[str], None] | None = None,
    on_thinking: Callable[[str], None] | None = None,
) -> DeckOutline:
    """只跑 Plan 步,产出叙事大纲(不 compose、不渲染);供调用方快速预览结构。

    on_heading:provider 支持流式时,章节标题在 LLM 边写边逐条回调(供流式浮现)。
    on_thinking:同上,逐条回调"阶段思考文案"(主题/划分章节/叙事/规划页),供 UI 思考区。
    """
    return run_plan(
        provider or MockLLMProvider(), inp, on_heading=on_heading, on_thinking=on_thinking
    )


def _theme_from_template(base: ThemeSpec, template: dict[str, Any]) -> ThemeSpec:
    """用模板的配色/字体/字阶覆盖一个合法 base 主题(保留 mood/spacing 等默认),实现模板回填。"""
    t = template.get("theme", {})
    overrides: dict[str, Any] = {"id": template.get("id", base.id), "name": t.get("name", base.name)}
    if "palette" in t:
        overrides["palette"] = base.palette.model_copy(update=t["palette"])
    if "fonts" in t:
        overrides["fonts"] = base.fonts.model_copy(update=t["fonts"])
    if "type_scale" in t:
        overrides["type_scale"] = base.type_scale.model_copy(update=t["type_scale"])
    return base.model_copy(update=overrides)


def render_from_outline(
    inp: GenerationInput,
    outline: DeckOutline,
    provider: LLMProvider | None = None,
    *,
    with_preview: bool = False,
    on_progress: ProgressFn | None = None,
    on_slide: SlideProgressFn | None = None,
    on_theme: Callable[[ThemeSpec], None] | None = None,
    template: dict[str, Any] | None = None,
) -> GenerationResult:
    """两阶段生成的第二步:按(可能已被用户编辑的)大纲 选主题 → Compose 正文 → 素材 → 渲染。

    与 generate() 共用同一条确定性尾链;区别只是大纲来自外部(用户确认过)而非现 Plan。
    传 template(预设字典)则用模板配色回填(跳过自动选主题);否则按 deck_type 自动选。
    **主题确定性、与正文无关,提前选好** → on_theme 先把主题回调给调用方,on_slide 每页带主题
    流式回调,调用方即可渲染"真实主题化"缩略图(而非灰骨架)。
    """
    report = on_progress or _noop
    provider = provider or MockLLMProvider()
    collector = BenchmarkCollector("pending")

    # 主题先定(deck_type 来自大纲,audience 来自输入,都已知)→ 回调给调用方供逐页真实渲染。
    report("选主题版式", 12)
    auto = ThemeEngine().select(outline.deck_type, inp.audience)
    theme = _theme_from_template(auto, template) if template else auto
    if on_theme is not None:
        on_theme(theme)

    # 模板的版式映射 + 数量约束(preset.layout / slot_map):接进渲染与校验,实现「换模板换版式」。
    layout_map = template.get("layout") if template else None
    constraints = (template.get("slot_map", {}) or {}).get("constraints") if template else None

    report("扩写正文", 25)
    deck = Planner(provider).compose(
        inp, outline, collector=collector, on_slide=on_slide, constraints=constraints
    )
    deck.theme = theme
    report("匹配素材", 78)
    assets = AssetEngine().bind(deck)

    report("渲染导出", 90)
    started = perf_counter()
    pptx = PPTXRenderer().render(deck, assets, layout_map=layout_map)
    render_ms = (perf_counter() - started) * 1000
    previews = to_png(pptx) if with_preview else []

    collector.deck_id = deck.id
    benchmark = collector.report(slide_count=len(deck.slides), render_ms=render_ms)
    report("完成", 100)
    return GenerationResult(
        deck_spec=deck, pptx_bytes=pptx, preview_png=previews, benchmark=benchmark
    )


def render_pptx(deck: DeckSpec) -> bytes:
    """把一个(已带 theme 的)deck 渲成 pptx:绑素材 + 渲染。供 revise 后重渲染复用。"""
    return PPTXRenderer().render(deck, AssetEngine().bind(deck))


def revise_slide(
    deck: DeckSpec, index: int, instruction: str = "", provider: LLMProvider | None = None
) -> DeckSpec:
    """重生成第 index 页,保留全局 theme 与其它页;过 Validator 收口。

    provider 预留:真实 LLM 接入后改为对该页发单页 prompt 的定点 Compose;当前走离线确定性改写。
    """
    if not 0 <= index < len(deck.slides):
        raise IndexError(f"slide index {index} out of range [0,{len(deck.slides)})")
    revised = deck.model_copy(deep=True)
    revised.slides[index] = revise_offline(revised.slides[index], instruction)
    return DeckSpecValidator().repair(revised)
