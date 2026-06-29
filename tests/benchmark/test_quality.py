"""质量评估(确定性)单测:满分路径 + 各惩罚维度。"""

from __future__ import annotations

from packages.benchmark import evaluate_quality
from packages.benchmark.quality import QualityReport
from packages.pipeline import generate
from packages.planner import GenerationInput


def _deck():
    return generate(GenerationInput(topic="测试", brief="质量评估", audience="工程师")).deck_spec


def test_full_deck_scores_well():
    rep = evaluate_quality(_deck())
    assert isinstance(rep, QualityReport)
    assert 0 <= rep.score <= 100
    assert rep.score >= 70  # 完整生成的稿子不该差
    assert {d.key for d in rep.dimensions} == {"content", "structure", "design"}


def test_to_dict_shape():
    d = evaluate_quality(_deck()).to_dict()
    assert set(d) == {"score", "summary", "dimensions"}
    assert all(set(x) == {"key", "label", "score", "issues"} for x in d["dimensions"])


def test_truncated_deck_penalised_on_structure():
    deck = _deck()
    deck.slides = deck.slides[:3]  # 砍到 3 页:页数远低于下限
    rep = evaluate_quality(deck)
    structure = next(d for d in rep.dimensions if d.key == "structure")
    assert structure.score < 100
    assert any("页" in i for i in structure.issues)


def test_blank_slides_penalised_on_content():
    deck = _deck()
    # 把若干内容页的所有文本字段清空 → 这些页变空白,content 维度应扣分
    for s in deck.slides[2:8]:
        for name in type(s).model_fields:
            if name in ("type", "id"):
                continue
            cur = getattr(s, name)
            if isinstance(cur, str):
                setattr(s, name, "")
            elif isinstance(cur, list):
                setattr(s, name, [])
    rep = evaluate_quality(deck)
    content = next(d for d in rep.dimensions if d.key == "content")
    assert content.score < 100
    assert content.issues
