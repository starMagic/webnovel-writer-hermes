#!/usr/bin/env python3
"""HTML single-file export — all chapters in one HTML document with inline CSS."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Optional

from export_manager.parser import md_to_html
from export_manager.styles import get_css


def export_html(
    chapters: list,
    output_path: Path,
    title: str = "",
    custom_css: Optional[Path] = None,
) -> None:
    """Export chapters as a single HTML file with navigation TOC."""
    css = get_css(custom_css)

    html_parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{escape(title) or '小说导出'}</title>",
        "<style>",
        css,
        "</style>",
        "</head>",
        "<body>",
    ]

    if title:
        html_parts.append(f"<h1 class='book-title'>{escape(title)}</h1>")

    html_parts.append('<nav class="toc"><h2>目录</h2><ol>')
    for ch in chapters:
        html_parts.append(
            f'<li><a href="#ch{ch.index:04d}">第{ch.index}章 {escape(ch.title)}</a></li>'
        )
    html_parts.append("</ol></nav>")

    for ch in chapters:
        text = ch.path.read_text(encoding="utf-8")
        body_html = md_to_html(text)
        html_parts.append(
            f'<section id="ch{ch.index:04d}">'
            f'<h1 class="chapter-title">第{ch.index}章 {escape(ch.title)}</h1>'
            f"{body_html}"
            f"</section>"
        )

    html_parts.append("</body></html>")

    output_path.write_text("\n".join(html_parts), encoding="utf-8")
