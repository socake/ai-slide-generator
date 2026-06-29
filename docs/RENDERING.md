# 渲染与美观规格 · RENDERING

> 美观度的**上限**由本文决定。核心是把"精调过的版式"封装成**参数化组件**,用 Design Token 驱动,而不是让代码到处写魔法坐标。

---

## 1. 渲染路线取舍(先拍板)

| 方案 | 美观度上限 | 可编辑性 | 可变内容适配 | 结论 |
|---|---|---|---|---|
| A. python-pptx 程序化绘制 + **组件库** | 中高(取决于组件打磨) | ✅ 原生可编辑 pptx | ✅ 数据驱动 | **选它** |
| B. 外部设计师 .pptx **母版填槽** | 高(单页) | ✅ | ❌ 固定槽位,难适配 2/3/4 卡、3-6 节点 | 作为 A 的素材来源,不作主渲染 |
| C. HTML/SVG 渲染成图片再嵌入 | 很高 | ❌ 变成图片,不可编辑 | ✅ | 放弃(题目要"可正常打开/可编辑") |

**决策:走 A。** "代码即母版" —— 把版式沉淀进组件(精调的留白、对齐、字阶),而非散落在渲染逻辑里。B 的母版可作为背景/装饰素材进 `assets/`,但版式骨架由组件掌控,这样才能数据驱动地适配可变数量内容(`repeat_slot`)。

> 美观度的工程纪律:**少即是好**。强排版网格、克制配色(theme preset 已定)、充足留白(spacing token)、统一字阶 —— 默认 python-pptx 的丑来自堆元素和默认样式,组件库就是用来消除默认样式的。

---

## 2. 渲染主循环

```
render(deck: DeckSpec, asset: AssetSpec) -> pptx_bytes:
  prs = new_presentation(16:9)
  for slide in deck.slides:
      layout = LayoutEngine.pick(slide)              # LayoutSpec
      bindings = asset.for_slide(slide.id)
      page = prs.add_slide(blank)
      Background.render(page, deck.theme, bindings)   # z=底
      slots = slot_mapper.map(slide, layout)          # content -> {slot_name: value}
      for name, slot in layout.slots.items():
          comp = COMPONENTS[slot.kind]
          comp.render(page, rect=slot.rect, value=slots[name],
                      theme=deck.theme, slot=slot, binding=bindings)
      Footer.render(page, deck.theme, index=slide.index)
      PageNumber.render(page, deck.theme, index=slide.index)
  return save(prs)
```

每页一致的 Footer/PageNumber/配色/字体由这里统一兜底 —— **renderer 不接受逐页随机样式**,这是风格一致性的最后一道闸。

---

## 3. 组件库接口(`packages/renderer/components.py`)

```python
class Component(Protocol):
    def render(self, page, *, rect: Rect, value, theme: ThemeSpec,
               slot: SlotSpec, binding: AssetBinding | None = None) -> None: ...
```

组件清单(每个都吃 theme token,自带留白与对齐,绝不硬编码颜色字号):

| 组件 | 用于 | 要点 |
|---|---|---|
| `Background` | 所有页 | solid / subtle_gradient / image+overlay;读 `needs_overlay` |
| `TitleBlock` | 页标题 | font_role=h1,统一上边距与基线 |
| `BodyText` / `BulletList` | 正文/要点 | auto-fit(§4),bullet 用 theme 间距 |
| `CardGrid` | cards | 按 `len(cards)` 排 2/3/4 列,等距 gutter,surface 底+圆角 |
| `Timeline` | timeline | 轴线 + 节点,时间/标题/描述三层字阶 |
| `CompareColumns` | comparison | 左右对称,中缝分隔,heading 用 accent |
| `ProcessSteps` | process | 编号箭头流,步骤等宽 |
| `MetricRow` | data | 大号 value + label + delta(涨绿跌红或 theme accent) |
| `QuoteBlock` | quote | 大引号装饰,attribution 右对齐 muted |
| `IconShape` | icon 槽 | 语义图标名 → assets/icons 解析 |
| `Footer` / `PageNumber` / `SectionDivider` | 全局 | 统一品牌条/页码/章节号 |

---

## 4. 文字自适配(避免溢出毁版式)

槽位是固定矩形,文字长度不定 → 必须有 fit 策略,否则 python-pptx 文字会溢出框:

1. 估算文本在 `rect.width` 下的行数(字体度量近似)。
2. 若 ≤ `slot.max_lines`:正常渲染。
3. 若超:**先缩字号**(在 type_scale 下浮 1-2 档,有下限);仍超 → **截断 + 省略号**,并在 Validator 阶段反馈"该页内容应改短"(回到 GENERATION_PIPELINE §5 的定点修复)。
4. `valign` 控制垂直居中,短内容也不顶在框顶。

> 字数其实应在 Compose 阶段就由 prompt 约束(每页要点数/字数上限),渲染期 fit 只是兜底。两道防线。

---

## 5. Design Token → pptx 落地

| 规格 | pptx |
|---|---|
| `Palette.*` (hex) | `RGBColor.from_string(hex[1:])` |
| `TypeScale.*` (pt) | `Pt(size)` |
| `Rect` (0..1) | `Emu(round(v * 画布EMU))` |
| `Spacing.*` (0..1) | 同 Rect 折算 |
| `Fonts.heading/body` | `run.font.name`(渲染环境须装该字体,见 §6) |
| `shape_style=rounded` | 圆角矩形 autoshape;`sharp` 直角 |

---

## 6. 预览生成 + 字体一致性(经典坑,提前定)

- **pptx → PNG/PDF 用 LibreOffice headless**:`soffice --headless --convert-to pdf`,再 PDF→PNG(pdf2image/pymupdf)。
- **中文字体坑**:LibreOffice 容器/CI 默认无中文字体 → 预览图方块乱码。**渲染环境(本机/容器/CI)必须预装 Noto Sans CJK / 思源黑体**,且 `ThemeSpec.fonts` 只能从"已安装且跨 PowerPoint/Keynote 通用"的字体集里选(避免用户机器缺字体回退变形)。
- 字体集白名单写进 `templates/themes/`,theme preset 不得引用环境没有的字体。
- 预览只为快速查看,**不影响 pptx 本身**;pptx 用标准 OOXML shapes,保证 PowerPoint/Keynote 原生打开不依赖 LibreOffice。

---

## 7. 验收要点(对齐能力闭环 2)

- mock 一个 DeckSpec(不调 LLM)能渲出 pptx,PowerPoint/Keynote 正常打开。
- 12 种 slide_type 各有可用布局;页面尺寸统一 16:9。
- 字体/配色/标题层级/页脚跨页一致。
- 文字不溢出框;背景图上文字清晰(overlay/safe_area 生效)。
