"""slot_mapper:把 typed content 字段映射到布局槽位,产出可直接渲染的 RenderSlot 列表。

固定槽位的位置来自布局 JSON;可变数量内容(cards/timeline/process/data)用网格/行
逻辑(纯代码,可复用可测)在 repeat_slot 区域内分配 Rect。renderer 只需遍历 RenderSlot
画出来,不再关心数量与排布。契约见 docs/DATA_MODEL §4.1。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from math import ceil

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
    LayoutSpec,
    ProcessSlide,
    QuoteSlide,
    Rect,
    SectionSlide,
    SlideSpec,
    SlotSpec,
    SummarySlide,
    TimelineSlide,
)
from packages.core.enums import Align, ColorRole, FontRole, SlotKind, VAlign

SlotValue = str | list[str]

# 语义图标解析回调:(语义关键词, 角色"card"/"process") → 图标 PNG 的 object_key 或 None。
# 由 renderer 注入(绑定主题色 + AssetEngine.resolve_icon);slot_mapper 自身保持调色板无关。
IconResolver = Callable[[str, str], str | None]


@dataclass
class RenderSlot:
    name: str
    value: SlotValue
    rect: Rect
    kind: SlotKind = "text"
    font_role: FontRole | None = None
    color_role: ColorRole = "text"
    align: Align = "left"
    valign: VAlign = "top"
    shape_role: str = "plain"  # shape 子类型:card / accent_bar / metric / plain

    @classmethod
    def from_spec(cls, name: str, value: SlotValue, spec: SlotSpec) -> RenderSlot:
        return cls(
            name, value, spec.rect, spec.kind, spec.font_role,
            spec.color_role, spec.align, spec.valign,
        )


# ── 几何工具(归一化,可复用) ───────────────────────────────────
def row_rects(region: Rect, n: int, gap: float = 0.02) -> list[Rect]:
    """把 region 横向等分成 n 个带间距的格子(用于时间轴/流程/数字卡的一行排布)。"""
    if n <= 0:
        return []
    w = (region.width - gap * (n - 1)) / n
    return [
        Rect(left=region.left + i * (w + gap), top=region.top, width=w, height=region.height)
        for i in range(n)
    ]


def grid_rects(region: Rect, n: int, cols: int, gap: float = 0.02) -> list[Rect]:
    """把 region 切成 cols 列、按需行数的网格,返回前 n 个格子(用于卡片网格)。"""
    if n <= 0:
        return []
    cols = max(1, cols)
    rows = ceil(n / cols)
    cw = (region.width - gap * (cols - 1)) / cols
    ch = (region.height - gap * (rows - 1)) / rows
    out: list[Rect] = []
    for i in range(n):
        r, c = divmod(i, cols)
        out.append(
            Rect(
                left=region.left + c * (cw + gap),
                top=region.top + r * (ch + gap),
                width=cw,
                height=ch,
            )
        )
    return out


_CANVAS_ASPECT = 12192000 / 6858000  # 16:9;把徽章画成正圆(EMU 等宽高)需按此收窄归一化宽


def _circle(left: float, top: float, diam_h: float) -> Rect:
    """正圆 Rect:高度 diam_h(归一化),宽度按画布宽高比收窄,保证 EMU 落地等宽高。"""
    return Rect(left=left, top=top, width=diam_h / _CANVAS_ASPECT, height=diam_h)


def _inset(rect: Rect, frac: float) -> Rect:
    """在 rect 内居中一个边长按 frac 缩放的子框(把方形图标压在圆形徽章中央)。"""
    w, h = rect.width * frac, rect.height * frac
    return Rect(
        left=rect.left + (rect.width - w) / 2,
        top=rect.top + (rect.height - h) / 2,
        width=w,
        height=h,
    )


def card_cols(n: int) -> int:
    """卡片列数随数量自适应:3→3 列(单行)、4→2×2、2→2 列、5-6→3 列两行。"""
    if n <= 1:
        return 1
    if n == 2:
        return 2
    if n == 3:
        return 3
    if n == 4:
        return 2
    return 3  # 5-6 张 → 3 列两行


# 卡片几何常量(归一化):间距/紧凑高度/单行高度上限/内边距
_CARD_GAP = 0.028
_CARD_COMPACT_H = 0.165  # body 为空时卡片高度上限,避免巨大空卡
_CARD_MAX_ROW_H = 0.4  # 单行卡片高度上限,避免竖条状空洞
_CARD_PAD_X = 0.024
_CARD_PAD_Y = 0.05


def _card_badge_label(card: Card, i: int) -> str:
    """卡片徽章内容:有短图标/符号用图标,否则用编号(母题:圆形色块 + 编号)。"""
    icon = (card.icon or "").strip()
    return icon if 0 < len(icon) <= 2 else str(i + 1)


def _expand_cards(
    cards: list[Card], region: Rect, icon_for: IconResolver | None = None,
    force_cols: int | None = None,
) -> list[RenderSlot]:
    """卡片网格:列数自适应(force_cols 强制列数,如 cards_2up 变体固定 2 列)、整体在区域内
    垂直居中、body 为空则收缩高度;每张卡 = 卡面 + 左上圆徽(图标/编号) + 标题 + 正文。"""
    out: list[RenderSlot] = []
    n = len(cards)
    if n == 0:
        return out
    cols = min(force_cols, n) if force_cols else card_cols(n)
    rows = ceil(n / cols)
    body_any = any(c.body.strip() for c in cards)
    cw = (region.width - _CARD_GAP * (cols - 1)) / cols
    raw_ch = (region.height - _CARD_GAP * (rows - 1)) / rows
    if not body_any:  # 全是纯标题卡:用紧凑高度排布,不留巨洞
        ch = _CARD_COMPACT_H
    elif rows == 1:
        ch = min(raw_ch, _CARD_MAX_ROW_H)
    else:
        ch = raw_ch
    used_h = ch * rows + _CARD_GAP * (rows - 1)
    # 单行靠上对齐(贴近标题),多行整体垂直居中
    top0 = region.top if rows == 1 else region.top + max(0.0, region.height - used_h) / 2
    for i, card in enumerate(cards):
        r, c = divmod(i, cols)
        cl = region.left + c * (cw + _CARD_GAP)
        ct = top0 + r * (ch + _CARD_GAP)
        has_body = bool(card.body.strip())
        card_h = ch if has_body else min(ch, _CARD_COMPACT_H)
        out.append(RenderSlot(f"card_{i}.bg", "", Rect(left=cl, top=ct, width=cw, height=card_h), "shape", shape_role="card"))
        # 圆形徽章(母题):左上角,编号或图标
        badge_h = min(card_h * 0.36, 0.085)
        badge = _circle(cl + _CARD_PAD_X, ct + _CARD_PAD_Y, badge_h)
        out.append(RenderSlot(f"card_{i}.badge", "", badge, "shape", shape_role="card_badge"))
        # 徽章内容:能解析出真实图标 PNG → 图标(on_primary 色压在 primary 圆上);否则编号/字形。
        icon_key = icon_for(card.icon or card.title, "card") if icon_for else None
        if icon_key:
            out.append(
                RenderSlot(f"card_{i}.icon", icon_key, _inset(badge, 0.56), "image", color_role="on_primary")
            )
        else:
            out.append(
                RenderSlot(
                    f"card_{i}.badgetext", _card_badge_label(card, i), badge,
                    "text", "h2", "on_primary", "center", "middle",
                )
            )
        # 标题在徽章右侧、与之同高居中
        tl = badge.left + badge.width + 0.014
        tw = max(0.04, cl + cw - _CARD_PAD_X - tl)
        if has_body:
            out.append(
                RenderSlot(
                    f"card_{i}.title", card.title,
                    Rect(left=tl, top=ct + _CARD_PAD_Y, width=tw, height=badge_h),
                    "text", "h2", valign="middle",
                )
            )
            body_top = ct + _CARD_PAD_Y + badge_h + 0.022
            out.append(
                RenderSlot(
                    f"card_{i}.body", card.body,
                    Rect(left=cl + _CARD_PAD_X, top=body_top, width=cw - _CARD_PAD_X * 2,
                         height=max(0.04, ct + card_h - _CARD_PAD_Y - body_top)),
                    "text", "body", "text_muted",
                )
            )
        else:
            out.append(
                RenderSlot(
                    f"card_{i}.title", card.title,
                    Rect(left=tl, top=ct + card_h / 2 - badge_h / 2, width=tw, height=badge_h),
                    "text", "h2", valign="middle",
                )
            )
    return out


# ── 列表行(agenda/summary):卡片化行 + 圆徽章,替代裸 bullet ──────
_ROW_GAP = 0.02
_ROW_PAD_X = 0.024
_ROW_MAX_H = 0.16  # 行高上限:条目少时不撑成巨条,保留留白


def _list_cols(n: int) -> int:
    """目录/小结列数:≤4 单列(整行更易读)、≥5 双列(填满横向、压缩纵向稀疏)。"""
    return 1 if n <= 4 else 2


def _expand_list_rows(
    items: list[str], region: Rect, icon_for: IconResolver | None
) -> list[RenderSlot]:
    """字符串列表 → 「卡片行 + 左侧圆徽章(语义图标优先,否则编号)+ 文本」。

    替代过去的裸 bullet:每行一张浅彩卡面 + primary 圆徽章(母题,与卡片页一致),
    徽章内放语义图标(icon_for 命中)或序号;文本在徽章右侧垂直居中。整体在区域内
    垂直居中、行高设上限,避免条目少时撑成巨条或顶部黑字堆叠。
    """
    out: list[RenderSlot] = []
    n = len(items)
    if n == 0:
        return out
    cols = _list_cols(n)
    rows = ceil(n / cols)
    cw = (region.width - _ROW_GAP * (cols - 1)) / cols
    ch = min((region.height - _ROW_GAP * (rows - 1)) / rows, _ROW_MAX_H)
    used_h = ch * rows + _ROW_GAP * (rows - 1)
    top0 = region.top + max(0.0, region.height - used_h) / 2  # 整体垂直居中
    badge_h = min(ch * 0.5, 0.075)
    text_role: FontRole = "h2" if cols == 1 else "body"
    for i, text in enumerate(items):
        r, c = divmod(i, cols)
        cl = region.left + c * (cw + _ROW_GAP)
        ct = top0 + r * (ch + _ROW_GAP)
        out.append(
            RenderSlot(
                f"row_{i}.bg", "", Rect(left=cl, top=ct, width=cw, height=ch),
                "shape", shape_role="card",
            )
        )
        badge = _circle(cl + _ROW_PAD_X, ct + (ch - badge_h) / 2, badge_h)
        out.append(RenderSlot(f"row_{i}.badge", "", badge, "shape", shape_role="card_badge"))
        # 语义图标(on_primary 压在 primary 圆上)优先;无命中退序号(目录序也是语义)。
        icon_key = icon_for(text, "card") if icon_for else None
        if icon_key:
            out.append(
                RenderSlot(f"row_{i}.icon", icon_key, _inset(badge, 0.56), "image", color_role="on_primary")
            )
        else:
            out.append(
                RenderSlot(
                    f"row_{i}.badgetext", str(i + 1), badge,
                    "text", "h2", "on_primary", "center", "middle",
                )
            )
        tl = badge.left + badge.width + 0.016
        tw = max(0.04, cl + cw - _ROW_PAD_X - tl)
        out.append(
            RenderSlot(
                f"row_{i}.text", text, Rect(left=tl, top=ct, width=tw, height=ch),
                "text", text_role, valign="middle",
            )
        )
    return out


# ── 对比页(comparison):左右对称面板 + 圆徽章 + 要点 + 中缝 VS ──────
_CMP_MARGIN = 0.06  # 页左右边距
_CMP_GAP = 0.04  # 两栏中缝(VS 落其中)
_CMP_TOP = 0.24  # 面板顶(标题之下)
_CMP_BOTTOM = 0.88  # 面板底
_CMP_PAD_X = 0.028
_CMP_PAD_Y = 0.05
_CMP_BADGE_H = 0.085
_CMP_VS_H = 0.12
_CMP_HEAD_GAP = 0.03  # 标题与要点之间的间距
# 字体无关的密度启发式(布局级常数,与主题无关,同 grid/gap):估算要点所需高度,
# 让面板贴合内容、左右对称、在带内垂直居中;字号最终由 renderer 自适应,故估偏大也只是留白、绝不溢出。
_CMP_NOMINAL_CPL = 56.0  # 满画布宽 ~16pt 正文每行字数当量
_CMP_LINE_H = 0.040  # 每行归一化高度(~16pt×1.3)
_CMP_MIN_PANEL = 0.30  # 面板最小高度,避免要点极少时过扁


def _panel_content_h(col: ComparisonColumn, text_w: float) -> float:
    """估算一栏(徽章+标题+要点)所需的归一化高度。len 作上界(CJK≈1),偏大→留白不溢出。"""
    cpl = max(6.0, _CMP_NOMINAL_CPL * text_w)
    lines = sum(max(1, ceil(len(p) / cpl)) for p in col.points) or 1
    return _CMP_PAD_Y * 2 + _CMP_BADGE_H + _CMP_HEAD_GAP + lines * _CMP_LINE_H


def _comparison_panel(
    prefix: str, col: ComparisonColumn, pl: float, pt: float, pw: float, ph: float,
    icon_for: IconResolver | None,
) -> list[RenderSlot]:
    """单栏面板:卡面(card)+ 左上圆徽章(母题:语义图标优先,否则标题首字)+ 标题 + 要点列表。

    与 cards 页同母题(圆形 primary 徽章 + 浅彩卡面),左右对称;要点走 list 文本槽,
    由 renderer 按框自适应字号 + 兜底截断,长要点不溢出面板。
    """
    out: list[RenderSlot] = []
    out.append(RenderSlot(f"{prefix}.bg", "", Rect(left=pl, top=pt, width=pw, height=ph), "shape", shape_role="card"))
    badge = _circle(pl + _CMP_PAD_X, pt + _CMP_PAD_Y, _CMP_BADGE_H)
    out.append(RenderSlot(f"{prefix}.badge", "", badge, "shape", shape_role="card_badge"))
    icon_key = icon_for(col.heading, "card") if icon_for else None
    if icon_key:
        out.append(RenderSlot(f"{prefix}.icon", icon_key, _inset(badge, 0.56), "image", color_role="on_primary"))
    else:
        out.append(
            RenderSlot(
                f"{prefix}.badgetext", (col.heading[:1] or "•"), badge,
                "text", "h2", "on_primary", "center", "middle",
            )
        )
    hl = badge.left + badge.width + 0.016
    hw = max(0.04, pl + pw - _CMP_PAD_X - hl)
    out.append(
        RenderSlot(
            f"{prefix}.heading", col.heading,
            Rect(left=hl, top=pt + _CMP_PAD_Y, width=hw, height=_CMP_BADGE_H),
            "text", "h2", valign="middle",
        )
    )
    pts_top = pt + _CMP_PAD_Y + _CMP_BADGE_H + _CMP_HEAD_GAP
    out.append(
        RenderSlot(
            f"{prefix}.points", col.points,
            Rect(left=pl + _CMP_PAD_X, top=pts_top, width=pw - _CMP_PAD_X * 2,
                 height=max(0.04, pt + ph - _CMP_PAD_Y - pts_top)),
            "list", "body",
        )
    )
    return out


def _expand_comparison(
    slide: ComparisonSlide, layout: LayoutSpec, icon_for: IconResolver | None
) -> list[RenderSlot]:
    """对比页全套槽:标题 + 左右对称面板 + 中缝 VS 圆徽章。VS 用浅底 accent 描边圆 + accent 文字。

    面板高度按两栏内容密度取较大者(对称),在 [0.24,0.88] 带内垂直居中,贴合内容、不溢出。
    """
    out: list[RenderSlot] = []
    title_spec = layout.slots.get("title")
    if title_spec is not None:
        out.append(RenderSlot.from_spec("title", slide.title, title_spec))
    pw = (1 - 2 * _CMP_MARGIN - _CMP_GAP) / 2
    text_w = pw - _CMP_PAD_X * 2
    band_h = _CMP_BOTTOM - _CMP_TOP
    need = max(_panel_content_h(slide.left, text_w), _panel_content_h(slide.right, text_w))
    ph = max(_CMP_MIN_PANEL, min(band_h, need))
    pt = _CMP_TOP + max(0.0, band_h - ph) / 2
    out.extend(_comparison_panel("left", slide.left, _CMP_MARGIN, pt, pw, ph, icon_for))
    out.extend(
        _comparison_panel("right", slide.right, _CMP_MARGIN + pw + _CMP_GAP, pt, pw, ph, icon_for)
    )
    # 中缝 VS:浅底 + accent 描边圆(num_badge 母题)压在两栏之间,accent 文字居中
    vs_w = _CMP_VS_H / _CANVAS_ASPECT
    cy = pt + ph / 2
    vs_rect = Rect(left=0.5 - vs_w / 2, top=cy - _CMP_VS_H / 2, width=vs_w, height=_CMP_VS_H)
    out.append(RenderSlot("vs.badge", "", vs_rect, "shape", shape_role="num_badge"))
    out.append(RenderSlot("vs", "VS", vs_rect, "text", "h2", "accent", "center", "middle"))
    return out


def _split_v(cell: Rect, top_frac: float) -> tuple[Rect, Rect]:
    th = cell.height * top_frac
    top = Rect(left=cell.left, top=cell.top, width=cell.width, height=th)
    bot = Rect(left=cell.left, top=cell.top + th, width=cell.width, height=cell.height - th)
    return top, bot


def _split_h(cell: Rect, left_frac: float) -> tuple[Rect, Rect]:
    lw = cell.width * left_frac
    left = Rect(left=cell.left, top=cell.top, width=lw, height=cell.height)
    right = Rect(left=cell.left + lw, top=cell.top, width=cell.width - lw, height=cell.height)
    return left, right


# ── 固定槽位:每种 type 的内容字段 → 槽位名 ──────────────────────
def _fixed_pairs(slide: SlideSpec) -> Iterator[tuple[str, SlotValue]]:
    if isinstance(slide, CoverSlide):
        yield "title", slide.title
        if slide.kicker:
            yield "kicker", slide.kicker
        if slide.subtitle:
            yield "subtitle", slide.subtitle
    elif isinstance(slide, AgendaSlide):
        yield "title", slide.title
        # items 由 repeat 展开为「卡片行 + 圆徽章 + 图标/编号」(见 _expand_list_rows)
    elif isinstance(slide, SectionSlide):
        yield "section_no", str(slide.section_number)
        yield "title", slide.title
        if slide.subtitle:
            yield "subtitle", slide.subtitle
    elif isinstance(slide, BigIdeaSlide):
        yield "statement", slide.statement
        if slide.support:
            yield "support", slide.support
    elif isinstance(slide, DataSlide):
        yield "title", slide.title
        if slide.note:
            yield "note", slide.note
    elif isinstance(slide, QuoteSlide):
        yield "quotemark", "“"  # 装饰大引号(无该布局槽位则自动跳过)
        yield "quote", slide.quote
        if slide.attribution:
            yield "attribution", slide.attribution
    elif isinstance(slide, SummarySlide):
        yield "title", slide.title
        # points 由 repeat 展开为「卡片行 + 圆徽章 + 图标/编号」(见 _expand_list_rows)
    elif isinstance(slide, ClosingSlide):
        if slide.title:
            yield "title", slide.title
        if slide.subtitle:
            yield "subtitle", slide.subtitle
        if slide.cta:
            yield "cta", slide.cta
    elif isinstance(slide, CardsSlide | TimelineSlide | ProcessSlide):
        yield "title", slide.title


# ── 可变数量内容:在 repeat 区域内展开 ──────────────────────────
def _expand_repeat(
    slide: SlideSpec, region: Rect, icon_for: IconResolver | None = None,
    layout: LayoutSpec | None = None,
) -> list[RenderSlot]:
    out: list[RenderSlot] = []
    if isinstance(slide, AgendaSlide):
        out.extend(_expand_list_rows(slide.items, region, icon_for))
    elif isinstance(slide, SummarySlide):
        out.extend(_expand_list_rows(slide.points, region, icon_for))
    elif isinstance(slide, CardsSlide):
        force = 2 if layout is not None and layout.id == "cards_2up" else None
        out.extend(_expand_cards(slide.cards, region, icon_for, force))
    elif isinstance(slide, TimelineSlide):
        # 横轴 + 节点跨轴排布:时间(accent)+标题在上、圆点落轴上、描述在下。
        events = slide.events
        n = len(events)
        cells = row_rects(region, n)
        axis_y = region.top + region.height * 0.55
        dot_h = 0.024
        # 主轴(先画 → 落在节点/文字下)
        out.append(
            RenderSlot(
                "tl.axis", "",
                Rect(left=region.left + 0.02, top=axis_y - 0.002, width=region.width - 0.04, height=0.004),
                "shape", color_role="primary", shape_role="axis_line",
            )
        )
        for i, (cell, ev) in enumerate(zip(cells, events, strict=True)):
            dot_role: ColorRole = "accent" if i == n - 1 else "primary"
            out.append(
                RenderSlot(f"event_{i}.time", ev.time,
                           Rect(left=cell.left, top=region.top, width=cell.width, height=0.06),
                           "text", "h2", "accent", "center")
            )
            out.append(
                RenderSlot(f"event_{i}.title", ev.title,
                           Rect(left=cell.left, top=region.top + 0.07, width=cell.width, height=0.085),
                           "text", "body", "text", "center")
            )
            cx = cell.left + cell.width / 2
            dot = _circle(cx - (dot_h / _CANVAS_ASPECT) / 2, axis_y - dot_h / 2, dot_h)
            out.append(RenderSlot(f"event_{i}.dot", "", dot, "shape", color_role=dot_role, shape_role="node_dot"))
            if ev.desc:
                out.append(
                    RenderSlot(f"event_{i}.desc", ev.desc,
                               Rect(left=cell.left, top=axis_y + 0.035, width=cell.width,
                                    height=max(0.04, region.top + region.height - (axis_y + 0.035))),
                               "text", "caption", "text_muted", "center")
                )
    elif isinstance(slide, ProcessSlide):
        steps = slide.steps
        n = len(steps)
        cells = row_rects(region, n)
        badge_h = min(region.height * 0.42, 0.12)
        # 连接线(先画 → 落在编号徽章下):从首徽章中心连到末徽章中心
        if n >= 2:
            x0 = cells[0].left + cells[0].width / 2
            x1 = cells[-1].left + cells[-1].width / 2
            out.append(
                RenderSlot("proc.rule", "",
                           Rect(left=x0, top=region.top + badge_h / 2 - 0.0015, width=x1 - x0, height=0.003),
                           "shape", shape_role="rule")
            )
        for i, (cell, st) in enumerate(zip(cells, steps, strict=True)):
            # 圆形编号徽章(母题)在上、步骤正文在下,版式更有视觉锚点
            badge = _circle(cell.left + (cell.width - badge_h / _CANVAS_ASPECT) / 2, cell.top, badge_h)
            body_rect = Rect(
                left=cell.left, top=cell.top + badge_h + 0.02,
                width=cell.width, height=max(0.04, cell.height - badge_h - 0.02),
            )
            label = st.title if not st.desc else f"{st.title}: {st.desc}"
            out.append(RenderSlot(f"step_{i}.badge", "", badge, "shape", shape_role="num_badge"))
            # 步骤标题能解析出真实图标 → accent 色图标压在浅底圆上;否则保留序号(序号本身有顺序语义)。
            icon_key = icon_for(st.title, "process") if icon_for else None
            if icon_key:
                out.append(
                    RenderSlot(f"step_{i}.icon", icon_key, _inset(badge, 0.52), "image", color_role="accent")
                )
            else:
                out.append(
                    RenderSlot(f"step_{i}.num", str(i + 1), badge, "text", "h2", "accent", "center", "middle")
                )
            out.append(RenderSlot(f"step_{i}.title", label, body_rect, "text", "body", "text", "center"))
    elif isinstance(slide, DataSlide):
        for i, (cell, m) in enumerate(
            zip(row_rects(region, len(slide.metrics)), slide.metrics, strict=True)
        ):
            top, bot = _split_v(cell, 0.6)
            out.append(RenderSlot(f"metric_{i}.bg", "", cell, "shape", shape_role="metric"))
            value = m.value if not m.delta else f"{m.value} ({m.delta})"
            out.append(
                RenderSlot(
                    f"metric_{i}.value", value, top, "metric", "display", "primary", "center"
                )
            )
            out.append(
                RenderSlot(
                    f"metric_{i}.label", m.label, bot, "text", "caption", "text_muted", "center"
                )
            )
    return out


def map_slots(
    slide: SlideSpec, layout: LayoutSpec, icon_for: IconResolver | None = None
) -> list[RenderSlot]:
    """产出该页的全部 RenderSlot(固定槽 + 展开的可变槽)。

    icon_for(可选,由 renderer 注入):把卡片/流程的语义关键词解析成真实图标 PNG 的
    object_key;为 None 或无命中时回退现有圆形徽章(编号/字形),整链路不依赖图标库存在。
    """
    if isinstance(slide, ComparisonSlide):
        return _expand_comparison(slide, layout, icon_for)
    out: list[RenderSlot] = []
    for name, value in _fixed_pairs(slide):
        spec = layout.slots.get(name)
        if spec is not None:
            out.append(RenderSlot.from_spec(name, value, spec))
    if layout.repeat_slot and (region := layout.slots.get(layout.repeat_slot)):
        out.extend(_expand_repeat(slide, region.rect, icon_for, layout))
    return out
