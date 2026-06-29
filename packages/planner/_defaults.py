"""中性占位主题。Planner 先塞这个,ThemeEngine(迭代4)再按 deck_type 替换 deck.theme。"""

from __future__ import annotations

from packages.core import Fonts, Palette, ThemeSpec


def neutral_theme() -> ThemeSpec:
    """一套安全的中性主题,仅作占位,保证 DeckSpec 始终合法可渲染。"""
    return ThemeSpec(
        id="neutral",
        name="Neutral (placeholder)",
        mood=["neutral"],
        palette=Palette(
            primary="#2563eb",
            secondary="#1e40af",
            accent="#f59e0b",
            background="#ffffff",
            surface="#f8fafc",
            text="#0f172a",
            text_muted="#64748b",
            border="#e2e8f0",
        ),
        fonts=Fonts(heading="Inter", body="Inter"),
    )
