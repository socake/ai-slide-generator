# 生成编排规格 · GENERATION_PIPELINE

> 把"输入 → DeckSpec → PPTX"这条链路的**编排、调用次数、结构化约束、校验与降级**定清楚。
> 三个考核维度(美观度/LLM 成本/生成速度)里,**成本与速度几乎完全由本文的编排决定**。

---

## 1. 全链路(标注:🤖=调 LLM,⚙️=纯程序)

```
UserInput
  ⚙️ InputValidator      校验 topic/brief/audience/page_count
  🤖 Plan                意图识别 + 叙事线 + 每页骨架(1 次调用)
  🤖 Compose             逐 section 批量填 typed content(并行,~5-7 次调用)
  ⚙️ DeckSpecValidator   结构校验 + 触发定点修复
  ⚙️ ThemeEngine         规则选 theme preset(不调 LLM)
  ⚙️ LayoutEngine        按 slide_type + 数量选 LayoutSpec
  ⚙️ AssetEngine         规则匹配素材 + safe_area
  ⚙️ PPTXRenderer        DeckSpec+Theme+Layout+Asset → pptx 字节
  ⚙️ PreviewGenerator    pptx → png(LibreOffice headless)
  ⚙️ StorageWriter       落地(CLI 写盘;存储实现由调用方注入)
  ⚙️ BenchmarkLogger     汇总成本与时延
```

**关键决策:只有 Plan 和 Compose 调 LLM。** Theme/Layout/Asset 全程序规则化 —— 这是风格一致(不让 LLM 每页自由发挥)、成本可控(LLM 调用次数恒定)、速度可控的根本。

---

## 2. 两段式 LLM 编排(成本/速度的核心)

**不要**让 LLM 一次吐完整 30 页(贵、易超长、易跑偏),也**不要**逐页一调(30 次调用,慢且贵)。

### 2.1 Plan(1 次调用,结构化输出 `DeckOutline`)

输入 topic/brief/audience;输出骨架,**只定结构不写正文**:

```python
class SlidePlan(BaseModel):
    type: SlideType
    title: str
    key_points: list[str]      # 2-4 个要点,供 Compose 扩写
    section_id: int            # 归属章节

class SectionPlan(BaseModel):
    id: int
    heading: str

class DeckOutline(BaseModel):
    title: str
    deck_type: DeckType
    purpose: str
    narrative: NarrativeSpec
    sections: list[SectionPlan]
    slides: list[SlidePlan]    # 25-30 条,已含 cover/section/closing
```

Plan 这一步同时完成意图识别 + 页面规划，少一次调用。

### 2.2 Compose(并行,按 section 批量)

把 `DeckOutline.slides` 按 `section_id` 分组,**每个 section 一次调用**,扩写出该段所有页的 typed content(返回 `list[SlideSpec]`)。

- 30 页 ≈ 5-7 个 section → **5-7 次 Compose 调用,可并行**。
- 全程 **≈ 1 + 6 = 7 次 LLM 调用**(写进 DESIGN 的成本/时延表)。
- 并行后 wall-clock ≈ Plan + 最慢的一个 Compose,而非 7 次串行之和 —— 这是"生成速度"的主要来源。
- 每个 Compose 拿到**整段上下文 + 全局 narrative**,所以同段连贯、跨段不跑题。

---

## 3. 结构化输出:事前约束 > 事后修复

原规划是"LLM 自由吐 JSON → Validator 修",不够优雅且浪费 token。改为**事前用 provider 的结构化能力强约束 schema**:

- 优先 **tool-use / JSON schema / response_format=json_schema**(OpenAI 兼容与 Anthropic 都支持),让模型直接产出可被 Pydantic parse 的对象。
- Compose 的 schema 是 `discriminated union`,模型按 `type` 填对应字段,天然避免"cards 里塞了 timeline 字段"。
- Validator 退化为**最后一道兜底**,而非主力。

---

## 4. LLMProvider 统一接口 + 成本表

多 provider(OpenAI / Claude / DeepSeek / Qwen)统一到一个 Protocol,benchmark 才可比、选便宜模型才方便。

```python
class LLMResponse(BaseModel):
    content: str | dict
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int

class LLMProvider(Protocol):
    def structured(self, messages: list[dict], *, schema: type[BaseModel],
                   model: str) -> tuple[BaseModel, LLMResponse]: ...
    def complete(self, messages: list[dict], *, model: str) -> LLMResponse: ...

# 每模型单价表(USD / 1M tokens),benchmark 用其折算成本
PRICING: dict[str, tuple[float, float]] = {
    "deepseek-chat":      (0.27, 1.10),
    "gpt-4o-mini":        (0.15, 0.60),
    "claude-haiku-...":   (...,  ...),
    # ...
}
def cost_usd(model, in_tok, out_tok) -> float: ...
```

> DeepSeek/Qwen 走 OpenAI 兼容端点,可复用同一个 `openai_provider`,只换 `base_url`/`model`。默认用便宜模型跑(对齐"LLM 成本"考核),可一键切贵模型对比质量,差异写进 DESIGN。

---

## 5. 校验与 graceful 降级(稳定输出)

题目要"程序兜底 AI 的不确定性"。分层处理,**永不整盘崩**:

| 失败点 | 策略 |
|---|---|
| Compose 某 section 失败 | 重试 ≤2 次(tenacity);仍失败 → 用该段 `key_points` 直接降级填 `summary`/`cards`,保住页数与连贯 |
| Validator 发现某页超长/重复/缺字段 | **只对问题页**发定点修复 prompt 重生成,不重跑全篇 |
| 页数偏离 [25,30] | 程序裁剪(合并相邻弱页)或补页(从 narrative 拆),优先程序处理 |
| 整体超时/超预算 | 用已生成部分 + 占位补齐,标记 `degraded=true` 仍出可用 pptx |
| 单页 revise | 只重生成该 `SlideSpec` + relayout 该页,保持全局 theme 不变(见 ARCHITECTURE §revise 一致性) |

---

## 6. 缓存与幂等(加速 demo 调试)

- **LLM response cache**:key = `hash(provider+model+prompt+schema)`,命中直接返回。调试同一输入反复跑时省钱省时。
- **幂等**:并发场景可由调用方加幂等锁,防重复生成。
- 缓存可由调用方注入(如本地文件缓存 `.cache/`),保持内核零基础设施依赖(见 ARCHITECTURE)。

---

## 7. BenchmarkReport(成本/时延实测,直接喂 DESIGN 表格)

```python
class LLMCall(BaseModel):
    step: Literal["plan","compose","repair"]
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int

class BenchmarkReport(BaseModel):
    deck_id: str
    slide_count: int
    llm_calls: list[LLMCall]
    total_cost_usd: float
    total_llm_latency_ms: int      # 各调用之和(并行前)
    wall_clock_ms: int             # 端到端真实耗时(含并行收益、渲染)
    render_ms: int
    degraded: bool = False
```

> CLI `--benchmark-out` 落 `demos/benchmark/*.benchmark.json`;5 套 demo 的 `total_cost_usd / wall_clock_ms / slide_count` 汇总成 DESIGN 的实测表格。
