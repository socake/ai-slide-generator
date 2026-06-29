# 自检输出（self-check）

本目录是作者在本机用 **deepseek-chat 真实生成**（`degraded=false`，非 mock 占位）跑出的一套成品，作为**自检 / 效果与成本基准**留存。

## 为什么单独冻结一份

`make demo` 等重新生成命令只写 `demos/pptx · specs · benchmark`，可能被 mock 或新结果覆盖。
**本目录不是任何生成命令的输出目标**，因此始终冻结——无论将来生成成功与否、效果如何波动，这里都有一套可回看、可对比的真本。

## 内容

| 文件 | 主题 | 类型 |
|---|---|---|
| `pptx/Python入门30分钟.pptx` | Python 入门 30 分钟 | 教学 |
| `pptx/年度复盘.pptx` | 2025 我的年度复盘 | 复盘 |
| `pptx/如何挑选咖啡豆.pptx` | 如何挑选咖啡豆 | 教学 |
| `pptx/Rust重写订单系统.pptx` | Rust 重写订单系统 | 技术汇报 |
| `pptx/周末玩遍京都.pptx` | 周末两天玩遍京都 | 旅行 |

- `pptx/` —— 5 套成品演示稿（PowerPoint / Keynote / WPS 可开）。
- `specs/` —— 对应的结构化 `DeckSpec`（LLM 产出的中间规格，按输入名 `examples/<slug>` 命名）。
- `benchmark/` —— 对应的成本 / 时延 / 页数实测数据。

> 生成条件：provider = `deepseek-chat`（原生端点），日期 2026-06-29。成本 / 时延汇总见根目录 [`DESIGN.md`](../../DESIGN.md) §5。
