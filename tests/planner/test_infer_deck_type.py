from __future__ import annotations

import pytest

from packages.planner import GenerationInput, fallback_outline


@pytest.mark.parametrize(
    ("topic", "expected"),
    [
        ("Python 入门 30 分钟", "teaching"),
        ("2025 我的年度复盘", "review"),
        ("如何挑选咖啡豆", "consumer"),
        ("Rust 重写订单系统", "tech"),
        ("周末两天玩遍京都", "travel"),
        ("关于某件随机事情", "generic"),
    ],
)
def test_offline_infers_deck_type(topic: str, expected: str) -> None:
    outline = fallback_outline(GenerationInput(topic=topic, brief="", audience=""))
    assert outline.deck_type == expected
