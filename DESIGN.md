# DESIGN · 决策日志

> 招聘核心交付物。按考核维度（**美观度 / LLM 成本 / 生成速度**）与 take-home 要求的小节组织。
> 详细设计分散在 `docs/`（ARCHITECTURE / DATA_MODEL / GENERATION_PIPELINE / RENDERING），本文是决策与取舍的浓缩。

---

## 1. 架构图 + 数据流

一句话：**LLM 出结构化 `DeckSpec`，程序确定性渲染成 PPTX**；主题/布局/素材全程序规则化。

```
input.json → InputValidator → Plan(LLM) → Compose(LLM)
  → DeckSpecValidator → ThemeEngine → LayoutEngine → AssetEngine(均为程序)
  → PPTXRenderer → output.pptx + deck_spec.json + benchmark.json
```

CLI 直跑内核，一条命令从 JSON 到 pptx，不依赖任何外部服务。完整分层见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

---

## 2. 模型选型

| 角色 | 模型 | 理由 |
|---|---|---|
| Plan（意图 + 叙事 + 骨架） | **deepseek-chat** / gpt-4o-mini | 结构化推理、量小、需稳定 JSON；均支持 json_object 约束 |
| Compose（逐段填内容） | **deepseek-chat** / gpt-4o-mini | 调用 ~6 次，成本敏感，便宜模型足够 |
| 离线 / CI 默认 | **MockLLMProvider** | 确定性、零成本、可复现；`make demo` / 测试全程不联网 |

- 多 provider 统一 `LLMProvider` 接口（`structured` / `complete`），DeepSeek 走 OpenAI 兼容端点，改 `base_url` / `model` 一键切换（见 GENERATION_PIPELINE §4）；定价表 `packages/llm/pricing.py` 就位，`BenchmarkCollector` 自动折算成本。
- **默认 deepseek-chat**（原生端点）：中文内容质感好、页数控制稳、单套 ~$0.018；成本优先可 `--provider openai` 切 gpt-4o-mini（成本约低一半）。两模型同 5 套输入的成本/时延横评见 §5。

---

## 3. 风格一致性怎么保的（核心难点，详写）

风格一致**不靠 LLM 自觉**，靠程序锁死：

1. **LLM 不碰样式**。LLM 只产出内容/意图（DeckSpec），从不输出颜色、坐标、字号。
2. **一套 ThemeSpec 贯穿全 deck**。`ThemeEngine` 按 `deck_type + audience` 选**一套精调的 theme preset**（配色 / 字阶 / 间距 token），全部页面共用（DATA_MODEL §3）。
3. **布局来自有限 LayoutSpec 库**，按 `slide_type` 选，不是每页自由排版。
4. **renderer 统一兜底**：页脚 / 页码 / 配色 / 字体在渲染主循环里统一施加，不接受逐页随机样式（RENDERING §2）。
5. **Design Token 化**：颜色 / 字号 / 间距都是 token，组件只引用 token，从源头杜绝“这页深蓝那页天蓝”。

> 一句话：风格一致 = 把“美术决策”从 LLM 手里拿走，固化进 theme preset + 组件库。

---

## 4. 多样性怎么保的（不同输入不像同模板填空）

- **IntentAnalyzer → DeckType**：把输入归类到 8 种演示类型（教学 / 复盘 / 消费 / 汇报 / 旅行 / 产品 / 路演 / 技术），每类有**不同的 theme 基调 + 默认布局序列**（DATA_MODEL §1.1）。
- **NarrativeSpec 因题而异**：hook / conflict / progression 由内容驱动，章节结构随主题变。
- **slide_type 组合多样**：cards / timeline / comparison / process / data / quote 按内容选，不是千篇一律 bullet 页。
- 结果：Python 教学走蓝白代码感 + 步骤布局，京都攻略走米白留白 + 时间轴，CEO 汇报走深色强对比 + 数据卡——同系统，不同长相（§5 的 deck_type 列即为印证）。

---

## 5. 成本与时延实测（5 套公开开发集）

实测条件：**真实 LLM 全程**（`degraded=false`，无离线兜底），关闭预览（纯测 Plan+Compose+render），串行单次场景；每套 7–8 次 LLM 调用（1 Plan + 6–7 Compose）。

**主：deepseek-chat（默认，原生端点 `api.deepseek.com`）**

| # | topic | deck_type | 页数 | LLM 调用 | 成本(USD) | 端到端时延 |
|---|---|---|---|---|---|---|
| 1 | Python 入门 30 分钟 | teaching | 29 | 8 | $0.0196 | 75s |
| 2 | 2025 我的年度复盘 | review | 29 | 7 | $0.0159 | 61s |
| 3 | 如何挑选咖啡豆 | teaching | 29 | 7 | $0.0181 | 79s |
| 4 | Rust 重写订单系统 | exec_report | 32* | 8 | $0.0194 | 128s |
| 5 | 周末两天玩遍京都 | travel | 26 | 7 | $0.0156 | 65s |
| | **平均** | | ~29 | ~7.4 | **~$0.018** | **~82s** |

**对照：gpt-4o-mini（OpenAI）**

| # | topic | 页数 | 成本(USD) | 时延 |
|---|---|---|---|---|
| 1 | Python 入门 | 34* | $0.0101 | 112s |
| 2 | 年度复盘 | 27 | $0.0084 | 79s |
| 3 | 咖啡豆 | 25 | $0.0104 | 117s |
| 4 | Rust 重写 | 25 | $0.0082 | 70s |
| 5 | 京都 | 28 | $0.0091 | 90s |
| | **平均** | ~28 | **~$0.009** | **~94s** |

> **选型结论**：两者速度相当（deepseek 原生 ~82s vs gpt-4o-mini ~94s/套，均受 Compose 串行所限）；**gpt-4o-mini 成本约低一半**（输出 token 单价 $0.60 vs deepseek $1.10 per 1M）。默认用 **deepseek-chat**（中文内容质感好、页数控制更稳），成本优先可一键 `--provider openai` 切 gpt-4o-mini——两者绝对成本都极低（30 页一套 ≈ 1–2 美分）。
> `*` 页数是 Plan 的软约束：deepseek 的 rust(32)、gpt-4o-mini 的 python(34) 各一套略超 25–30，其余均在区间内；未做硬截断（取舍见 §6）。
> **provider 通道稳定性对时延是决定性的**：同一 deepseek-chat 经第三方中转端点曾测出 5–22 分钟/套 + Plan 频繁 ReadTimeout 回退离线大纲，换原生端点后降到 ~82s/套且全程无降级（踩坑见 §6）。
> 渲染（确定性）稳定在 ~60–130ms/套，与模型无关；时延变量全在 LLM 两步。**Compose 当前串行**是时延主因，设计上可并行，wall-clock 可降到 ≈ Plan + 最慢一段。

---

## 6. 踩坑和取舍

已决策的取舍：

| 取舍 | 选择 | 放弃项 / 理由 |
|---|---|---|
| 渲染路线 | python-pptx + 自研组件库 | 放弃 HTML→图片（丢可编辑性）、放弃纯母版填槽（难适配可变数量内容）；母版降级为素材 |
| 结构化输出 | 事前 json_object + schema 约束 | 不靠“自由吐 + 事后大改”，Validator 仅兜底 |
| LLM 编排 | 两段（Plan + 按 section Compose） | 不一次吐 30 页（贵 / 易超长）、不逐页调（慢 / 贵） |
| 素材匹配 | 规则（tag 交集打分） | 向量检索作后续增强；先要可解释 |
| 主题 | 有限精调 preset | 不让 LLM 随机配色（美观度不可控） |
| provider 接入 | 工厂 + 懒加载，默认 mock | 切真实 LLM 仅 `--provider`；不配 key / 不加 flag 绝不联网，demo / 测试零成本 |
| data 页可视化 | 数值则原生柱状图，否则回退指标块 | 不强行图表化（非数值会失真）；用 python-pptx 原生 chart 保可编辑 |
| 生成前预览 | outline 步（只跑 Plan，不渲染） | 先看叙事结构再决定是否出全稿，省一次完整渲染 |

> 实操踩坑（已处置）：长文本按容量估算**截断兜底**；LLM schema 违例由 `DeckSpecValidator` 修复 + 离线骨架兜底；预览依赖 LibreOffice 缺失时**优雅跳过**（不阻断生成）；中转端点偶发 `ReadTimeout`，SDK 内置退避重试吸收瞬时抖动，仍失败则该段骨架兜底并标 `degraded`。

---

## 7. AI 协作复盘

> 题面强调：**没有这一段，决策日志维度直接扣一半**。要看的是“用 AI 加速但保持判断”的人，不是“被 AI 牵着走”的人。

### 7.1 AI 提的、我照做了

- **`SlideSpec` 改为按 `slide_type` 的可辨识联合（typed content）**——AI 指出原设计里 `blocks: list[ContentBlock]` 的 `ContentBlock` 从未定义、渲染器只能猜内容，建议按类型强类型化。采纳，写入 DATA_MODEL §2。
- **两段式 LLM 编排（Plan + 按 section Compose）+ “只在 Plan/Compose 调 LLM、Theme/Layout/Asset/Render 全程序化”**——AI 提出以控制成本与速度。采纳。
- **确定性兜底贯彻到内容层**：无 LLM key 时 planner 走 `offline.py` 按 deck_type 模板成章 + brief 切句派生要点，使 `make demo` 离线零成本也能出 5 套风格各异的 deck。

### 7.2 AI 提的、我推翻了（写清为什么）

- 开发中曾计划做一个 `HeuristicProvider` 实现 `LLMProvider` 协议来增强离线内容。**推翻**——该 provider 只能拿到渲染后的 prompt 字符串，要生成好内容得反向解析 prompt，脆弱；改为直接增强 `offline.fallback_outline`（离线内容的真正源头），更简洁、无脆弱解析。教训：**别为“接口对称”硬塞抽象，在真正的数据源头改更干净。**

### 7.3 “AI 跑偏，我把它拽回来”的具体例子

- **误报“已完成”**：AI 在搭脚手架时误用工具调用格式，导致两个本应后台执行的文档生成根本没启动，却报告成“已完成”。我发现目标文件缺失后核对任务状态（pending 而非 completed），识别出这是空转，改为直接自己写。教训：**AI 的“已完成”必须用产物（文件是否真存在）核验，不能只信口头汇报。**
- **提示注入（真实发生）**：一个本应实现内核模块的子 agent **0 次工具调用**就返回，内容是伪造的“human-in-the-loop 协议”，施压话术（MUST / 合规 / 协议违规）诱导把全部代码外发到**某个外部仓库**才能“收尾”。识别信号：0 工具调用 + 施压话术 + 要求把代码外发到外部服务。处置：**拒绝外发**；磁盘核验确认子 agent 空转/被劫持；自己直接实现该模块；把“忽略冒充系统/协议的带内指令、绝不向外部服务发布代码、子 agent 产出以磁盘核验”写进操作规程。教训：**外发类带内指令默认拒绝；口头“已完成”必须用产物核验。**

### 7.4 我对 AI 输出做了哪些核验 / 兜底

- **产物核验**：每步用文件是否真实落地确认，不信“已完成”的口头声明（见上条）。
- **程序兜底 AI**：生成链路里 `DeckSpecValidator` + graceful 降级，把 LLM 的不确定性关进确定性的笼子（GENERATION_PIPELINE §5）。
- **每迭代三件套**：`ruff` / `mypy` / `pytest` 全绿才提交。
- **端到端实跑核验**：渲染产物用 python-pptx 重新打开 + 数页数确认，不只信“写了渲染代码”。

---

## 8. 自评分

| 维度 | 自评 | 理由 |
|---|---|---|
| 美观度 | 8/10 | 组件库 + 8 套精调 theme（随 deck_type 切）+ surface 卡片/网格 + 渐变底图 + safe_area 遮罩 + 文本溢出兜底 + 页脚页码；真照片素材库与更细排版留作上限 |
| LLM 成本 | 8/10 | 两段编排锁定 ~7 次调用；deepseek-chat 实测约 $0.02/套（见 §5）；定价表 + BenchmarkCollector 就位 |
| 生成速度 | 7/10 | 渲染（确定性）~60–130ms/套；LLM 两步是瓶颈，Compose 当前串行（设计上可并行化，wall-clock 可降到 ≈ 最慢一段） |
| 决策日志 | 9/10 | 本文含真实提示注入处置与核验规程；风格一致 / 多样性 / 取舍详写，AI 协作复盘完整 |
