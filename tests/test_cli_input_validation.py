from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def test_generate_bad_json_exits_with_message(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    r = runner.invoke(app, ["generate", str(bad), str(tmp_path / "o.pptx")])
    assert r.exit_code == 1
    assert "输入无效" in r.output


def test_generate_missing_field_exits(tmp_path: Path) -> None:
    bad = tmp_path / "m.json"
    bad.write_text('{"topic": "T"}', encoding="utf-8")  # 缺 brief/audience
    r = runner.invoke(app, ["generate", str(bad), str(tmp_path / "o.pptx")])
    assert r.exit_code == 1
    assert "输入无效" in r.output


def test_revise_bad_spec_exits(tmp_path: Path) -> None:
    bad = tmp_path / "spec.json"
    bad.write_text("not json at all", encoding="utf-8")
    r = runner.invoke(app, ["revise", str(bad), "0", str(tmp_path / "o.pptx")])
    assert r.exit_code == 1
    assert "输入无效" in r.output
