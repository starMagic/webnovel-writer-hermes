#!/usr/bin/env python3
"""Export manager CLI — 章节收集 + 格式 dispatch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
# 确保 scripts 目录在 Python path 中（subprocess 运行时不会自动添加）
_scripts_root = Path(__file__).resolve().parent.parent
if str(_scripts_root) not in sys.path:
    sys.path.insert(0, str(_scripts_root))


from export_manager.chapter_collector import collect_chapters as _collect, ChapterInfo, _parse_range


def collect_chapters(*args, **kwargs):
    """Backward-compat: returns list[tuple[int, str, Path]]."""
    results = _collect(*args, **kwargs)
    return [(ch.index, ch.title, ch.path) for ch in results]


# ── CLI ──────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace) -> int:
    chapters = collect_chapters(args.project_root)
    if not chapters:
        print("无章节文件")
        return 1
    for num, title, path in chapters:
        print(f"第{num:04d}章  {title}  ({path})")
    print(f"\n共 {len(chapters)} 章")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    project_root = args.project_root
    chapters = collect_chapters(project_root, range_spec=args.range, volume=args.volume)

    if not chapters:
        print("错误：正文/ 目录不存在或无章节文件。请先使用 /webnovel-write 创建章节。")
        return 1

    fmt = args.format
    output = args.output
    if not output:
        title = args.title or project_root.name
        output = str(project_root / "导出" / f"{title}.{fmt}")

    # 确保输出目录存在
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    if fmt == "md":
        from export_manager.formats.markdown import export_markdown
        title = args.title or project_root.name
        export_markdown(chapters, Path(output), title)
    elif fmt == "txt":
        from export_manager.formats.txt import export_txt
        export_txt(chapters, Path(output))
    elif fmt == "epub":
        from export_manager.formats.epub import export_epub
        export_epub(
            chapters=chapters,
            output_path=Path(output),
            title=args.title or project_root.name,
            author=args.author,
            cover=args.cover,
            style=args.style,
            cover_size=args.cover_size,
        )
    elif fmt == "html":
        from export_manager.chapter_collector import ChapterInfo
        from export_manager.formats.html import export_html
        html_chapters = [ChapterInfo(index=n, title=t, path=p, volume=0) for n, t, p in chapters]
        export_html(
            chapters=html_chapters,
            output_path=Path(output),
            title=args.title or project_root.name,
            custom_css=Path(args.style) if args.style else None,
        )
    elif fmt == "docx":
        from export_manager.formats.docx import export_docx
        export_docx(
            chapters=chapters,
            output_path=Path(output),
            title=args.title or project_root.name,
            author=args.author,
        )
    elif fmt == "pdf":
        from export_manager.formats.pdf import export_pdf
        export_pdf(
            chapters=chapters,
            output_path=Path(output),
            title=args.title or project_root.name,
            custom_css=Path(args.style) if args.style else None,
        )
    else:
        print(f"不支持的格式: {fmt}，可选: md, txt, epub, html, docx, pdf")
        return 1

    print(f"导出完成: {output}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="webnovel export manager")
    parser.add_argument("--project-root", type=Path, required=True, help="项目根目录")

    sub = parser.add_subparsers(dest="action")

    # export list
    sub.add_parser("list", help="列出可导出章节")

    # export (执行导出)
    p_export = sub.add_parser("export", help="执行导出")
    p_export.add_argument("--format", choices=["md", "txt", "epub", "html", "docx", "pdf"], default="md", help="输出格式")
    p_export.add_argument("--range", help="章节范围: 1-50 / 1,3,5 / all")
    p_export.add_argument("--volume", type=int, help="按卷导出")
    p_export.add_argument("--output", help="输出文件路径")
    p_export.add_argument("--title", help="书名")
    p_export.add_argument("--author", help="作者名 (EPUB)")
    p_export.add_argument("--cover", help="封面图路径 (EPUB)")
    p_export.add_argument("--style", help="自定义 CSS 文件路径")
    p_export.add_argument("--cover-size", default="1200x1600", help="封面裁剪尺寸 (EPUB)")

    args = parser.parse_args()

    if args.action == "list":
        code = cmd_list(args)
    elif args.action == "export":
        code = cmd_export(args)
    else:
        parser.print_help()
        code = 1

    raise SystemExit(code)


if __name__ == "__main__":
    main()
