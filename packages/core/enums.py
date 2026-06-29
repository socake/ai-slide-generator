"""领域内的有限取值(Literal 别名),集中定义以便各包共用。"""

from __future__ import annotations

from typing import Literal

# 意图 → 主题/布局基调(多样性的源头),见 DATA_MODEL §1.1
DeckType = Literal[
    "teaching",
    "review",
    "consumer",
    "exec_report",
    "travel",
    "product",
    "pitch",
    "tech",
    "generic",
]

# 幻灯片判别字段,见 DATA_MODEL §2.1
SlideType = Literal[
    "cover",
    "agenda",
    "section",
    "big_idea",
    "cards",
    "timeline",
    "comparison",
    "process",
    "data",
    "quote",
    "summary",
    "closing",
]

# 槽位类型,见 DATA_MODEL §4
SlotKind = Literal["text", "rich_text", "list", "image", "icon", "metric", "shape", "divider"]

Emphasis = Literal["low", "normal", "high"]
FontRole = Literal["display", "h1", "h2", "body", "caption"]
ColorRole = Literal["text", "text_muted", "primary", "accent", "on_primary"]
Align = Literal["left", "center", "right"]
VAlign = Literal["top", "middle", "bottom"]
ShapeStyle = Literal["sharp", "rounded", "pill"]
BackgroundStyle = Literal["solid", "subtle_gradient", "image"]
FooterStyle = Literal["none", "minimal", "branded"]
AssetRole = Literal["background", "icon", "illustration", "decoration"]
LLMStep = Literal["plan", "compose", "repair"]
