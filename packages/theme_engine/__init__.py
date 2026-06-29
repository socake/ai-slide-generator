"""packages.theme_engine —— 规则化选主题(零 LLM)。预设见 templates/themes/*.json。"""

from __future__ import annotations

from packages.theme_engine.engine import DECK_TYPE_PRESET, ThemeEngine
from packages.theme_engine.loader import load_themes

__all__ = ["ThemeEngine", "DECK_TYPE_PRESET", "load_themes"]
