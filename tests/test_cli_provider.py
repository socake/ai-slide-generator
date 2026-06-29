from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def test_cli_provider_mock_generates(tmp_path: Path) -> None:
    inp = tmp_path / "in.json"
    inp.write_text(
        '{"topic": "Python 入门", "brief": "变量", "audience": "零基础"}', encoding="utf-8"
    )
    out = tmp_path / "o.pptx"
    r = runner.invoke(app, ["generate", str(inp), str(out), "--provider", "mock"])
    assert r.exit_code == 0, r.output
    assert out.read_bytes()[:2] == b"PK"


def test_cli_unknown_provider_exits_nonzero(tmp_path: Path) -> None:
    inp = tmp_path / "in.json"
    inp.write_text('{"topic": "T", "brief": "B", "audience": "A"}', encoding="utf-8")
    r = runner.invoke(app, ["generate", str(inp), str(tmp_path / "o.pptx"), "--provider", "nope"])
    assert r.exit_code == 1
