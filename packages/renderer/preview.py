"""pptx → png 预览(LibreOffice headless + pdftoppm)。

系统级依赖(soffice / pdftoppm)缺失则返回空列表,不抛、不阻塞 —— 预览是增强,不是必需。
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def soffice_bin() -> str | None:
    """返回 LibreOffice 可执行路径(soffice/libreoffice),都没有则 None。"""
    return shutil.which("soffice") or shutil.which("libreoffice")


def preview_available() -> bool:
    """三件套(soffice + pdftoppm)齐备才能逐页出图。"""
    return soffice_bin() is not None and shutil.which("pdftoppm") is not None


def to_png(pptx_bytes: bytes, *, dpi: int = 96) -> list[bytes]:
    """pptx 字节 → 每页一张 png 字节;环境不具备则返回 []。"""
    soffice = soffice_bin()
    if soffice is None or shutil.which("pdftoppm") is None:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "deck.pptx").write_bytes(pptx_bytes)
        try:
            subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(d),
                    str(d / "deck.pptx"),
                ],
                cwd=d,
                capture_output=True,
                timeout=120,
                check=True,
            )
            subprocess.run(
                ["pdftoppm", "-png", "-r", str(dpi), str(d / "deck.pdf"), str(d / "page")],
                cwd=d,
                capture_output=True,
                timeout=120,
                check=True,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        return [p.read_bytes() for p in sorted(d.glob("page*.png"))]
