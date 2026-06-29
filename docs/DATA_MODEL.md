# 领域模型规格 · DATA_MODEL

> 这是整个系统的**地基**。`packages/core` 的 Pydantic 模型以本文为准;`planner` 产出它、`validator` 校验它、`theme/layout/asset/renderer` 消费它。
> 设计原则:**LLM 只产出"内容与意图"(DeckSpec),程序产出"位置与像素"(Layout+Theme+Render)**。二者通过**命名槽位(slot)**对接,这是风格一致与美观度的关键接缝。

本文补强了四处此前留空/过松的地方:
1. `SlideSpec` 按 `slide_type` 做 **typed content(可辨识联合)**,不再是扁平大杂烩;
2. 补全 `SlotSpec` / `ContentBlock`,打通 **内容 → 槽位 → 坐标** 链路;
3. 新增 **Design Token 层**,把 `ThemeSpec` 从魔法字符串下沉到可渲染的设计令牌;
4. `DeckSpec` 增加 `schema_version`,定义演进策略。

---

## 0. 坐标与单位约定(先定,后面都依赖它)

- 画布固定 **16:9**,逻辑尺寸 `13.333in × 7.5in`(= `12192000 × 6858000` EMU)。
- **规格层不出现 EMU**。所有位置用 **归一化矩形 `Rect`**:`left/top/width/height ∈ [0,1]`,相对画布。
- 只有 `renderer` 在最后一步把 `Rect × 画布EMU` 转成 python-pptx 的绝对坐标。
- 好处:布局与画布尺寸/渲染后端解耦;换 4:3 或换渲染器,布局规格不动。

```python
class Rect(BaseModel):
    left: float        # 0..1
    top: float         # 0..1
    width: float       # 0..1
    height: float      # 0..1
```

---

## 1. DeckSpec(根产物)

系统的核心中间产物,可序列化为 `deck_spec.json`。

```python
class DeckSpec(BaseModel):
    schema_version: str = "1.0"     # ★ 演进必备,见 §7
    id: str
    title: str
    topic: str
    brief: str
    audience: str
    purpose: str                    # IntentAnalyzer 推断的演示目的/类型
    deck_type: DeckType             # 见 §1.1,驱动主题与默认布局序列
    narrative: NarrativeSpec        # 整套叙事线(保证"一套"而非"一堆")
    theme: ThemeSpec                # 选定的视觉系统(§3)
    slides: list[SlideSpec]         # 25-30 张,见 §2
```

### 1.1 DeckType(意图 → 主题/布局基调)

`IntentAnalyzer` 把任意输入归一到有限演示稿类型,是**多样性**的源头(不同输入走不同基调,不像同模板填空):

```python
DeckType = Literal[
    "teaching",      # 教学课件     蓝白/清爽/代码块/步骤感
    "review",        # 年度复盘     暖色/手账/时间轴
    "consumer",      # 消费决策     标签/风味轮/对比
    "exec_report",   # CEO 汇报     深色/克制/强对比/少装饰
    "travel",        # 旅行攻略     米白/地图感/日式留白
    "product",       # 产品发布
    "pitch",         # 融资路演
    "tech",          # 技术方案
    "generic",       # 兜底
]
```

### 1.2 NarrativeSpec

```python
class NarrativeSpec(BaseModel):
    hook: str                 # 开场钩子
    conflict: str             # 张力/问题
    progression: list[str]    # 章节推进(每项对应一个 section 段落主旨)
    resolution: str           # 收束/行动
```

> `progression` 的长度 ≈ 章节数。`DeckPlanner` 先产出 NarrativeSpec,再据此分配 `slides`,确保有开头—展开—收尾的内在线索。

---

## 2. SlideSpec —— 按类型的 typed content(本文核心补强)

**反模式(原规划)**:所有 type 共用 `title/body/bullets/blocks/visual_hint` 扁平结构,`blocks: list[ContentBlock]` 兜底但 `ContentBlock` 未定义 → 渲染器只能 `if type==...` 猜内容。

**新设计**:可辨识联合(discriminated union),每种 `slide_type` 有自己的 content schema。渲染器拿到的是强类型数据,不猜。

### 2.1 公共基类

```python
class SlideBase(BaseModel):
    id: str
    index: int                          # 0-based 顺序
    type: SlideType                     # 判别字段
    title: str                          # 顶部标题(closing/quote 可空串)
    speaker_notes: str | None = None    # 讲稿
    layout_id: str | None = None        # 显式指定布局,否则 LayoutEngine 按 type 选默认
    asset_hint: str | None = None       # 给 AssetEngine 的检索提示(LLM 的 visual_hint)
    emphasis: Literal["low","normal","high"] = "normal"  # 影响留白/字号

SlideType = Literal[
    "cover","agenda","section","big_idea","cards",
    "timeline","comparison","process","data","quote","summary","closing",
]
```

### 2.2 各类型 content

```python
class CoverSlide(SlideBase):
    type: Literal["cover"] = "cover"
    subtitle: str | None = None
    kicker: str | None = None           # 标题上方的小字(主题/日期/作者)

class AgendaSlide(SlideBase):
    type: Literal["agenda"] = "agenda"
    items: list[str]                    # 目录项(通常等于各 section 标题)

class SectionSlide(SlideBase):
    type: Literal["section"] = "section"
    section_number: int
    subtitle: str | None = None

class BigIdeaSlide(SlideBase):
    type: Literal["big_idea"] = "big_idea"
    statement: str                      # 一句大字主张
    support: str | None = None          # 一行支撑

class Card(BaseModel):
    title: str
    body: str
    icon: str | None = None             # 语义图标名,AssetEngine 解析

class CardsSlide(SlideBase):
    type: Literal["cards"] = "cards"
    cards: list[Card]                   # 2-4 张,LayoutEngine 按数量选 2/3/4 列

class TimelineEvent(BaseModel):
    time: str
    title: str
    desc: str | None = None

class TimelineSlide(SlideBase):
    type: Literal["timeline"] = "timeline"
    events: list[TimelineEvent]         # 3-6 个节点

class ComparisonColumn(BaseModel):
    heading: str
    points: list[str]

class ComparisonSlide(SlideBase):
    type: Literal["comparison"] = "comparison"
    left: ComparisonColumn
    right: ComparisonColumn

class ProcessStep(BaseModel):
    title: str
    desc: str | None = None

class ProcessSlide(SlideBase):
    type: Literal["process"] = "process"
    steps: list[ProcessStep]            # 3-5 步

class Metric(BaseModel):
    value: str                          # "78%" / "3.2x" / "¥1.2M"
    label: str
    delta: str | None = None            # "+12%" 同比/环比

class DataSlide(SlideBase):
    type: Literal["data"] = "data"
    metrics: list[Metric]               # 数字卡;图表是后续扩展
    note: str | None = None

class QuoteSlide(SlideBase):
    type: Literal["quote"] = "quote"
    quote: str
    attribution: str | None = None

class SummarySlide(SlideBase):
    type: Literal["summary"] = "summary"
    points: list[str]

class ClosingSlide(SlideBase):
    type: Literal["closing"] = "closing"
    subtitle: str | None = None
    cta: str | None = None              # 行动号召/联系方式

SlideSpec = Annotated[
    CoverSlide | AgendaSlide | SectionSlide | BigIdeaSlide | CardsSlide
    | TimelineSlide | ComparisonSlide | ProcessSlide | DataSlide
    | QuoteSlide | SummarySlide | ClosingSlide,
    Field(discriminator="type"),
]
```

> **ContentBlock 去哪了?** 取消通用 `ContentBlock`。原本想用它兜底的富文本块,改由上面各 typed content 显式承载;真要"自由段落"用 `BigIdeaSlide`/`SummarySlide`。强类型 > 兜底大杂烩。

---

## 3. ThemeSpec + Design Token(本文核心补强)

**美观度的真正来源是一致的设计系统**,不是一句 `background_style="dark"`。`ThemeSpec` = 一套实例化的设计令牌。

```python
class Palette(BaseModel):
    primary: str        # 主色 (hex)
    secondary: str
    accent: str         # 强调/点缀
    background: str     # 页面底
    surface: str        # 卡片/容器底
    text: str           # 正文
    text_muted: str     # 次要文字
    border: str

class TypeScale(BaseModel):
    # 字号阶梯(pt),renderer 直接用
    display: float = 54     # cover 大标题
    h1: float = 36          # 页标题
    h2: float = 24          # 卡片/小节标题
    body: float = 16
    caption: float = 12
    line_height: float = 1.25

class Fonts(BaseModel):
    heading: str            # 字体族名(需保证渲染环境已安装,见 RENDERING)
    body: str

class Spacing(BaseModel):
    # 归一化间距阶梯(相对画布短边),布局与组件留白都引用
    unit: float = 0.012
    xs: float = 0.012
    s: float = 0.024
    m: float = 0.040
    l: float = 0.064
    xl: float = 0.096

class Grid(BaseModel):
    columns: int = 12
    margin: float = 0.06    # 页边距(归一化)
    gutter: float = 0.02    # 列间距

class ThemeSpec(BaseModel):
    id: str                 # theme preset id, e.g. "exec_dark"
    name: str
    mood: list[str]         # ["serious","executive"] 用于素材匹配
    palette: Palette
    fonts: Fonts
    type_scale: TypeScale = TypeScale()
    spacing: Spacing = Spacing()
    grid: Grid = Grid()
    shape_style: Literal["sharp","rounded","pill"] = "rounded"
    background_style: Literal["solid","subtle_gradient","image"] = "solid"
    footer_style: Literal["none","minimal","branded"] = "minimal"
```

> Theme preset 存 `templates/themes/*.json`,每个 `DeckType` 至少 1-2 套精调预设(配色/字体经过设计,而非随机)。`ThemeEngine` 按 `deck_type + audience` 选 preset,可微调 `palette`。**美观度优先靠"精调的有限预设",不靠 LLM 随机配色。**

---

## 4. LayoutSpec + SlotSpec(打通"内容→槽位→坐标")

布局是 `slide_type` 的版式定义:一组**命名槽位**,每个槽位有归一化位置 + 渲染约束。`slot_mapper` 把 typed content 的字段按约定塞进同名槽位,`renderer` 把槽位画出来。

```python
SlotKind = Literal["text","rich_text","list","image","icon","metric","shape","divider"]

class SlotSpec(BaseModel):
    name: str                       # 约定命名,见 §4.1
    kind: SlotKind
    rect: Rect                      # 归一化位置
    font_role: Literal["display","h1","h2","body","caption"] | None = None
    color_role: Literal["text","text_muted","primary","accent","on_primary"] = "text"
    align: Literal["left","center","right"] = "left"
    valign: Literal["top","middle","bottom"] = "top"
    max_lines: int | None = None    # 超出触发缩字号/截断策略(见 RENDERING)
    z: int = 0                      # 叠放次序(背景图在底层)

class LayoutSpec(BaseModel):
    id: str
    slide_type: SlideType
    name: str
    slots: dict[str, SlotSpec]      # key == SlotSpec.name
    repeat_slot: str | None = None  # 可重复槽位前缀(如 "card_"),供 cards/timeline 动态展开
```

### 4.1 槽位命名约定(slot_mapper 的契约)

| slide_type | content 字段 | 槽位 |
|---|---|---|
| cover | title/subtitle/kicker | `title` / `subtitle` / `kicker` |
| section | title/section_number | `title` / `section_no` |
| big_idea | statement/support | `statement` / `support` |
| cards | cards[i].{title,body,icon} | `card_{i}.title` / `card_{i}.body` / `card_{i}.icon` |
| timeline | events[i].{time,title,desc} | `event_{i}.time` / `event_{i}.title` / `event_{i}.desc` |
| comparison | left/right.{heading,points} | `left.heading`/`left.points` / `right.*` |
| process | steps[i] | `step_{i}.title` / `step_{i}.desc` |
| data | metrics[i] | `metric_{i}.value`/`.label`/`.delta` |

> `repeat_slot` 让一个布局适配可变数量(2/3/4 张卡片用同一族布局,`LayoutEngine` 据 `len(cards)` 选列数变体或等距排布)。**布局是数据驱动的,不是每个数量写死一个模板。**

---

## 5. AssetSpec(素材绑定 + 安全区)

`AssetEngine` 为需要素材的 slide 绑定背景/图标/插画,并带**安全区**约束文字避让。

```python
class AssetBinding(BaseModel):
    slide_id: str
    role: Literal["background","icon","illustration","decoration"]
    object_key: str                 # assets/ 相对路径(asset 引用)
    safe_area: Rect | None = None    # 文字应落在此区域内(背景图非空区在外)
    needs_overlay: bool = False      # 是否需压一层半透明遮罩以保证文字对比度
    overlay_opacity: float = 0.0

class AssetSpec(BaseModel):
    bindings: list[AssetBinding]
```

> 素材索引(`assets/asset_index.json`)字段约定:`asset_type / domain_tags / mood_tags / color_tags / best_slide_types / safe_area / needs_overlay`。匹配先用**规则(tag 交集打分)**,够用且可解释;向量检索作为后续增强。`renderer` 必须读 `safe_area` 收窄文字槽位、按 `needs_overlay` 叠遮罩——这是"图上有字也清楚"的保证。

---

## 6. GenerationResult(统一产物)

避免每个调用方各搞一套。一次生成 = 一个 `GenerationResult`,落地位置由调用方决定:CLI 写文件系统。

```python
class GenerationResult(BaseModel):
    deck_spec: DeckSpec
    pptx_bytes: bytes | None = None     # 渲染产物字节(由调用方决定落盘/分发)
    pdf_bytes: bytes | None = None
    preview_png: list[bytes] = []
    benchmark: BenchmarkReport          # 见 GENERATION_PIPELINE
```

---

## 7. schema_version 演进策略

- `DeckSpec.schema_version` 当前 `"1.0"`。
- 任何破坏性字段变更 → 升次版本,并在 `packages/core/migrations/` 加 `migrate_x_y(dict) -> dict`。
- 读取旧 `deck_spec.json` 时,按 version 链式升级到当前版本再 parse,保证老演示稿可重新渲染。
- 新增可选字段(带默认值)不升主版本。

---

## 校验清单(DeckSpecValidator 据此,详见 GENERATION_PIPELINE)

- 页数 ∈ [25,30];存在且唯一的 `cover` / `closing`;至少 1 个 `section`。
- `index` 连续无重复;无相邻重复页(同 type + 高度相似 title)。
- 各 typed content 数量约束(cards 2-4、timeline 3-6、process 3-5…)。
- 标题非空、正文不超长(超长触发改写或缩字号,不直接溢出)。
- `narrative.progression` 与 section 数量自洽。
- 整个对象可被 Pydantic 严格 parse(失败即触发修复重试)。
