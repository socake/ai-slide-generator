"""packages.renderer —— DeckSpec → .pptx 字节(确定性,零 LLM)。EMU 只在此出现。

预览(pptx→png)依赖系统级 LibreOffice/pdftoppm,缺失则优雅跳过。
"""

from __future__ import annotations

from packages.renderer.preview import preview_available, to_png
from packages.renderer.renderer import CANVAS_H, CANVAS_W, PPTXRenderer, render_deck

__all__ = ["PPTXRenderer", "render_deck", "CANVAS_W", "CANVAS_H", "to_png", "preview_available"]
