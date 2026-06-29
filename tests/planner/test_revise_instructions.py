from __future__ import annotations

import pytest

from packages.core import Card, CardsSlide, CoverSlide
from packages.planner.revise import revise_offline


def _cards() -> CardsSlide:
    return CardsSlide(
        id="x", index=3, title="要点页",
        cards=[Card(title="A", body="aa"), Card(title="B", body="bb"), Card(title="C", body="cc")],
    )


@pytest.mark.parametrize(
    ("instruction", "expected"),
    [
        ("换成对比", "comparison"),
        ("换成数据", "data"),
        ("换成步骤", "process"),
        ("换成时间轴", "timeline"),
        ("换成卡片", "cards"),
    ],
)
def test_revise_keyword_targets_type(instruction: str, expected: str) -> None:
    out = revise_offline(_cards(), instruction)
    assert out.type == expected
    assert out.id == "x" and out.index == 3  # id/index 保持


def test_revise_simplify_keeps_type() -> None:
    out = revise_offline(_cards(), "更简洁")
    assert out.type == "cards"  # 简洁只裁内容,不换型
    assert isinstance(out, CardsSlide) and len(out.cards) <= 3


def test_revise_no_keyword_rotates() -> None:
    out = revise_offline(_cards(), "随便改改")
    assert out.type == "comparison"  # cards → 环上下一型


def test_revise_empty_instruction_safe() -> None:
    out = revise_offline(_cards(), "")
    assert out.id == "x"
    assert out.type == "comparison"  # 空指令同样轮换,产物合法


def test_revise_structure_page_without_keyword_keeps_type() -> None:
    out = revise_offline(CoverSlide(id="c", index=0, title="封面"), "调整一下")
    assert out.type == "cover"  # 结构页无关键词时不换型
