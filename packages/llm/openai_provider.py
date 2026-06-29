"""OpenAI / OpenAI 兼容端点(DeepSeek、Qwen 等)适配器。

client 懒加载:import 与构造都不联网;只有真正调用 complete/structured 才建连。
默认不在自主循环里发起真实调用(成本),仅供手动跑通时启用。
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from collections.abc import Callable
from typing import Any

from packages.llm.provider import LLMResponse, LLMUsage, ModelT, StructuredResponse

logger = logging.getLogger("aippt.llm")

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.S)
_JSON_OBJ = re.compile(r"\{.*\}", re.S)
_STREAM_RETRIES = 2  # 流式偶发连接错误的重试次数(耗尽回退非流式)
# 应用层重试退避:指数 + **满抖动(full jitter)**,封顶。抖动让并发调用的重试错峰,
# 不同步打满代理端点;封顶保证端点真不可达时不被退避拖长(配合 max_retries 不上调的纪律)。
_RETRY_BACKOFF_BASE = 0.4  # 退避基数(秒)
_RETRY_BACKOFF_CAP = 4.0  # 退避上限(秒)


def _extract_json(text: str) -> str:
    """从模型输出里取出 JSON 对象:优先 ```json 围栏,否则取首个 {...}。"""
    m = _JSON_FENCE.search(text) or _JSON_OBJ.search(text)
    return m.group(1) if m and m.lastindex else (m.group(0) if m else text)


def _backoff_with_jitter(attempt: int) -> None:
    """重试前退避:指数 `base * 2**attempt`、封顶 `CAP`,再取 [0, 上限] 的满抖动后 sleep。"""
    cap = min(_RETRY_BACKOFF_CAP, _RETRY_BACKOFF_BASE * (2**attempt))
    time.sleep(random.uniform(0.0, cap))


class OpenAIProvider:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout  # 单次调用超时(秒),防请求永久挂起占住调用线程
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI  # 懒加载,避免无 key 环境 import 即失败

            # max_retries=3:代理端点(APIYI 等)间歇性 APIConnectionError,SDK 内置指数退避重试能
            # 吸收单次瞬时抖动;不调更高,否则端点真正不可达时每个调用都退避数次会拖垮整体生成时长
            # (宁可快速回退离线占位 + 标记降级让用户重试,也不让用户干等几分钟)。
            self._client = OpenAI(
                api_key=self._api_key, base_url=self._base_url,
                timeout=self._timeout, max_retries=3,
            )
        return self._client

    def complete(self, system: str, user: str, *, max_tokens: int = 2048) -> LLMResponse:
        client = self._ensure_client()
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        text = resp.choices[0].message.content or ""
        return LLMResponse(text=text, usage=self._usage(resp, latency_ms))

    def structured(
        self, system: str, user: str, schema: type[ModelT], *, max_tokens: int = 4096
    ) -> StructuredResponse[ModelT]:
        # 用 json_object(中转/各家普遍支持)+ schema 提示,而非严格 json_schema(对可辨识联合兼容差)
        client = self._ensure_client()
        hint = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": f"{system}\n\n只输出一个 JSON 对象,严格符合下面的 JSON Schema"
                    "(字段齐全、type 判别字段正确,不要 markdown 代码块、不要多余文字):\n"
                    f"{hint}",
                },
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        text = resp.choices[0].message.content or "{}"
        return StructuredResponse(
            value=schema.model_validate_json(_extract_json(text)),
            usage=self._usage(resp, latency_ms),
        )

    def structured_stream(
        self,
        system: str,
        user: str,
        schema: type[ModelT],
        *,
        max_tokens: int = 4096,
        on_delta: Callable[[str], None] | None = None,
    ) -> StructuredResponse[ModelT]:
        """流式结构化输出:边收 token 边把**累积文本**回调给 on_delta(供增量抽取标题)。

        token 流仅用于"边写边浮现"的进度提示;最终仍把完整文本解析成权威 Model 返回。
        端点不支持流式 / 流式中途失败 → 回落普通 structured(权威结果优先于进度增强)。
        """
        client = self._ensure_client()
        hint = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        messages = [
            {
                "role": "system",
                "content": f"{system}\n\n只输出一个 JSON 对象,严格符合下面的 JSON Schema"
                "(字段齐全、type 判别字段正确,不要 markdown 代码块、不要多余文字):\n"
                f"{hint}",
            },
            {"role": "user", "content": user},
        ]
        # 代理端点流式偶发 APIConnectionError → **重试**(退避带抖动)再回退非流式,
        # 让"边写边浮现"更常生效;失败次数记日志便于观测端点抖动 vs 真不可达。
        for attempt in range(_STREAM_RETRIES):
            t0 = time.perf_counter()
            try:
                stream = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                    stream=True,
                    stream_options={"include_usage": True},
                )
                acc = ""
                usage_obj: Any = None
                for event in stream:
                    if getattr(event, "usage", None) is not None:
                        usage_obj = event.usage  # 末帧携带(需 include_usage,缺省则 None)
                    choices = getattr(event, "choices", None)
                    if not choices:
                        continue
                    piece = getattr(choices[0].delta, "content", None)
                    if piece:
                        acc += piece
                        if on_delta is not None:
                            on_delta(acc)  # 回调累积文本,调用方按累积文本去重,重试重发无害
                latency_ms = (time.perf_counter() - t0) * 1000
                return StructuredResponse(
                    value=schema.model_validate_json(_extract_json(acc or "{}")),
                    usage=self._usage_obj(usage_obj, latency_ms),
                )
            except Exception as exc:  # noqa: BLE001 — 本轮失败:记数 + 退避后续轮,耗尽回落非流式
                logger.warning(
                    "structured_stream 流式重试 %d/%d 失败:%s",
                    attempt + 1, _STREAM_RETRIES, exc,
                )
                if attempt + 1 < _STREAM_RETRIES:
                    _backoff_with_jitter(attempt)  # 退避带抖动;最后一轮不睡,直接回落非流式
        # 流式重试都失败 → 非流式(权威产出优先于"边写边浮现"的进度增强)
        return self.structured(system, user, schema, max_tokens=max_tokens)

    def _usage(self, resp: Any, latency_ms: float) -> LLMUsage:
        return self._usage_obj(getattr(resp, "usage", None), latency_ms)

    def _usage_obj(self, usage: Any, latency_ms: float) -> LLMUsage:
        return LLMUsage(
            model=self.model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency_ms,
        )
