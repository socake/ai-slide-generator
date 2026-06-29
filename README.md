# aippt

输入一段 JSON，生成**一套**（25–30 张）风格一致、有叙事线的 `.pptx`——不是一堆互相独立的卡片。

```json
{ "topic": "主题", "brief": "简介(≤500 字)", "audience": "目标受众" }
```

核心思路：**LLM 负责策划（产出结构化 `DeckSpec`），程序负责稳定输出（确定性渲染成 PPTX）**。
这样同时拿住三件事：风格一致、成本可控、生成速度可控。完整设计见 [`DESIGN.md`](DESIGN.md) 与 [`docs/`](#文档)。

## 快速开始

```bash
# 1) 依赖
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) 跑一个 demo —— 单条命令吃 JSON 吐 PPTX（默认 mock，离线、零成本、可复现）
python cli.py generate examples/python_intro.json out.pptx \
  --spec-out out.deck.json \
  --benchmark-out out.benchmark.json

# 3) 一次跑全部 5 套公开开发集
make demo
```

产物：`out.pptx`（可被 PowerPoint / Keynote 打开）、`out.deck.json`（结构化规格）、`out.benchmark.json`（成本/时延实测）。

## 接入真实 LLM

默认全程走 `MockLLMProvider`（离线、零成本、可复现）。要用真实模型生成内容，配好 key 后加 `--provider`：

```bash
cp .env.example .env        # 填入对应 key
export DEEPSEEK_API_KEY=sk-...
python cli.py generate examples/python_intro.json out.pptx --provider deepseek
# OpenAI:  --provider openai  --model gpt-4o-mini   (需 OPENAI_API_KEY)
# Claude:  --provider anthropic                     (需 ANTHROPIC_API_KEY)

# 用真实模型复现 5 套 demo 的成本/时延：
make demo PROVIDER=deepseek
```

provider 懒加载：不配 key、不加 `--provider` 时**绝不联网**，demo/测试零成本。成本与时延由 `benchmark.json` 实测；5 套真实数据见 [`DESIGN.md`](DESIGN.md) §5。

## 这套系统怎么跑（一眼版）

```
input.json
  → InputValidator → Plan(LLM：意图 + 叙事线 + 每页骨架)
  → Compose(LLM：逐 section 填内容) → DeckSpecValidator
  → ThemeEngine → LayoutEngine → AssetEngine(纯程序)
  → PPTXRenderer → output.pptx + deck_spec.json + benchmark.json
```

全程仅 **~7 次 LLM 调用**（1 次 Plan + ~6 次 Compose）；主题/布局/素材/渲染全是确定性程序——这是风格一致、成本/速度可控的根本。详见 [`docs/GENERATION_PIPELINE.md`](docs/GENERATION_PIPELINE.md)。

## 其它命令

```bash
python cli.py outline examples/python_intro.json          # 只看叙事大纲(不渲染,秒级)
python cli.py revise out.deck.json 5 out.pptx --instruction "更简洁"   # 单页重写(保全局一致)
```

## 目录

| 路径 | 职责 |
|---|---|
| `packages/` | 生成内核（零基础设施依赖）：`core` 模型 / `llm` provider / `planner` 策划 / `theme·layout·asset_engine` / `renderer` / `benchmark` |
| `cli.py` | CLI 适配器（单命令吃 JSON 吐 PPTX） |
| `templates/` `assets/` | 预设主题 / 素材库 |
| `examples/` `demos/` | 5 套公开输入 / 对应产出与实测 |
| `docs/` | 设计文档 |

## 工程质量

```bash
ruff check .          # lint
mypy packages         # 类型检查(只查生成内核)
pytest                # 测试(约 200 项;packages 覆盖率门槛 ≥ 80%)
make verify           # 一键:lint + typecheck + test + 5 套 demo
```

## 约束

不使用 Gamma / Tome / Beautiful.ai 等一键生成 SaaS；PPTX 由 `python-pptx` + 自研组件库渲染。密钥不进仓（见 `.gitignore` 与 `.env.example`）。

## 文档

| 文档 | 内容 |
|---|---|
| [DESIGN](DESIGN.md) | 决策日志：架构 / 模型选型 / 风格一致性 / 多样性 / 成本时延实测 / 取舍 / AI 协作复盘 / 自评分 |
| [docs/ARCHITECTURE](docs/ARCHITECTURE.md) | 系统分层 / 数据流 / 内核零依赖纪律 |
| [docs/DATA_MODEL](docs/DATA_MODEL.md) | 领域模型：DeckSpec / typed SlideSpec / Design Token |
| [docs/GENERATION_PIPELINE](docs/GENERATION_PIPELINE.md) | LLM 两段编排 / 结构化输出 / 校验降级 / Benchmark |
| [docs/RENDERING](docs/RENDERING.md) | 渲染路线 / 组件库 / 文字自适配 / 预览 |
