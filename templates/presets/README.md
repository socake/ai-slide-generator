# 预制模板（Templates）

> 模板 = **一套确定性的"视觉 + 版式 + 槽位映射"预设**。LLM 只产出内容(DeckSpec)，模板负责把内容**回填**进固定的版式与配色，确定性渲染成 pptx。
> 这样保证：**单份内格式统一** + **同一模板下的系列演示稿风格一致**，且不每次靠 LLM 配色（更稳更省）。

## 回答三个核心问题

### 1. 我们产出什么数据
内核 Plan/Compose 产出 `DeckSpec`（见 `docs/DATA_MODEL.md`）：按 `type` 的可辨识联合 slides，每页是 typed content——
`cover{title,subtitle,kicker}` / `section{title,section_number,subtitle}` / `agenda{items[]}` / `summary{points[]}` /
`big_idea{statement,support}` / `cards{cards[{title,body}]}` / `comparison{left,right}` / `data{metrics[{value,label}]}` /
`process{steps[]}` / `timeline{events[]}` / `closing{subtitle,cta}`。
**内容与样式分离**：DeckSpec 只有内容（+ 可选元素级 `style` 覆盖），不含版式/配色决策。

### 2. 模板要做成什么样，才能支持回填 + 渲染
一个模板 = 三层（见 `presets.json` 每条）：
- **`theme`**：完整 `ThemeSpec`（palette 8 色 + fonts + type_scale）——决定配色与字阶，对齐 `packages/core` 的 ThemeSpec。
- **`layout`**：按 `SlideType` 指定**版式变体**（每类页用哪种排布：如 cards 用 2×2 还是横排、cover 居中还是左对齐、data 用大数字还是柱图）。是 `layout_engine` 的确定性参数，不是自由坐标。
- **`slot_map`**：DeckSpec 字段 → 模板槽位的映射（通常是恒等映射；模板可声明"本模板 data 页最多 3 个 metric""cards 固定 3 张"等约束，渲染时按约束裁/补——**但不塞占位**，不足就少）。

### 3. 模板的具体形式（生成时怎么用）
- 形式：**预设 JSON**（本目录 `presets.json`，未来可拆成单文件）。
- 生成时：`GenerationInput.template_id`
  - **不传** → 用 `baseline`（万金油基准），即默认。
  - **传了** → 用对应模板：**跳过 ThemeEngine 的自动选主题**，直接用 `template.theme`；`layout_engine` 读 `template.layout`；`renderer` 按 `slot_map` 回填。
- 已生成的 deck 换模板：传入新 `template_id` 重跑确定性**渲染**（内容不变、不重跑 LLM）。
## 模板清单（`presets.json`）
| id | 名称 | 场景 | 默认 |
|---|---|---|---|
| `baseline` | 万金油基准 | 适配各类场景的通用基准 | ✅ 未选时默认 |
| `tech_dark` | 科技深色 | 架构/技术分享 | |
| `business_clean` | 商务简洁 | 汇报/方案 | |
| `teaching_fresh` | 教学清新 | 课件/教程 | |
| `magazine` | 杂志编辑 | 品牌/故事 | |
| `pitch_bold` | 路演大胆 | 融资/发布路演 | |

## 落地状态
- 本目录是**结构与基线**：`baseline` 给全字段示例，其余 5 套给 theme + layout 关键参数。
- 真正执行渲染前需：① 把 `layout` 变体接进 `layout_engine`；② `renderer` 读 template.theme 覆盖默认；③ 校验模板约束。
