from __future__ import annotations

from packages.core import QuoteSlide
from packages.layout_engine import LayoutEngine, map_slots


def test_quote_emits_decorative_mark() -> None:
    slide = QuoteSlide(id="q", index=0, title="金句", quote="大道至简", attribution="老子")
    slots = map_slots(slide, LayoutEngine().select("quote"))
    marks = [s for s in slots if s.name == "quotemark"]
    assert len(marks) == 1
    assert marks[0].value == "“"
    assert marks[0].color_role == "accent"
    # 引号、正文、署名都在
    names = {s.name for s in slots}
    assert {"quotemark", "quote", "attribution"} <= names
