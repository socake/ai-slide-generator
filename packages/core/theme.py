"""ThemeSpec = 一套实例化的设计令牌(Design Token),见 DATA_MODEL §3。

美观度来自一致的设计系统,而非魔法字符串。Theme preset 存 templates/themes/*.json,
ThemeEngine 按 deck_type + audience 选取。
"""

from __future__ import annotations

from pydantic import BaseModel

from packages.core.enums import BackgroundStyle, FooterStyle, ShapeStyle


class Palette(BaseModel):
    primary: str  # 主色 (hex)
    secondary: str
    accent: str  # 强调/点缀
    background: str  # 页面底
    surface: str  # 卡片/容器底
    text: str  # 正文
    text_muted: str  # 次要文字
    border: str


class TypeScale(BaseModel):
    """字号阶梯(pt),renderer 直接用。"""

    display: float = 54  # cover 大标题
    h1: float = 36  # 页标题
    h2: float = 24  # 卡片/小节标题
    body: float = 16
    caption: float = 12
    line_height: float = 1.25


class Fonts(BaseModel):
    heading: str  # 字体族名(需保证渲染环境已安装,见 RENDERING)
    body: str


class Spacing(BaseModel):
    """归一化间距阶梯(相对画布短边)。"""

    unit: float = 0.012
    xs: float = 0.012
    s: float = 0.024
    m: float = 0.040
    l: float = 0.064  # noqa: E741 — 设计令牌阶梯名(xs/s/m/l/xl),保持与 DATA_MODEL 一致
    xl: float = 0.096


class Grid(BaseModel):
    columns: int = 12
    margin: float = 0.06  # 页边距(归一化)
    gutter: float = 0.02  # 列间距


class ThemeSpec(BaseModel):
    id: str  # theme preset id, e.g. "exec_dark"
    name: str
    mood: list[str]  # ["serious","executive"] 用于素材匹配
    palette: Palette
    fonts: Fonts
    type_scale: TypeScale = TypeScale()
    spacing: Spacing = Spacing()
    grid: Grid = Grid()
    shape_style: ShapeStyle = "rounded"
    background_style: BackgroundStyle = "solid"
    footer_style: FooterStyle = "minimal"
