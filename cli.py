"""CLI 适配器:单命令吃 JSON 吐 PPTX(招聘题验收入口)。

内核在 packages/,此处只做 IO 与参数解析(CLI 适配器)。
用法:python cli.py generate input.json out.pptx [--spec-out spec.json] [--benchmark-out bench.json]
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, TypeVar

import typer
from pydantic import BaseModel, ValidationError

from packages.core import DeckSpec
from packages.llm import make_provider
from packages.pipeline import generate as run_pipeline
from packages.pipeline import plan_outline, render_pptx, revise_slide
from packages.planner import GenerationInput

app = typer.Typer(add_completion=False, help="aippt —— AI 演示稿生成 CLI")

_T = TypeVar("_T", bound=BaseModel)


def _load(path: Path, model: type[_T]) -> _T:
    """读 JSON → 校验为 model;坏 JSON/缺字段 → 友好报错 + 退出码 1(不抛 traceback)。"""
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        typer.echo(f"✗ 输入无效 {path}：{exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.callback()
def _root() -> None:
    """保证 `generate` 作为具名子命令存在(单命令 typer 否则会折叠掉子命令名)。"""


@app.command()
def generate(
    input_path: Annotated[Path, typer.Argument(help="输入 JSON(topic/brief/audience)")],
    output_path: Annotated[Path, typer.Argument(help="输出 .pptx 路径")],
    spec_out: Annotated[
        Path | None, typer.Option("--spec-out", help="同时写 deck_spec.json")
    ] = None,
    benchmark_out: Annotated[
        Path | None, typer.Option("--benchmark-out", help="同时写 benchmark.json")
    ] = None,
    provider: Annotated[
        str, typer.Option("--provider", help="mock(默认)/openai/deepseek/anthropic")
    ] = "mock",
    model: Annotated[
        str | None, typer.Option("--model", help="模型名(留空用 provider 默认)")
    ] = None,
) -> None:
    """读输入 JSON → 生成 → 写 pptx(+可选 spec/benchmark)。默认 mock 离线零成本。"""
    inp = _load(input_path, GenerationInput)
    try:
        prov = make_provider(provider, model)
    except ValueError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc
    result = run_pipeline(inp, prov)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result.pptx_bytes or b"")
    if spec_out is not None:
        spec_out.parent.mkdir(parents=True, exist_ok=True)
        spec_out.write_text(result.deck_spec.model_dump_json(indent=2), encoding="utf-8")
    if benchmark_out is not None:
        benchmark_out.parent.mkdir(parents=True, exist_ok=True)
        benchmark_out.write_text(result.benchmark.model_dump_json(indent=2), encoding="utf-8")

    bench = result.benchmark
    typer.echo(
        f"✓ {output_path} · {len(result.deck_spec.slides)} 页 · "
        f"${bench.total_cost_usd:.4f} · {bench.wall_clock_ms:.0f}ms"
    )


@app.command()
def revise(
    spec_path: Annotated[Path, typer.Argument(help="deck_spec.json 路径")],
    index: Annotated[int, typer.Argument(help="要改写的页索引(0-based)")],
    output_path: Annotated[Path, typer.Argument(help="输出 .pptx 路径")],
    instruction: Annotated[
        str, typer.Option("--instruction", help="改写指令:更简洁/换对比/换数据/换步骤…")
    ] = "",
    spec_out: Annotated[
        Path | None, typer.Option("--spec-out", help="同时写改后的 deck_spec.json")
    ] = None,
) -> None:
    """读 deck_spec.json,重生成第 index 页(保全局一致),写出 pptx(+可选 spec)。"""
    deck = _load(spec_path, DeckSpec)
    try:
        deck = revise_slide(deck, index, instruction)
    except IndexError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render_pptx(deck))
    if spec_out is not None:
        spec_out.parent.mkdir(parents=True, exist_ok=True)
        spec_out.write_text(deck.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"✓ 第 {index} 页 → {deck.slides[index].type} · {output_path}")


@app.command()
def outline(
    input_path: Annotated[Path, typer.Argument(help="输入 JSON(topic/brief/audience)")],
    provider: Annotated[
        str, typer.Option("--provider", help="mock(默认)/openai/deepseek/anthropic")
    ] = "mock",
    model: Annotated[
        str | None, typer.Option("--model", help="模型名(留空用 provider 默认)")
    ] = None,
) -> None:
    """只看叙事大纲(不渲染):打印 deck_type/标题/hook + 章节 + 每页标题。"""
    inp = _load(input_path, GenerationInput)
    try:
        prov = make_provider(provider, model)
    except ValueError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc

    o = plan_outline(inp, prov)
    typer.echo(f"# {o.title}  ·  {o.deck_type}")
    typer.echo(f"> {o.narrative.hook}")
    headings = {s.id: s.heading for s in o.sections}
    current: int | None = None
    for sl in o.slides:
        if sl.section_id != current:
            current = sl.section_id
            typer.echo(f"\n## {headings.get(sl.section_id, sl.section_id)}")
        typer.echo(f"- [{sl.type}] {sl.title}")


if __name__ == "__main__":
    app()
