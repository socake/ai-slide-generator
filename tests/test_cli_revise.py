from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from pptx import Presentation
from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def _generate_spec(tmp_path: Path) -> tuple[Path, dict]:
    inp = tmp_path / "in.json"
    inp.write_text(
        '{"topic": "Python 入门", "brief": "变量、循环", "audience": "零基础"}', encoding="utf-8"
    )
    spec = tmp_path / "spec.json"
    r = runner.invoke(
        app, ["generate", str(inp), str(tmp_path / "g.pptx"), "--spec-out", str(spec)]
    )
    assert r.exit_code == 0, r.output
    return spec, json.loads(spec.read_text(encoding="utf-8"))


def test_cli_revise_changes_slide(tmp_path: Path) -> None:
    spec, deck = _generate_spec(tmp_path)
    idx = next(i for i, s in enumerate(deck["slides"]) if s["type"] == "cards")
    out = tmp_path / "rev.pptx"
    spec2 = tmp_path / "spec2.json"

    rr = runner.invoke(
        app,
        [
            "revise",
            str(spec),
            str(idx),
            str(out),
            "--instruction",
            "换成对比",
            "--spec-out",
            str(spec2),
        ],
    )
    assert rr.exit_code == 0, rr.output
    assert out.read_bytes()[:2] == b"PK"
    revised = json.loads(spec2.read_text(encoding="utf-8"))
    assert revised["slides"][idx]["type"] == "comparison"
    assert len(Presentation(BytesIO(out.read_bytes())).slides) == len(deck["slides"])


def test_cli_revise_bad_index_exits_nonzero(tmp_path: Path) -> None:
    spec, _ = _generate_spec(tmp_path)
    rr = runner.invoke(app, ["revise", str(spec), "999", str(tmp_path / "x.pptx")])
    assert rr.exit_code == 1
