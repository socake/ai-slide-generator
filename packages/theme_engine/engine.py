"""ThemeEngine:按 deck_type(+ audience)规则选主题预设,**不调 LLM**。

视觉令牌是数据(templates/themes/*.json),"哪种意图配哪套主题"是规则(本文件)。
这是风格一致与可控的关键:不让 LLM 每次随机配色。
"""

from __future__ import annotations

from pathlib import Path

from packages.core import Fonts, Palette, ThemeSpec
from packages.theme_engine.loader import load_themes

DEFAULT_THEMES_DIR = Path(__file__).resolve().parents[2] / "templates" / "themes"

# deck_type → 预设 stem。无对应者回落 "generic"。
DECK_TYPE_PRESET: dict[str, str] = {
    "teaching": "teaching",
    "tech": "tech_dark",
    "exec_report": "exec_report",
    "pitch": "pitch_bold",
    "product": "exec_report",
    "consumer": "consumer",
    "review": "review_warm",
    "travel": "travel_warm",
    "generic": "generic",
}

# 受众含这些线索 → 强制走克制的 exec 主题。
_EXEC_HINTS = ("高管", "ceo", "cfo", "董事", "投资", "leadership", "executive", "board")


def _fallback_theme() -> ThemeSpec:
    """无任何预设可用时的兜底中性主题(纯代码,自包含)。"""
    return ThemeSpec(
        id="fallback",
        name="Fallback Neutral",
        mood=["neutral"],
        palette=Palette(
            primary="#475569",
            secondary="#334155",
            accent="#2563eb",
            background="#ffffff",
            surface="#f8fafc",
            text="#0f172a",
            text_muted="#64748b",
            border="#e2e8f0",
        ),
        fonts=Fonts(heading="Noto Sans CJK SC", body="Noto Sans CJK SC"),
    )


class ThemeEngine:
    def __init__(self, themes_dir: Path | None = None) -> None:
        self._themes = load_themes(themes_dir or DEFAULT_THEMES_DIR)

    def select(self, deck_type: str, audience: str | None = None) -> ThemeSpec:
        """选定主题。返回深拷贝,调用方可安全微调而不污染预设缓存。"""
        stem = DECK_TYPE_PRESET.get(deck_type, "generic")
        if audience and any(h in audience.lower() for h in _EXEC_HINTS):
            stem = "exec_report"
        theme = self._themes.get(stem) or self._themes.get("generic") or _fallback_theme()
        return theme.model_copy(deep=True)
