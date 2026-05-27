"""Tests for export_manager module."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure scripts/ is on the path
_scripts_dir = Path(__file__).resolve().parents[2]
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from export_manager import collect_chapters, _parse_range
from export_manager.formats.markdown import export_markdown
from export_manager.formats.txt import export_txt, _strip_markdown


class TestParseRange:
    def test_single(self):
        assert _parse_range("5") == {5}

    def test_range(self):
        assert _parse_range("1-5") == {1, 2, 3, 4, 5}

    def test_comma_mix(self):
        assert _parse_range("1-3,5,7-9") == {1, 2, 3, 5, 7, 8, 9}

    def test_clamped(self):
        assert _parse_range("1-100", max_num=5) == {1, 2, 3, 4, 5}


class TestCollectChapters:
    def test_empty_dir(self, tmp_path):
        (tmp_path / "正文").mkdir()
        result = collect_chapters(tmp_path)
        assert result == []

    def test_no_chapters_dir(self, tmp_path):
        result = collect_chapters(tmp_path)
        assert result == []

    def test_flat_layout(self, tmp_path):
        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章-标题.md").write_text("# 第1章 测试", encoding="utf-8")
        (tmp_path / "正文" / "第0002章-继续.md").write_text("# 第2章 继续", encoding="utf-8")

        result = collect_chapters(tmp_path)
        assert len(result) == 2
        assert result[0][0] == 1
        assert result[0][1] == "第1章 测试"
        assert result[1][0] == 2

    def test_volume_layout(self, tmp_path):
        vol_dir = tmp_path / "正文" / "第1卷"
        vol_dir.mkdir(parents=True)
        (vol_dir / "第001章-开篇.md").write_text("# 第1章 开篇", encoding="utf-8")
        (vol_dir / "第002章-发展.md").write_text("# 第2章 发展", encoding="utf-8")

        result = collect_chapters(tmp_path)
        assert len(result) == 2

    def test_mixed_layout(self, tmp_path):
        """平铺和卷布局混合时正确收集。"""
        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章-旧格式.md").write_text("# 旧1", encoding="utf-8")
        vol_dir = tmp_path / "正文" / "第1卷"
        vol_dir.mkdir(parents=True)
        (vol_dir / "第002章-新格式.md").write_text("# 新2", encoding="utf-8")

        result = collect_chapters(tmp_path)
        assert len(result) == 2

    def test_range_filter(self, tmp_path):
        (tmp_path / "正文").mkdir()
        for i in range(1, 6):
            (tmp_path / "正文" / f"第{i:04d}章.md").write_text(f"# 第{i}章", encoding="utf-8")

        result = collect_chapters(tmp_path, range_spec="2-4")
        assert len(result) == 3
        assert [r[0] for r in result] == [2, 3, 4]

    def test_volume_filter(self, tmp_path):
        v1_dir = tmp_path / "正文" / "第1卷"
        v1_dir.mkdir(parents=True)
        v2_dir = tmp_path / "正文" / "第2卷"
        v2_dir.mkdir(parents=True)
        # 第1卷: 章 1-50; 第2卷: 章 51-100
        (v1_dir / "第001章.md").write_text("# 1", encoding="utf-8")
        (v2_dir / "第051章.md").write_text("# 51", encoding="utf-8")

        result = collect_chapters(tmp_path, volume=1)
        assert len(result) == 1
        assert result[0][0] == 1

        result = collect_chapters(tmp_path, volume=2)
        assert len(result) == 1
        assert result[0][0] == 51


class TestMarkdownExport:
    def test_basic(self, tmp_path):
        chapters_dir = tmp_path / "正文"
        chapters_dir.mkdir()
        ch1 = chapters_dir / "第0001章.md"
        ch1.write_text("# 第1章 开始\n\n正文内容。", encoding="utf-8")
        ch2 = chapters_dir / "第0002章.md"
        ch2.write_text("# 第2章 继续\n\n更多内容。", encoding="utf-8")

        chapters = collect_chapters(tmp_path)
        output = tmp_path / "导出" / "小说.md"
        output.parent.mkdir()

        export_markdown(chapters, output, title="测试小说")

        content = output.read_text(encoding="utf-8")
        assert "# 测试小说" in content
        assert "# 第1章 开始" in content
        assert "正文内容。" in content
        assert "---" in content


class TestTxtExport:
    def test_basic(self, tmp_path):
        chapters_dir = tmp_path / "正文"
        chapters_dir.mkdir()
        ch1 = chapters_dir / "第0001章.md"
        ch1.write_text("# 第1章 测试\n\n**粗体**和*斜体*。", encoding="utf-8")

        chapters = collect_chapters(tmp_path)
        output = tmp_path / "导出" / "小说.txt"
        output.parent.mkdir()

        export_txt(chapters, output)

        content = output.read_text(encoding="utf-8")
        assert "第1章" in content
        assert "粗体" in content
        assert "斜体" in content
        assert "**" not in content  # markdown stripped

    def test_strip_markdown(self):
        assert _strip_markdown("**粗体**文字") == "粗体文字"
        assert _strip_markdown("*斜体*文字") == "斜体文字"
        assert _strip_markdown("[链接](http://x.com)") == "链接"
        assert _strip_markdown("普通文字") == "普通文字"


class TestEpubImportError:
    def test_import_error(self, tmp_path, monkeypatch):
        """模拟 ebooklib 未安装时退出。"""
        chapters_dir = tmp_path / "正文"
        chapters_dir.mkdir()
        (chapters_dir / "第0001章.md").write_text("# 测试", encoding="utf-8")
        chapters = collect_chapters(tmp_path)

        output = tmp_path / "导出" / "小说.epub"
        output.parent.mkdir()

        # Remove ebooklib from sys.modules cache if present, to force __import__ call
        sys.modules.pop("ebooklib", None)

        # Mock import to simulate missing ebooklib
        import builtins

        _orig_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "ebooklib":
                raise ImportError("No module named 'ebooklib'")
            return _orig_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _mock_import)

        from export_manager.formats.epub import export_epub

        with pytest.raises(SystemExit) as exc:
            export_epub(chapters, output, title="测试", author="作者")
        assert exc.value.code == 1


class TestParser:
    """Tests for unified markdown parser."""

    def test_heading_to_html(self):
        from export_manager.parser import md_to_html
        html = md_to_html("# 第1章 开篇")
        assert '<h1 class="chapter-title">第1章 开篇</h1>' in html

    def test_paragraph_to_html(self):
        from export_manager.parser import md_to_html
        html = md_to_html("这是第一段。")
        assert '<p>这是第一段。</p>' in html

    def test_bold_to_html(self):
        from export_manager.parser import md_to_html
        html = md_to_html("**粗体**文字")
        assert '<strong' in html
        assert '粗体' in html

    def test_scene_break_to_html(self):
        from export_manager.parser import md_to_html
        html = md_to_html("---")
        assert 'class="scene-break"' in html

    def test_empty_input(self):
        from export_manager.parser import md_to_html
        html = md_to_html("")
        assert html == ""

    def test_multi_paragraph(self):
        from export_manager.parser import md_to_html
        html = md_to_html("第一段。\n\n第二段。")
        assert html.count("<p>") == 2

    def test_blocks_output(self):
        from export_manager.parser import md_to_blocks
        blocks = md_to_blocks("正文内容。")
        assert isinstance(blocks, list)
        assert len(blocks) > 0
        first = blocks[0]
        assert isinstance(first, dict)
        assert "type" in first


class TestStyles:
    def test_default_css(self):
        from export_manager.styles import get_default_css
        css = get_default_css()
        assert "text-indent" in css
        assert "line-height" in css
        assert "chapter-title" in css

    def test_load_custom_css(self, tmp_path):
        from export_manager.styles import load_custom_css
        css_file = tmp_path / "custom.css"
        css_file.write_text("p { color: red; }", encoding="utf-8")
        css = load_custom_css(css_file)
        assert "color: red" in css

    def test_get_css_fallback(self):
        from export_manager.styles import get_css
        css = get_css()
        assert "text-indent" in css

    def test_get_css_custom(self, tmp_path):
        from export_manager.styles import get_css
        css_file = tmp_path / "custom.css"
        css_file.write_text("body { margin: 0; }", encoding="utf-8")
        css = get_css(custom_path=css_file)
        assert "margin: 0" in css


class TestCollectorValidation:
    def test_gap_warning(self, tmp_path, capsys):
        from export_manager.chapter_collector import collect_chapters
        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text("# 第1章", encoding="utf-8")
        (tmp_path / "正文" / "第0003章.md").write_text("# 第3章", encoding="utf-8")
        result = collect_chapters(tmp_path)
        captured = capsys.readouterr()
        assert len(result) == 2
        assert "缺失" in captured.out

    def test_duplicate_error(self, tmp_path):
        from export_manager.chapter_collector import collect_chapters
        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text("# 第1章", encoding="utf-8")
        (tmp_path / "正文" / "第1卷").mkdir()
        (tmp_path / "正文" / "第1卷" / "第001章-b.md").write_text("# 第1章b", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            collect_chapters(tmp_path)
        assert exc.value.code == 1

    def test_empty_file_title_fallback(self, tmp_path):
        from export_manager.chapter_collector import collect_chapters
        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text("", encoding="utf-8")
        result = collect_chapters(tmp_path)
        assert result[0].title == "第1章"

    def test_no_heading_title(self, tmp_path):
        from export_manager.chapter_collector import collect_chapters
        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text("正文直接开始，没有标题。", encoding="utf-8")
        result = collect_chapters(tmp_path)
        assert "正文直接开始" in result[0].title

    def test_progress_output(self, tmp_path, capsys):
        from export_manager.chapter_collector import collect_chapters
        (tmp_path / "正文").mkdir()
        for i in range(1, 4):
            (tmp_path / "正文" / f"第{i:04d}章.md").write_text(f"# 第{i}章", encoding="utf-8")
        collect_chapters(tmp_path)
        captured = capsys.readouterr()
        assert "[1/3]" in captured.out
        assert "[3/3]" in captured.out

    def test_volume_from_dir(self, tmp_path):
        from export_manager.chapter_collector import collect_chapters
        (tmp_path / "正文" / "第2卷").mkdir(parents=True)
        (tmp_path / "正文" / "第2卷" / "第051章.md").write_text("# 第51章", encoding="utf-8")
        result = collect_chapters(tmp_path)
        assert result[0].volume == 2

    def test_volume_fallback(self, tmp_path):
        from export_manager.chapter_collector import collect_chapters
        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0051章.md").write_text("# 第51章", encoding="utf-8")
        result = collect_chapters(tmp_path)
        assert result[0].volume == 2  # (51-1)//50+1 = 2


class TestHtmlExport:
    def test_basic(self, tmp_path):
        from export_manager.chapter_collector import collect_chapters
        from export_manager.formats.html import export_html

        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text("# 第1章 开篇\n\n正文内容。", encoding="utf-8")
        (tmp_path / "正文" / "第0002章.md").write_text("# 第2章 发展\n\n更多内容。", encoding="utf-8")

        chapters = collect_chapters(tmp_path)
        output = tmp_path / "导出" / "小说.html"
        output.parent.mkdir()

        export_html(chapters, output, title="测试小说")

        content = output.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert '<html lang="zh-CN"' in content
        assert '<meta charset="utf-8">' in content
        assert "测试小说" in content
        assert "第1章 开篇" in content
        assert "正文内容。" in content
        assert 'class="toc"' in content
        assert 'id="ch0001"' in content


class TestEpubForward:
    def test_epub_creates_file(self, tmp_path):
        """Test that EPUB export produces a non-empty file (requires ebooklib)."""
        try:
            from ebooklib import epub  # noqa: F401
        except ImportError:
            pytest.skip("ebooklib not installed")

        from export_manager import collect_chapters
        from export_manager.formats.epub import export_epub

        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text(
            "# 第1章 开篇\n\n这是正文。\n\n第二段。", encoding="utf-8"
        )

        chapters = collect_chapters(tmp_path)
        output = tmp_path / "导出" / "小说.epub"
        output.parent.mkdir()

        export_epub(chapters, output, title="测试", author="作者")

        assert output.is_file()
        assert output.stat().st_size > 0


class TestDocxExport:
    def test_basic(self, tmp_path):
        try:
            from docx import Document  # noqa: F401
        except ImportError:
            pytest.skip("python-docx not installed")

        from export_manager.chapter_collector import collect_chapters
        from export_manager.formats.docx import export_docx

        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text(
            "# 第1章 开篇\n\n这是正文内容。\n\n第二段。", encoding="utf-8"
        )

        chapters = collect_chapters(tmp_path)
        output = tmp_path / "导出" / "小说.docx"
        output.parent.mkdir()

        export_docx(chapters, output, title="测试", author="作者")

        assert output.is_file()
        assert output.stat().st_size > 0

    def test_scene_break(self, tmp_path):
        try:
            from docx import Document  # noqa: F401
        except ImportError:
            pytest.skip("python-docx not installed")

        from export_manager.chapter_collector import collect_chapters
        from export_manager.formats.docx import export_docx

        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text(
            "第一场景。\n\n---\n\n第二场景。", encoding="utf-8"
        )

        chapters = collect_chapters(tmp_path)
        output = tmp_path / "导出" / "小说.docx"
        output.parent.mkdir()

        export_docx(chapters, output, title="测试")

        from docx import Document
        doc = Document(str(output))
        texts = [p.text for p in doc.paragraphs]
        assert any("* * *" in t for t in texts)

    def test_bold_text(self, tmp_path):
        try:
            from docx import Document  # noqa: F401
        except ImportError:
            pytest.skip("python-docx not installed")

        from export_manager.chapter_collector import collect_chapters
        from export_manager.formats.docx import export_docx

        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text(
            "这是**粗体**文字。", encoding="utf-8"
        )

        chapters = collect_chapters(tmp_path)
        output = tmp_path / "导出" / "小说.docx"
        output.parent.mkdir()

        export_docx(chapters, output, title="测试")

        from docx import Document
        doc = Document(str(output))
        found_bold = False
        for p in doc.paragraphs:
            for run in p.runs:
                if run.bold and "粗体" in run.text:
                    found_bold = True
        assert found_bold


class TestPdfExport:
    def test_missing_dependency(self, tmp_path, monkeypatch):
        """PDF exits gracefully when weasyprint is not installed."""
        from export_manager.chapter_collector import collect_chapters

        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text("# 第1章\n\n正文。", encoding="utf-8")
        chapters = collect_chapters(tmp_path)
        output = tmp_path / "导出" / "小说.pdf"
        output.parent.mkdir()

        import builtins
        _orig_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "weasyprint":
                raise ImportError("No module named 'weasyprint'")
            return _orig_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _mock_import)

        from export_manager.formats.pdf import export_pdf

        with pytest.raises(SystemExit) as exc:
            export_pdf(chapters, output, title="测试")
        assert exc.value.code == 1


class TestExportCli:
    def test_export_html_integration(self, tmp_path, monkeypatch):
        """End-to-end CLI test for HTML export."""
        (tmp_path / "正文").mkdir()
        (tmp_path / "正文" / "第0001章.md").write_text("# 第1章\n\n内容。", encoding="utf-8")

        monkeypatch.setattr("sys.argv", [
            "export_manager",
            "--project-root", str(tmp_path),
            "export",
            "--format", "html",
            "--range", "1",
        ])

        with pytest.raises(SystemExit) as exc:
            from export_manager.__init__ import main
            main()
        assert exc.value.code == 0

        # Verify file was created
        export_dir = tmp_path / "导出"
        html_files = list(export_dir.glob("*.html"))
        assert len(html_files) == 1
        content = html_files[0].read_text(encoding="utf-8")
        assert "第1章" in content
