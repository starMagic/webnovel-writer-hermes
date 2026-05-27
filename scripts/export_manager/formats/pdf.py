#!/usr/bin/env python3
"""PDF export — renders HTML to PDF via weasyprint (optional dependency)."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Optional

from export_manager.parser import md_to_html
from export_manager.styles import get_css


_PDF_EXTRA_CSS = """
@page {
    size: A4;
    margin: 2cm;
}
h1.chapter-title {
    page-break-before: always;
}
"""


def export_pdf(
    chapters: list,
    output_path: Path,
    title: str = "",
    custom_css: Optional[Path] = None,
) -> None:
    """Export chapters as a PDF file. Requires weasyprint."""
    try:
        from weasyprint import HTML
    except ImportError:
        print("PDF 导出需要 weasyprint，请运行: pip install weasyprint")
        raise SystemExit(1)

    css = get_css(custom_css) + _PDF_EXTRA_CSS

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
        ch_index = ch.index if hasattr(ch, 'index') else ch[0]
        ch_title = ch.title if hasattr(ch, 'title') else ch[1]
        html_parts.append(
            f'<li><a href="#ch{ch_index:04d}">第{ch_index}章 {escape(ch_title)}</a></li>'
        )
    html_parts.append("</ol></nav>")

    for ch in chapters:
        ch_index = ch.index if hasattr(ch, 'index') else ch[0]
        ch_title = ch.title if hasattr(ch, 'title') else ch[1]
        ch_path = ch.path if hasattr(ch, 'path') else ch[2]
        text = ch_path.read_text(encoding="utf-8")
        body_html = md_to_html(text)
        html_parts.append(
            f'<section id="ch{ch_index:04d}">'
            f'<h1 class="chapter-title">第{ch_index}章 {escape(ch_title)}</h1>'
            f"{body_html}"
            f"</section>"
        )

    html_parts.append("</body></html>")

    html_str = "\n".join(html_parts)
    HTML(string=html_str).write_pdf(str(output_path))
