from __future__ import annotations

from packages.core import Fonts, Grid, Palette, Spacing, ThemeSpec, TypeScale


def _palette() -> Palette:
    return Palette(
        primary="#1a1a1a",
        secondary="#2b2b2b",
        accent="#e0533d",
        background="#ffffff",
        surface="#f5f5f5",
        text="#111111",
        text_muted="#666666",
        border="#dddddd",
    )


def test_theme_token_defaults() -> None:
    theme = ThemeSpec(
        id="exec_dark",
        name="Exec Dark",
        mood=["serious", "executive"],
        palette=_palette(),
        fonts=Fonts(heading="Inter", body="Inter"),
    )
    # 默认令牌(DATA_MODEL §3)
    assert theme.type_scale.display == 54
    assert theme.type_scale.line_height == 1.25
    assert theme.spacing.unit == 0.012
    assert theme.grid.columns == 12
    assert theme.shape_style == "rounded"
    assert theme.background_style == "solid"
    assert theme.footer_style == "minimal"


def test_theme_overrides() -> None:
    theme = ThemeSpec(
        id="t",
        name="t",
        mood=[],
        palette=_palette(),
        fonts=Fonts(heading="A", body="B"),
        type_scale=TypeScale(display=60),
        spacing=Spacing(unit=0.02),
        grid=Grid(columns=8),
        shape_style="sharp",
    )
    assert theme.type_scale.display == 60
    assert theme.grid.columns == 8
    assert theme.shape_style == "sharp"
