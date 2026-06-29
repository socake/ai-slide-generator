"""离线确定性内容生成:无 LLM key 时产出题目相关、按 deck_type 成章的 DeckOutline。

仍是**启发式**(非真 LLM):章节用各 deck_type 的模板,要点从 brief 切句派生,slide 类型
按位轮换以展示渲染多样性。确定性 —— 同输入同输出。真实 LLM 接入后由 Plan 取代本路径。
"""

from __future__ import annotations

import re

from packages.core.enums import DeckType, SlideType
from packages.core.narrative import NarrativeSpec
from packages.planner.schemas import DeckOutline, GenerationInput, SectionPlan, SlidePlan

# 各 deck_type 的 6 章模板(决定叙事骨架,差异化"不同输入不像同模板填空")
SECTION_TEMPLATES: dict[DeckType, list[str]] = {
    "teaching": ["背景与目标", "核心概念", "动手示例", "常见误区", "进阶方向", "实战清单"],
    "review": ["这一年的关键词", "做成了什么", "数据回顾", "踩过的坑", "收获与成长", "明年计划"],
    "consumer": ["为什么值得关注", "选购维度", "横向对比", "推荐清单", "使用建议", "避坑指南"],
    "travel": ["行程概览", "必去清单", "美食地图", "交通与住宿", "预算与贴士", "实用锦囊"],
    "tech": ["问题背景", "方案设计", "架构与实现", "关键权衡", "落地与验证", "后续规划"],
    "exec_report": ["执行摘要", "业绩概览", "关键指标", "风险与挑战", "战略举措", "下一步"],
    "product": ["市场机会", "产品亮点", "核心功能", "竞品对比", "商业模式", "上线计划"],
    "pitch": ["痛点与机会", "解决方案", "市场与模式", "竞争壁垒", "团队与进展", "融资计划"],
    "generic": ["背景", "现状分析", "核心要点", "案例与对比", "落地建议", "总结展望"],
}

# 每章 3 张内容页的版式组合:承载量大的 cards/comparison/process 为主,big_idea 稀疏(每章≤1)。
# 离线无可量化信息 → 不用 data/timeline,避免编造数字与日期(见内容质量红线)。
_CHAPTER_PATTERNS: list[list[SlideType]] = [
    ["cards", "process", "comparison"],
    ["comparison", "cards", "big_idea"],
    ["process", "comparison", "cards"],
    ["cards", "comparison", "process"],
    ["process", "big_idea", "comparison"],
    ["comparison", "process", "cards"],
]
_CONTENT_TITLE: dict[str, str] = {
    "big_idea": "一句话主张",
    "cards": "关键要点",
    "comparison": "两种思路对比",
    "process": "推进步骤",
}


def brief_points(brief: str, k: int, *, seed: str = "") -> list[str]:
    """把 brief 切成短句作为要点;不足用 seed 派生补足。确定性、不重复。"""
    parts = [p.strip() for p in re.split(r"[,，。.;；、/\n]+", brief) if p.strip()]
    out = list(parts[:k])
    while len(out) < k:
        out.append(f"{seed or '要点'}{len(out) + 1}")
    return out


def _content_slide(stype: SlideType, sec: SectionPlan, points: list[str]) -> SlidePlan:
    return SlidePlan(
        type=stype,
        title=f"{sec.heading}·{_CONTENT_TITLE.get(stype, '要点')}",
        key_points=points,
        section_id=sec.id,
    )


def build_offline_outline(inp: GenerationInput, deck_type: DeckType) -> DeckOutline:
    """按 deck_type 模板成章,从 brief 派生要点,slide 类型轮换。产出 25-30 页骨架。"""
    headings = SECTION_TEMPLATES.get(deck_type, SECTION_TEMPLATES["generic"])
    sections = [SectionPlan(id=i + 1, heading=h) for i, h in enumerate(headings)]
    points = brief_points(inp.brief, max(6, len(headings) * 2), seed=inp.topic)

    slides: list[SlidePlan] = [
        SlidePlan(
            type="cover",
            title=inp.topic,
            key_points=[inp.brief[:60] or inp.topic, f"面向{inp.audience}"],
            section_id=0,
        ),
        SlidePlan(type="agenda", title="目录", key_points=headings, section_id=0),
    ]
    cursor = 0
    for s_idx, sec in enumerate(sections):
        slides.append(
            SlidePlan(
                type="section",
                title=sec.heading,
                key_points=[f"本章讲清「{sec.heading}」的关键问题与取舍"],  # 强制 section 导语不空
                section_id=sec.id,
            )
        )
        pattern = _CHAPTER_PATTERNS[s_idx % len(_CHAPTER_PATTERNS)]
        for c in range(3):  # 每章 3 张内容页,按章别版式组合(承载量大优先)
            stype = pattern[c]
            chunk = [points[(cursor + j) % len(points)] for j in range(3)]
            cursor += 1
            slides.append(_content_slide(stype, sec, chunk))
    slides.append(
        SlidePlan(
            type="summary",
            title="小结",
            key_points=brief_points(inp.brief, 3, seed=inp.topic),
            section_id=0,
        )
    )
    slides.append(
        SlidePlan(
            type="closing", title="谢谢观看", key_points=[f"欢迎与{inp.audience}交流"], section_id=0
        )
    )

    return DeckOutline(
        title=inp.topic,
        deck_type=deck_type,
        purpose=f"向{inp.audience}讲清{inp.topic}",
        narrative=NarrativeSpec(
            hook=f"为什么{inp.topic}值得关注",
            conflict="常见的困惑、误区与权衡",
            progression=list(headings),
            resolution="可落地的下一步",
        ),
        sections=sections,
        slides=slides,
    )
