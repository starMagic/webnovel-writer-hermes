#!/usr/bin/env python3
"""CSS typesetting templates for Chinese web novel export."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

_DEFAULT_CSS = """\
body {
    font-family: "Source Han Serif SC", "Noto Serif CJK SC", "SimSun", serif;
    font-size: 16px;
    max-width: 42em;
    margin: 0 auto;
    padding: 2em;
}
p {
    text-indent: 2em;
    margin: 0.5em 0;
    line-height: 1.8;
}
h1.chapter-title {
    text-align: center;
    margin: 2em 0 1em;
    font-size: 1.5em;
}
hr.scene-break {
    border: none;
    text-align: center;
    margin: 1.5em 0;
}
hr.scene-break::after {
    content: "* * *";
    letter-spacing: 1em;
    color: #666;
}
"""


def get_default_css() -> str:
    """Return the default CSS template for Chinese web novel typesetting."""
    return _DEFAULT_CSS


def load_custom_css(path: Path) -> str:
    """Load CSS from a custom file path."""
    return path.read_text(encoding="utf-8")


def get_css(custom_path: Optional[Path] = None) -> str:
    """Get CSS: prefer custom path, fallback to default template."""
    if custom_path is not None and custom_path.is_file():
        return load_custom_css(custom_path)
    return _DEFAULT_CSS
