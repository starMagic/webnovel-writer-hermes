#!/usr/bin/env python3
"""Markdown 格式导出 — 拼接章节原文，章节间用 --- 分隔。"""

from __future__ import annotations

from pathlib import Path


def export_markdown(
    chapters: list[tuple[int, str, Path]],
    output_path: Path,
    title: str = "",
) -> None:
    """将所有章节拼接为单个 .md 文件。"""
    lines: list[str] = []

    if title:
        lines.append(f"# {title}\n")

    for num, chapter_title, path in chapters:
        text = path.read_text(encoding="utf-8")
        lines.append(text.rstrip())
        lines.append("\n\n---\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
