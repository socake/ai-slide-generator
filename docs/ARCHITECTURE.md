# 系统架构 · ARCHITECTURE

> 本文定义系统分层、数据流与最重要的一条边界：**生成内核零基础设施依赖**。
> 领域模型见 [DATA_MODEL](DATA_MODEL.md)，生成编排见 [GENERATION_PIPELINE](GENERATION_PIPELINE.md)。

---

## 1. 分层与数据流

单进程、同步：一条命令从 JSON 输入直跑到 `.pptx` 输出，不依赖任何服务。

```
input.json
   │
   ▼
 cli.py  (适配器：只做 I/O 与参数解析)
   │  调用
   ▼
┌──────────────────────────────────────────────┐
│ packages/  生成内核 (零基础设施依赖)            │
│   Plan / Compose (LLM) → DeckSpecValidator     │
│   → ThemeEngine → LayoutEngine → AssetEngine   │  (确定性)
│   → PPTXRenderer                               │
└──────────────────────────────────────────────┘
   │  GenerationResult (deck_spec + pptx 字节 + benchmark)
   ▼
 output.pptx + deck_spec.json + benchmark.json
```

数据流（一次生成）：`读输入 JSON → 校验 → Plan 出叙事大纲与页面骨架 → Compose 逐 section 扩写正文 → DeckSpecValidator 收口 → 选主题/布局/素材(确定性) → 渲染成 pptx 字节 → 写文件`。

---

## 2. ★ 核心边界：`packages/` 零基础设施依赖

**纪律**：`packages/**` 只吃 `spec/config`、只吐 `GenerationResult`（spec + 字节），不碰文件系统/网络/外部存储。

为什么这条决定整套架构：

- **可独立直跑**：CLI 无需起任何服务，一条命令就能从 JSON 出 pptx——招聘验收用例直接成立。
- **可测试**：内核是“spec/config 进、spec/字节出”的纯逻辑，单测不需要任何中间件（见 `tests/`）。
- **可扩展**：内核对运行环境零假设——要嵌入任何调用场景，内核一行不改，存储/并发/持久化都由外层以依赖倒置注入。

落地方式（依赖倒置）：

- 内核产出**字节**（`pptx_bytes` / `preview_png`），由调用方决定如何落盘/分发。
- 需要“读素材/缓存”时，内核接收一个接口（Protocol），由调用方注入实现：CLI 注入本地文件实现。
- LLM provider 同样可注入：默认 `MockLLMProvider`（离线、零成本），`--provider` 切真实模型。

---

## 3. LLM 只在两步，其余全确定性

| 阶段 | 是否 LLM | 说明 |
|---|---|---|
| Plan | ✅ | 意图识别 + 叙事线 + 每页骨架（1 次调用，结构化输出） |
| Compose | ✅ | 逐 section 扩写 typed 正文（~6 次调用） |
| DeckSpecValidator | ❌ | 结构校验 + 定点修复，失败页骨架兜底 |
| ThemeEngine / LayoutEngine / AssetEngine | ❌ | 按 `deck_type` / `slide_type` 规则选主题/布局/素材 |
| PPTXRenderer | ❌ | 组件库 + Design Token → python-pptx → 字节 |

把“美术决策”从 LLM 手里拿走、固化进 theme preset 与组件库，是风格一致、成本/速度可控的根本（详见 GENERATION_PIPELINE 与 RENDERING）。

---

## 4. revise 单页修改的一致性

单页修改不能破坏整体风格/叙事：

- **theme 不变**：revise 只改该页 `SlideSpec` 内容，`DeckSpec.theme` 与其它页不动 → 风格天然一致。
- **只 relayout 该页**：重选/复用该页 LayoutSpec，不触碰其它页。
- **叙事保护**：revise 注入该页在 `narrative` 中的角色（属于哪个 progression 段），避免改飞脱离上下文。

---

## 5. 目录结构与职责

| 目录 | 职责 | 依赖基础设施？ |
|---|---|---|
| `packages/core` | 领域模型（DeckSpec…）、Protocol 接口 | ❌ |
| `packages/llm` | LLMProvider 实现 + 成本表 | ❌（只 HTTP） |
| `packages/planner` | Plan / Compose / prompts / 校验 | ❌ |
| `packages/theme_engine` `layout_engine` `asset_engine` | 规则化主题 / 布局 / 素材 | ❌ |
| `packages/renderer` | 组件库 + pptx + 预览 | ❌（LibreOffice 为外部进程） |
| `packages/benchmark` | cost / 时延采集 | ❌ |
| `cli.py` | CLI 适配器（I/O 与参数解析） | ❌ |
| `templates/` `assets/` | 预设主题 / 素材库 + 索引 | — |
| `examples/` `demos/` | 公开输入 / 产出与实测 | — |

> 基础设施依赖只允许出现在适配器层（`cli.py`）。这一栏就是架构 review 的检查表。
