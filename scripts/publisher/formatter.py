# .opencode/scripts/publisher/formatter.py
"""Markdown → 平台格式转换。纯函数，无外部依赖。"""
from __future__ import annotations

import re


def to_plain_text(md: str) -> str:
    """Markdown → 纯文本。保留段落结构，去除行内标记。"""
    lines = md.splitlines()
    out: list[str] = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            out.append("")
        elif stripped.startswith("#"):
            out.append(re.sub(r"^#+\s*", "", stripped))
        elif stripped == "---":
            out.append("***")
        else:
            out.append(_clean_inline(stripped))

    # 合并连续空行，避免多余空白
    result: list[str] = []
    prev_blank = False
    for item in out:
        if item == "":
            if not prev_blank:
                result.append(item)
                prev_blank = True
        else:
            result.append(item)
            prev_blank = False

    return "\n".join(result).rstrip()


def _clean_inline(text: str) -> str:
    """去除行内 Markdown 标记：粗体、斜体、链接、行内代码。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def to_html(md: str) -> str:
    """Markdown → 简单 HTML。段落内容内联，无多余换行。"""
    lines = md.splitlines()
    out: list[str] = []
    para_lines: list[str] = []

    def flush_para():
        if para_lines:
            text = " ".join(para_lines)
            html_text = _inline_to_html(text)
            out.append(f"<p>{html_text}</p>")
            para_lines.clear()

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#"):
            flush_para()
            title = re.sub(r"^#+\s*", "", stripped)
            out.append(f"<h2>{title}</h2>")
            continue

        if stripped == "---":
            flush_para()
            out.append("<hr>")
            continue

        if stripped:
            para_lines.append(stripped)
        else:
            flush_para()

    flush_para()
    return "\n".join(out)


def _inline_to_html(text: str) -> str:
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text


_DEFAULT_HINTS = {
    "indent": "　　",   # 全角空格，中文网文标准
}


def format_for_platform(md: str, platform: str, hints: dict | None = None) -> str:
    """平台感知格式化。默认 MD→纯文本 + 段首全角缩进。"""
    plain = to_plain_text(md)
    cfg = {**_DEFAULT_HINTS, **(hints or {})}
    indent = cfg.get("indent", "　　")

    paragraphs = plain.split("\n\n")
    formatted: list[str] = []
    for para in paragraphs:
        stripped = para.strip()
        if not stripped or stripped == "***":
            formatted.append(stripped if stripped else "")
            continue
        formatted.append(f"{indent}{stripped}")
    return "\n\n".join(formatted)
