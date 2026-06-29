"""Planner 的 I/O 契约(见 docs/GENERATION_PIPELINE §2)。

Plan 产出 `DeckOutline`(只定结构不写正文);Compose 按 section 产出 `ComposedSection`
(扩写后的 typed content)。两者都用结构化输出事前约束。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from packages.core.enums import DeckType, SlideType
from packages.core.narrative import NarrativeSpec
from packages.core.slides import SlideSpec


class GenerationInput(BaseModel):
    """生成入参(对应 examples/*.json)。"""

    topic: str
    brief: str
    audience: str
    page_count: int | None = None  # None → 目标 26（落在 [25,60]）
    output_locale: str = "zh-CN"  # 生成内容语言(与界面语言分离)
    template_id: str | None = None  # 选用的模板;None → 万金油基准


class SectionPlan(BaseModel):
    id: int
    heading: str


class OutlineSkeleton(BaseModel):
    """两跳 Plan 的第一跳:只出"标题 + 章节标题列表",输出小、出得快(~5-8s),且**非流式**。

    用于可靠地让章节标题尽早逐条浮现(代理端点流式 token 不稳时,token 流会失败;
    小的非流式骨架调用稳定),第二跳再据此展开完整 DeckOutline。
    """

    title: str
    sections: list[str]  # 5-6 个章节标题


class SlidePlan(BaseModel):
    type: SlideType
    title: str
    key_points: list[str] = Field(default_factory=list)  # 2-4 个,供 Compose 扩写
    section_id: int = 0  # 结构页(cover/agenda/summary/closing)LLM 常漏填,容错默认 0;内容页给真实章号


class CoverageDim(BaseModel):
    """内容覆盖维度(供"AI 分析/资料覆盖"展示)。"""

    name: str  # 维度名,如"趋势与机遇""成本与收益"
    status: Literal["covered", "partial", "uncovered"] = "covered"


class OutlineAnalysis(BaseModel):
    """对大纲的"元判断":受众解读、风险、内容覆盖、待确认建议。

    供大纲分析回答"为什么这么生成、哪里需要确认"。
    LLM 在 Plan 时一并产出(有上下文最准);缺失时由 _ensure_analysis 启发式兜底。
    """

    audience_note: str = ""  # 对受众的一句解读(如"关注技术趋势与落地实践")
    risks: list[str] = Field(default_factory=list)  # 1-3 条风险/不确定性提示
    coverage: list[CoverageDim] = Field(default_factory=list)  # 内容覆盖维度
    suggestion: str = ""  # 一条可选的待确认补充建议(如"是否加入企业落地成本对比?")


class DeckOutline(BaseModel):
    """Plan 步的结构化产出:骨架,不含正文与主题。

    字段声明顺序即 JSON Schema properties 顺序,也是希望模型流式写出的顺序:
    sections 紧跟 title/deck_type、远早于 narrative/slides → 流式时章节标题(`"heading"`)
    ~2-3s 就出现,标题逐条浮现,而非等模型写完 narrative/slides 才一次性冒(见 plan._plan_stream)。
    analysis 放最后(不影响标题流式顺序),供大纲分析;可空,缺失时启发式兜底。
    """

    title: str
    deck_type: DeckType
    sections: list[SectionPlan]
    purpose: str
    narrative: NarrativeSpec
    slides: list[SlidePlan]  # 25-30 条,已含 cover/section/closing
    analysis: OutlineAnalysis | None = None


class ComposedSection(BaseModel):
    """Compose 步对单个 section 的结构化产出。"""

    slides: list[SlideSpec]
