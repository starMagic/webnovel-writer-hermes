#!/usr/bin/env python3
"""Unified Markdown parser — mistune v3 based, outputs HTML and AST."""
from __future__ import annotations

import mistune


class WebnovelRenderer(mistune.HTMLRenderer):
    """Custom HTML renderer for Chinese web novel content."""

    def heading(self, text: str, level: int, **attrs) -> str:
        if level == 1:
            return f'<h1 class="chapter-title">{text}</h1>\n'
        return super().heading(text, level, **attrs)

    def thematic_break(self) -> str:
        return '<hr class="scene-break" />\n'


_html_md = mistune.create_markdown(renderer=WebnovelRenderer())
_ast_md = mistune.create_markdown(renderer=None)


def md_to_html(text: str) -> str:
    """Convert Markdown text to HTML fragment (no html/body wrapper)."""
    if not text.strip():
        return ""
    return _html_md(text).strip()


def md_to_blocks(text: str) -> list[dict]:
    """Convert Markdown to mistune AST block list."""
    if not text.strip():
        return []
    return _ast_md(text)


def ast_to_text(block: dict) -> str:
    """Recursively extract plain text from a mistune AST block or inline token."""
    if "raw" in block:
        return block["raw"]
    if "text" in block and isinstance(block["text"], str):
        return block["text"]
    children = block.get("children", [])
    if not children:
        return ""
    parts = []
    for child in children:
        if isinstance(child, dict):
            parts.append(ast_to_text(child))
        elif isinstance(child, str):
            parts.append(child)
    return "".join(parts)
