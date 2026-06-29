"""Plan / Compose 指令模板。返回 (system, user) 供 LLMProvider.structured 使用。

事前约束:模型按目标 schema 直接产出可被 Pydantic parse 的对象(见 GENERATION_PIPELINE §3)。
"""

from __future__ import annotations

from packages.planner.schemas import DeckOutline, GenerationInput, SectionPlan, SlidePlan

PLAN_SYSTEM = (
    "你是资深演示稿策划。产出完整结构(叙事线 + 每页骨架),不写正文。**铁律:slides 必须给满 25-60 项,这是硬指标,宁多勿少。**\n"
    "0) 先判定 deck_type,从 [teaching/review/consumer/exec_report/travel/product/pitch/tech/generic] 选**最贴合**的:"
    "技术/框架/架构/编程/系统/AI/工程→tech;教程/入门/讲解/科普/课程→teaching;汇报/总结/复盘/年度→exec_report 或 review;"
    "提案/路演/融资/方案推介→pitch;产品介绍/功能发布→product;选购/测评/好物/美食→consumer;旅行/行程/攻略→travel。"
    "**只有确实不属于任何专门类型时才用 generic**(别图省事默认 generic,类型决定主题与版式);\n"
    "1) 结构与页数算术(照此给满): cover×1 + agenda×1 + 5~6 个 section,每个 section = 1 个 section 页 + 4~5 个内容页 + summary×1 + closing×1;\n"
    "   → 例:5 个 section × (1+4) = 25 + cover/agenda/summary/closing 4 页 = 29 页。务必让 slides 数组真实包含这么多项,不要在脑中省略;\n"
    "2) 内容页 type 以承载量大的 cards/comparison/process 为主,辅以 data/timeline(仅当有可量化信息/时间脉络时);"
    "**每个 section 至多 1 个 big_idea**,不要靠 big_idea 凑页;每个 section 内尽量 3 种以上版式;\n"
    "3) **无可量化数字不要选 data 页型,无明确时间脉络不要选 timeline 页型**(避免下游编造数字/日期);\n"
    "4) 每页 title 具体到点(不要泛泛如「概述」),key_points 给 3-5 条具体、可扩写的要点;**section 页也要给 1 条导语式 key_point**(点出本章要回答什么);\n"
    "5) 结构页(cover/agenda/summary/closing)的 section_id 填 0,内容页填所属 section 的 id;\n"
    "6) 自检:产出前数一遍 slides 长度,< 25 就继续加内容页直到 ≥ 25。"
)

COMPOSE_SYSTEM = (
    "你是演示稿文案,把每页骨架扩写成充实、具体的 typed content。按 type 满足下列密度要求:\n"
    "- cards: 每张有 title 和一句具体的 body(≥15 字,可含例子/数字),body 不能为空、不复述 title;"
    "并给一个英文语义 icon 关键词(从 growth/security/data/team/speed/quality/cost/risk/idea/process/"
    "goal/time/market/tech/launch/compare 等里选最贴合的一个,用于自动配图标);\n"
    "- comparison: 左右各 2-3 条完整短句,两侧 heading 点明对比维度; process: 每步给一句 desc 说明;\n"
    "- big_idea: statement 是一句有观点的主张(≠标题),**必须**配 support 给一行论据/数据;\n"
    "- section: subtitle 必填,一句点出本章要回答什么; summary: 每条是带信息的完整句(呼应正文,非罗列章名);\n"
    "- timeline: 每个 event 有一句 desc,time 用真实/相对时间(如「2024 Q1」「第一阶段」)而非纯序号;\n"
    "- data: metrics 给真实数值与标签;\n"
    "通用铁律:任何字段不得为空或复述标题;不得出现「要点N/说明N」之类占位;无数据支撑不要编造数字;"
    "紧扣本页主题与全局叙事,信息密度高,不灌水、不留空。"
)


def _clamp_target(inp: GenerationInput) -> int:
    """目标页数收口到 [25,60](page_count 越界则就近取;默认 26)。"""
    return max(25, min(60, inp.page_count or 26))


_LOCALE_NAME = {"zh-CN": "简体中文", "en-US": "英文(English)"}


def _locale_line(inp: GenerationInput) -> str:
    name = _LOCALE_NAME.get(inp.output_locale, "简体中文")
    return f"生成语言: 全部内容(标题/章节/要点/正文)使用{name}。\n"


SKELETON_SYSTEM = (
    "你是资深演示稿策划。**只**快速产出:title(标题)+ sections(5-6 个章节标题字符串列表)。"
    "不要写正文、不要写每页、不要解释。章节要覆盖完整叙事(背景→核心→案例→落地→展望之类),具体不空泛。"
)


def build_skeleton_messages(inp: GenerationInput) -> tuple[str, str]:
    """两跳 Plan 第一跳:只要 标题 + 章节标题列表(OutlineSkeleton),输出小、出得快、非流式可靠。"""
    user = (
        f"主题: {inp.topic}\n简介: {inp.brief}\n受众: {inp.audience}\n"
        + _locale_line(inp)
        + "快速给出这份演示稿的 title 和 5-6 个章节标题(sections 字符串列表),只要标题,马上返回。"
    )
    return SKELETON_SYSTEM, user


def build_plan_messages(
    inp: GenerationInput, sections: list[str] | None = None
) -> tuple[str, str]:
    """组装 Plan 步的 (system, user) 提示:把输入转成产出 DeckOutline 的指令。

    传 sections(第一跳骨架的章节标题)则约束完整大纲沿用这些章节,保证"预览标题=最终结构"。
    """
    target = _clamp_target(inp)
    section_hint = (
        f"**章节已定,严格沿用这些章节标题(顺序一致)**: {' / '.join(sections)}\n" if sections else ""
    )
    user = (
        f"主题: {inp.topic}\n"
        f"简介: {inp.brief}\n"
        f"受众: {inp.audience}\n"
        + _locale_line(inp)
        + section_hint
        + f"目标页数: {target} 页(硬性落在 25-60,slides 数组实打实给够 {target} 项)。\n"
        "产出 DeckOutline,**严格按此字段顺序书写**: title → deck_type → sections → purpose → "
        "narrative → slides。**先确定 title/deck_type,再立刻写出完整的 sections(5-6 章的章节标题列表),"
        "然后才写 purpose/narrative/slides** —— 章节结构先定,后续每页归到对应章。\n"
        "slides 顺序: cover → agenda → 每个 section(1 个 section 页 + 4-5 个内容页) → summary → closing。\n"
        "最后产出 analysis(对这份大纲的元判断,供用户确认): audience_note(对受众的一句话解读); "
        "risks(1-3 条真实的风险/不确定性,如受众过宽、缺少数据、某角度未覆盖); "
        "coverage(4-6 个内容覆盖维度,每个 name + status: covered/partial/uncovered,如实评估哪些已覆盖、"
        "哪些仅部分、哪些缺); suggestion(一条可选的待确认补充建议,如「是否加入成本对比?」,没有则留空)。"
    )
    return PLAN_SYSTEM, user


def build_optimize_messages(inp: GenerationInput, outline: DeckOutline) -> tuple[str, str]:
    """智能优化:给当前大纲 + 分析,要 LLM 产出改进版 DeckOutline(补覆盖缺口/再平衡/收紧标题)。"""
    cov = outline.analysis.coverage if outline.analysis else []
    gaps = [c.name for c in cov if c.status != "covered"]
    risks = outline.analysis.risks if outline.analysis else []
    secs = "\n".join(
        f"- {s.heading}（{len([p for p in outline.slides if p.section_id == s.id])}页）"
        for s in outline.sections
    )
    user = (
        f"主题: {inp.topic}\n受众: {inp.audience}\n"
        + _locale_line(inp)
        + "下面是当前大纲,请**优化**后返回一份完整 DeckOutline(同样 25-60 页、同样字段顺序、含 analysis):\n"
        f"当前章节:\n{secs}\n"
        + (f"待补强的覆盖维度(未覆盖/部分覆盖): {', '.join(gaps)}\n" if gaps else "")
        + (f"已识别风险: {'; '.join(risks)}\n" if risks else "")
        + "优化目标: 补齐未覆盖/部分覆盖的维度(可加章或加页); 让各章页数更均衡(每章 4-6 页内容页); "
        "标题更具体有力、避免泛泛; 叙事更连贯。保持主题与受众不变,重新产出 analysis(覆盖维度据优化后如实评估)。"
    )
    return PLAN_SYSTEM, user


def build_expand_messages(
    inp: GenerationInput, outline: DeckOutline, target: int
) -> tuple[str, str]:
    """页数不足时的「补章」指令:带「还差几页」的具体缺口反馈,要求返回完整加长版 DeckOutline。

    新增的是**真实内容页**(具体 title + key_points),不是占位;给模型明确缺口比泛泛要求有效得多。
    """
    have = len(outline.slides)
    deficit = max(0, target - have)
    current = "\n".join(f"- [{p.type}] {p.title}" for p in outline.slides)
    user = (
        f"主题: {inp.topic}\n受众: {inp.audience}\n"
        f"下面这版大纲只有 {have} 页,**少了**,目标 {target} 页,还差约 {deficit} 页。\n"
        f"当前各页:\n{current}\n\n"
        f"请返回一份**完整**的 DeckOutline:保留上面已有的页,并新增约 {deficit} 个**内容页**,"
        f"让 slides 总数达到 {target}(落在 25-60)。新增页插入到相关 section 内,"
        "type 在 cards/comparison/process/timeline/data/big_idea 间选,title 具体、key_points 给 3-5 条,"
        "与已有页不重复、紧扣主题、叙事连贯;cover/agenda/summary/closing 各仍只 1 个。"
    )
    return PLAN_SYSTEM, user


def build_compose_messages(
    outline: DeckOutline, section: SectionPlan, plans: list[SlidePlan]
) -> tuple[str, str]:
    """组装 Compose 步的 (system, user) 提示:带全局叙事 + 本章骨架,指令扩写本章各页。"""
    skeleton = "\n".join(f"- [{p.type}] {p.title} :: {', '.join(p.key_points)}" for p in plans)
    n = len(plans)
    user = (
        f"演示稿: {outline.title}({outline.deck_type})\n"
        f"全局叙事: hook={outline.narrative.hook}; resolution={outline.narrative.resolution}\n"
        f"本章: {section.heading}\n"
        f"本章各页骨架(共 {n} 页):\n{skeleton}\n"
        f"为本章这 {n} 页各产出一个充实的 typed SlideSpec,装进 ComposedSection.slides(正好 {n} 个);"
        "每页正文具体到可直接放进 PPT,不要空字段、不要占位。"
    )
    return COMPOSE_SYSTEM, user
