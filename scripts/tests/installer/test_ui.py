"""Tests for installer.ui — terminal output utilities."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from installer.ui import display_width, Colors, step, step_ok, info, warn


class TestDisplayWidth:
    def test_ascii_only(self):
        assert display_width("Hello") == 5

    def test_chinese_chars(self):
        assert display_width("你好") == 4  # Each CJK char = 2

    def test_mixed_cjk_ascii(self):
        assert display_width("Hello你好") == 9  # 5 + 4

    def test_ansi_escape_stripped(self):
        s = "\033[92mHello\033[0m"
        assert display_width(s) == 5

    def test_empty_string(self):
        assert display_width("") == 0


class TestStepFormatting:
    def test_step(self, capsys):
        step(1, 4, "系统预检")
        out = capsys.readouterr().out
        assert "1/4" in out
        assert "系统预检" in out

    def test_step_ok(self, capsys):
        step_ok(1, 4, "系统预检通过")
        out = capsys.readouterr().out
        assert "1/4" in out
        assert "系统预检通过" in out


class TestInfoWarn:
    def test_info_output(self, capsys):
        info("All good")
        out = capsys.readouterr().out
        assert "All good" in out

    def test_warn_output(self, capsys):
        warn("Something weird")
        out = capsys.readouterr().out
        assert "Something weird" in out
