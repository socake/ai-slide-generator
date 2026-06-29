from __future__ import annotations

import pytest

from packages.llm import PRICING, cost_usd


def test_known_model_cost() -> None:
    # gpt-4o-mini: 0.15 / 0.60 per 1M
    cost = cost_usd("gpt-4o-mini", 1_000_000, 1_000_000)
    assert abs(cost - (0.15 + 0.60)) < 1e-9


def test_partial_tokens() -> None:
    cost = cost_usd("gpt-4o-mini", 500_000, 0)
    assert abs(cost - 0.075) < 1e-9


def test_unknown_model_is_free() -> None:
    assert cost_usd("does-not-exist", 10_000, 10_000) == 0.0


def test_mock_is_free_and_registered() -> None:
    assert "mock" in PRICING
    assert cost_usd("mock", 9_999, 9_999) == 0.0


@pytest.mark.parametrize(
    ("model", "input_tokens", "output_tokens", "expected"),
    [
        ("deepseek-chat", 1_000_000, 0, 0.27),
        ("claude-3-5-haiku-latest", 0, 1_000_000, 4.00),
        ("claude-3-5-sonnet-latest", 1_000_000, 1_000_000, 18.00),  # 3 + 15
    ],
)
def test_full_pricing_table(
    model: str, input_tokens: int, output_tokens: int, expected: float
) -> None:
    assert abs(cost_usd(model, input_tokens, output_tokens) - expected) < 1e-9

