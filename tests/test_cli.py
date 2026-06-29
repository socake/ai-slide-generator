from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def test_cli_generate_writes_all_outputs(tmp_path: Path) -> None:
    inp = tmp_path / "in.json"
    inp.write_text('{"topic": "主题", "brief": "简介", "audience": "受众"}', encoding="utf-8")
    out = tmp_path / "out.pptx"
    spec = tmp_path / "spec.json"
    bench = tmp_path / "bench.json"

    result = runner.invoke(
        app,
        ["generate", str(inp), str(out), "--spec-out", str(spec), "--benchmark-out", str(bench)],
    )
    assert result.exit_code == 0, result.output
    assert out.read_bytes()[:2] == b"PK"
    assert "页" in result.output

    spec_data = json.loads(spec.read_text(encoding="utf-8"))
    assert 25 <= len(spec_data["slides"]) <= 30
    assert spec_data["schema_version"] == "1.0"
    assert json.loads(bench.read_text(encoding="utf-8"))["slide_count"] >= 25


def test_cli_pptx_only(tmp_path: Path) -> None:
    inp = tmp_path / "in.json"
    inp.write_text('{"topic": "T", "brief": "B", "audience": "A"}', encoding="utf-8")
    out = tmp_path / "deep" / "out.pptx"  # 父目录不存在 → 自动创建
    result = runner.invoke(app, ["generate", str(inp), str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
