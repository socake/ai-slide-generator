"""确定性演示稿质量评估(PPTEval 启发,零 LLM)。

三维各 0-100,加权汇总:
  - content  内容充实度:空白页、正文密度、占位残留
  - structure 结构完整度:封面/目录/结尾、页数落在 [25,60]、章节均衡
  - design   版式多样度:slide type 多样性(不全是 big_idea)、备注覆盖

输出可直接用于"导出检查/质量分",也用于 benchmark 回归。内核内零基础设施依赖。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.core import BigIdeaSlide, CardsSlide, DeckSpec, TimelineSlide
from packages.core.slides import SlideSpec

_PLACEHOLDER_HINTS = ("lorem", "ipsum", "xxxx", "占位", "待补充", "tbd", "todo", "要点n", "说明n")
_MIN_SLIDES = 25
_MAX_SLIDES = 60
_MIN_CARD_BODY = 12  # 卡片正文最低字数(低于此视为稀疏)
_VISUAL_RATIO_FLOOR = 0.6  # 含视觉元素页占比下限
# 自带视觉元素的页型(图表/卡片网格/编号徽章/两栏/母题色块/大引号/大数字)
_VISUAL_TYPES = frozenset(
    {"cards", "data", "process", "timeline", "comparison", "big_idea", "section", "cover", "quote"}
)


@dataclass
class Dimension:
    key: str
    label: str
    score: int
    issues: list[str] = field(default_factory=list)


@dataclass
class QualityReport:
    score: int
    dimensions: list[Dimension]
    summary: str

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "summary": self.summary,
            "dimensions": [
                {"key": d.key, "label": d.label, "score": d.score, "issues": d.issues}
                for d in self.dimensions
            ],
        }


def _slide_text(s: SlideSpec) -> str:
    """把一页里所有「有效且不重复」的用户可见文本拼起来(用于密度/空白/占位判定)。

    去空(空 body 不计有效文本)+ 去重(statement==title、重复短语只算一次),让语义稀疏现形。
    """
    parts: list[str] = []
    data = s.model_dump()
    for k, v in data.items():
        if k in _META_FIELDS:
            continue
        _collect_strings(v, parts)
    seen = dict.fromkeys(p.strip() for p in parts if p and p.strip())
    return " ".join(seen).strip()


def _collect_strings(v: object, parts: list[str]) -> None:
    """递归收集字符串叶子:覆盖嵌套 dict(如 comparison 的 left/right)与 list(points/cards)。"""
    if isinstance(v, str):
        parts.append(v)
    elif isinstance(v, list):
        for item in v:
            _collect_strings(item, parts)
    elif isinstance(v, dict):
        for x in v.values():
            _collect_strings(x, parts)


# 非内容元字段:不计入「页面可见文本」,否则空白页会被 id/type 撑过密度阈值
_META_FIELDS = frozenset(
    {"id", "index", "type", "emphasis", "layout_id", "asset_hint", "speaker_notes"}
)


def _field_violations(s: SlideSpec) -> int:
    """按 type 的最小字段检查:卡片正文过短/复述标题、big_idea 缺支撑或复述标题、timeline 缺 desc。"""
    bad = 0
    if isinstance(s, CardsSlide):
        for c in s.cards:
            body = c.body.strip()
            if len(body) < _MIN_CARD_BODY or body == c.title.strip():
                bad += 1
    elif isinstance(s, BigIdeaSlide):
        if not (s.support or "").strip():
            bad += 1
        if s.statement.strip() == s.title.strip():
            bad += 1
    elif isinstance(s, TimelineSlide):
        bad += sum(1 for e in s.events if not (e.desc or "").strip())
    return bad


def _has_visual(s: SlideSpec) -> bool:
    """该页是否含视觉元素(图表/卡片网格/徽章/两栏/母题等)。cards 需 ≥2 张才算网格。"""
    if isinstance(s, CardsSlide):
        return len(s.cards) >= 2
    return s.type in _VISUAL_TYPES


def _content_dim(slides: list[SlideSpec]) -> Dimension:
    issues: list[str] = []
    blanks = [i for i, s in enumerate(slides) if len(_slide_text(s)) < 8]
    placeholders = [
        i for i, s in enumerate(slides)
        if any(h in _slide_text(s).lower() for h in _PLACEHOLDER_HINTS)
    ]
    thin = [i for i, s in enumerate(slides) if 8 <= len(_slide_text(s)) < 40]
    score = 100
    if blanks:
        score -= min(50, 12 * len(blanks))
        issues.append(f"{len(blanks)} 页内容近乎空白")
    if placeholders:
        score -= min(30, 15 * len(placeholders))
        issues.append(f"{len(placeholders)} 页疑似占位文本")
    if len(thin) > len(slides) * 0.3:
        score -= 15
        issues.append(f"{len(thin)} 页正文偏薄,信息密度不足")
    weak = sum(_field_violations(s) for s in slides)
    if weak:
        score -= min(30, 5 * weak)
        issues.append(f"{weak} 处字段稀疏(卡片正文过短/复述标题、big_idea 缺论据、timeline 缺说明)")
    return Dimension("content", "内容充实度", max(0, score), issues)


def _structure_dim(slides: list[SlideSpec]) -> Dimension:
    issues: list[str] = []
    types = [s.type for s in slides]
    score = 100
    if "cover" not in types:
        score -= 20
        issues.append("缺少封面页")
    if "closing" not in types:
        score -= 15
        issues.append("缺少结束页")
    n = len(slides)
    if n < _MIN_SLIDES:
        score -= min(30, 4 * (_MIN_SLIDES - n))
        issues.append(f"仅 {n} 页,低于建议下限 {_MIN_SLIDES}")
    elif n > _MAX_SLIDES:
        score -= 10
        issues.append(f"{n} 页,超过上限 {_MAX_SLIDES}")
    return Dimension("structure", "结构完整度", max(0, score), issues)


def _design_dim(slides: list[SlideSpec]) -> Dimension:
    issues: list[str] = []
    content = [s for s in slides if s.type not in ("cover", "agenda", "section", "summary", "closing")]
    score = 100
    if content:
        kinds = {s.type for s in content}
        if len(kinds) <= 1:
            score -= 35
            issues.append("内容页版式单一(仅一种类型)")
        elif len(kinds) == 2:
            score -= 15
            issues.append("内容页版式偏少(仅两种类型)")
        big = sum(1 for s in content if s.type == "big_idea")
        if big > len(content) * 0.5:
            score -= 20
            issues.append("big_idea 版式占比过高")
    noteless = sum(1 for s in slides if not (getattr(s, "speaker_notes", "") or "").strip())
    if noteless > len(slides) * 0.5:
        score -= 15
        issues.append(f"{noteless} 页缺演讲备注")
    # 视觉维度:含视觉元素的页占比,过低说明纯文字页太多
    if slides:
        ratio = sum(1 for s in slides if _has_visual(s)) / len(slides)
        if ratio < _VISUAL_RATIO_FLOOR:
            score -= min(25, round((_VISUAL_RATIO_FLOOR - ratio) * 100))
            issues.append(f"仅 {round(ratio * 100)}% 的页含视觉元素(图表/卡片/母题),纯文字页偏多")
    return Dimension("design", "版式多样度", max(0, score), issues)


def evaluate_quality(deck: DeckSpec) -> QualityReport:
    """对一份 DeckSpec 做确定性质量打分。content 0.5 / structure 0.3 / design 0.2。"""
    slides = list(deck.slides)
    dims = [_content_dim(slides), _structure_dim(slides), _design_dim(slides)]
    weights = {"content": 0.5, "structure": 0.3, "design": 0.2}
    overall = round(sum(d.score * weights[d.key] for d in dims))
    n_issues = sum(len(d.issues) for d in dims)
    summary = "未发现明显问题" if n_issues == 0 else f"发现 {n_issues} 处可改进项"
    return QualityReport(score=overall, dimensions=dims, summary=summary)
