from __future__ import annotations

from packages.core import AssetBinding, AssetSpec, LayoutSpec, Rect, SlotSpec


def test_slot_and_layout() -> None:
    slot = SlotSpec(name="title", kind="text", rect=Rect(left=0.1, top=0.1, width=0.8, height=0.2))
    assert slot.color_role == "text"
    assert slot.align == "left"
    assert slot.z == 0

    layout = LayoutSpec(
        id="cover_centered",
        slide_type="cover",
        name="Cover Centered",
        slots={"title": slot},
        repeat_slot=None,
    )
    assert layout.slots["title"].name == "title"
    assert layout.slide_type == "cover"


def test_asset_binding_and_spec() -> None:
    binding = AssetBinding(
        slide_id="s1",
        role="background",
        object_key="backgrounds/city.jpg",
        safe_area=Rect(left=0.05, top=0.5, width=0.5, height=0.4),
        needs_overlay=True,
        overlay_opacity=0.35,
    )
    assert binding.needs_overlay is True
    spec = AssetSpec(bindings=[binding])
    assert len(spec.bindings) == 1
    assert AssetSpec().bindings == []
