from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def test_cli_outline_prints_structure(tmp_path: Path) -> None:
    inp = tmp_path / "in.json"
    inp.write_text(
        '{"topic": "Python 入门", "brief": "变量、循环、函数", "audience": "零基础"}',
        encoding="utf-8",
    )
    r = runner.invoke(app, ["outline", str(inp)])
    assert r.exit_code == 0, r.output
    assert "# " in r.output  # 标题行
    assert "## " in r.output  # 至少一个章节
    assert "- [" in r.output  # 至少一页 [type] 标题


def test_cli_outline_unknown_provider_exits(tmp_path: Path) -> None:
    inp = tmp_path / "in.json"
    inp.write_text('{"topic": "T", "brief": "B", "audience": "A"}', encoding="utf-8")
    r = runner.invoke(app, ["outline", str(inp), "--provider", "nope"])
    assert r.exit_code == 1
