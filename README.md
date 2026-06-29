<h1 align="center">aippt · AI 演示稿生成器</h1>

<p align="center">
输入一段 JSON，生成<b>一套</b>（25–30 张）风格一致、有叙事线的 <code>.pptx</code>——不是一堆互相独立的卡片。
</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="tests" src="https://img.shields.io/badge/tests-197%20passing-brightgreen">
  <img alt="typed" src="https://img.shields.io/badge/mypy-strict-2a6db0">
  <img alt="llm" src="https://img.shields.io/badge/LLM-deepseek%20%7C%20openai%20%7C%20claude-7952b3">
</p>

> **核心思路**：LLM 负责策划（产出结构化 `DeckSpec`），程序负责稳定输出（确定性渲染成 PPTX）——同时拿住三件事：**风格一致、成本可控、生成速度可控**。

```json
{ "topic": "主题", "brief": "简介(≤500 字)", "audience": "目标受众" }
```

## ✨ 亮点

- 🎯 **风格一致靠程序锁死**：LLM 只产内容，配色 / 布局 / 字号全是 Design Token + 精调 theme preset，杜绝"这页深蓝那页天蓝"。
- 🌈 **不千篇一律**：8 种演示类型各有主题基调与布局序列，同一套系统、不同长相。
- 💰 **成本可控**：两段式编排锁定 ~7 次 LLM 调用，真实实测 ≈ **$0.02 / 套**（30 页，见 [DESIGN](DESIGN.md) §5）。
- 🔌 **多 provider 一键切**：deepseek / openai / claude；默认 `mock` 离线零成本、不联网。
- 🛟 **优雅降级**：LLM 超时 / 违例自动回退骨架兜底，永不中断出稿。
- 🧪 **197 项测试全绿**、`mypy` 严格类型、内核零基础设施依赖。

---

## 🚀 使用说明（先看这里）

### 1. 装依赖（Python ≥ 3.10）

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # 或: pip install -e ".[llm,dev]"
```

> 只需标准 Python 环境。`.pptx` 预览图（可选）依赖系统级 **LibreOffice**，缺失会自动跳过、不影响生成。

### 2. 跑一条命令：吃 JSON 吐 PPTX

```bash
# 默认 mock provider：离线、零成本、可复现，不联网、不需要任何 key
python cli.py generate examples/python_intro.json out.pptx \
  --spec-out out.deck.json \
  --benchmark-out out.benchmark.json
```

产物：`out.pptx`（PowerPoint / Keynote / WPS 可开）、`out.deck.json`（结构化规格）、`out.benchmark.json`（成本 / 时延实测）。

一次跑全部 5 套公开开发集：

```bash
make demo                                 # 默认 mock，离线零成本
```

### 3. 接入真实 LLM（API Key 怎么配）

默认全程走 `MockLLMProvider`，**不配 key 就绝不联网**。要用真实模型生成内容，配好 key 再加 `--provider`：

```bash
cp .env.example .env                      # 编辑 .env 填入对应 key（.env 已被 .gitignore，不进仓）
```

`.env` 里填（或直接 `export` 同名环境变量），三家任选其一：

| provider | 需要的环境变量 | 备注 |
|---|---|---|
| `deepseek` **（默认推荐）** | `DEEPSEEK_API_KEY` | 原生端点 `https://api.deepseek.com`；中文质感好、页数稳。可选 `DEEPSEEK_BASE_URL` 覆盖端点 |
| `openai` | `OPENAI_API_KEY` | 配 `--model gpt-4o-mini`；成本约低一半 |
| `anthropic` | `ANTHROPIC_API_KEY` | Claude |

```bash
export DEEPSEEK_API_KEY=sk-xxxxxxxx
python cli.py generate examples/python_intro.json out.pptx --provider deepseek

# 用真实模型复现 5 套 demo 的成本 / 时延：
make demo PROVIDER=deepseek
```

> provider 懒加载：不配 key、不加 `--provider` 时绝不联网，demo / 测试零成本。5 套真实实测数据见 [`DESIGN.md`](DESIGN.md) §5。

### 其它命令

```bash
python cli.py outline examples/python_intro.json                       # 只看叙事大纲(不渲染,秒级)
python cli.py revise out.deck.json 5 out.pptx --instruction "更简洁"     # 单页重写(保全局一致)
make cli IN=examples/kyoto_weekend.json OUT=out.pptx                    # Makefile 入口
```

---

## 📂 Demo：预生成样例（直接打开看效果）

`demos/` 下是 **5 套用 deepseek-chat 真实生成**的产物（`degraded=false`，非 mock 占位），clone 仓库后**无需联网、无需 key** 即可直接打开。

### 打开路径：`demos/pptx/`

直接双击，用 PowerPoint / Keynote / WPS 打开：

| 文件 | 主题 | 类型 |
|---|---|---|
| `demos/pptx/Python入门30分钟.pptx` | Python 入门 30 分钟 | 教学 |
| `demos/pptx/年度复盘.pptx` | 2025 我的年度复盘 | 复盘 |
| `demos/pptx/如何挑选咖啡豆.pptx` | 如何挑选咖啡豆 | 教学 |
| `demos/pptx/Rust重写订单系统.pptx` | Rust 重写订单系统 | 技术汇报 |
| `demos/pptx/周末玩遍京都.pptx` | 周末两天玩遍京都 | 旅行 |

> 例：clone 到本地后，演示稿就在 `<仓库目录>/demos/pptx/年度复盘.pptx`。

### 配套技术产物

另两个目录按输入名 `examples/<slug>` 命名，与上面的 pptx 一一对应：

- `demos/specs/<slug>.deck.json` —— 每套的结构化 `DeckSpec`（LLM 产出的中间规格，可被 `revise` 复用）。
- `demos/benchmark/<slug>.benchmark.json` —— 每套的成本 / 时延 / 页数实测原始数据。

> 想自己重新生成：`make demo PROVIDER=deepseek`（需先配 `DEEPSEEK_API_KEY`），会覆盖 `demos/pptx/` 下的同名文件。

---

## 🔧 这套系统怎么跑（一眼版）

```
input.json
  → InputValidator → Plan(LLM：意图 + 叙事线 + 每页骨架)
  → Compose(LLM：逐 section 填内容) → DeckSpecValidator
  → ThemeEngine → LayoutEngine → AssetEngine(纯程序)
  → PPTXRenderer → output.pptx + deck_spec.json + benchmark.json
```

全程仅 **~7 次 LLM 调用**（1 次 Plan + ~6 次 Compose）；主题 / 布局 / 素材 / 渲染全是确定性程序——这是风格一致、成本 / 速度可控的根本。详见 [`docs/GENERATION_PIPELINE.md`](docs/GENERATION_PIPELINE.md)。

---

## 🗂 目录

| 路径 | 职责 |
|---|---|
| `packages/` | 生成内核（零基础设施依赖）：`core` 模型 / `llm` provider / `planner` 策划 / `theme·layout·asset_engine` / `renderer` / `benchmark` |
| `cli.py` | CLI 适配器（单命令吃 JSON 吐 PPTX） |
| `templates/` `assets/` | 预设主题 / 素材库 |
| `examples/` | 5 套公开输入 JSON |
| `demos/` | 上述 5 套对应的真实产出：`pptx/`（中文名样例）+ `specs/` + `benchmark/` |
| `docs/` | 设计文档 |

## ✅ 工程质量

```bash
ruff check .          # lint
mypy packages         # 类型检查(严格,只查生成内核)
pytest                # 197 项,覆盖生成内核与 CLI
make verify           # 一键:lint + typecheck + test + 5 套 demo
```

## 📌 约束

不使用 Gamma / Tome / Beautiful.ai 等一键生成 SaaS；PPTX 由 `python-pptx` + 自研组件库渲染。密钥不进仓（见 `.gitignore` 与 `.env.example`）。

## 📖 文档

| 文档 | 内容 |
|---|---|
| [DESIGN](DESIGN.md) | 决策日志：架构 / 模型选型 / 风格一致性 / 多样性 / 成本时延实测 / 取舍 / AI 协作复盘 / 自评分 |
| [docs/ARCHITECTURE](docs/ARCHITECTURE.md) | 系统分层 / 数据流 / 内核零依赖纪律 |
| [docs/DATA_MODEL](docs/DATA_MODEL.md) | 领域模型：DeckSpec / typed SlideSpec / Design Token |
| [docs/GENERATION_PIPELINE](docs/GENERATION_PIPELINE.md) | LLM 两段编排 / 结构化输出 / 校验降级 / Benchmark |
| [docs/RENDERING](docs/RENDERING.md) | 渲染路线 / 组件库 / 文字自适配 / 预览 |
</content>
