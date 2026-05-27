"""Tests for installer.check — system preflight checks."""
import sys
import platform
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from installer.check import (
    check_python_version,
    check_disk_space,
    platform_name,
    KNOWN_OPENCODE_PROCESSES,
)


class TestPythonVersion:
    def test_python_310_passes(self):
        assert check_python_version((3, 10)) == True

    def test_python_39_fails(self):
        assert check_python_version((3, 9)) == False

    def test_current_python_passes(self):
        # Current interpreter must be >= 3.10 for this project
        assert check_python_version() == True


class TestDiskSpace:
    def test_sufficient_space(self):
        # Should have at least 1 MB free in temp dir
        d = tempfile.gettempdir()
        assert check_disk_space(d, required_mb=1) == True

    def test_insufficient_mb(self):
        # Request impossibly large space
        assert check_disk_space(tempfile.gettempdir(), required_mb=10**7) == False


class TestPlatformName:
    def test_returns_string(self):
        name = platform_name()
        assert name in ("windows", "linux", "darwin")

    @patch("installer.check._platform.system")
    def test_windows(self, mock_sys):
        mock_sys.return_value = "Windows"
        assert platform_name() == "windows"

    @patch("installer.check._platform.system")
    def test_linux(self, mock_sys):
        mock_sys.return_value = "Linux"
        assert platform_name() == "linux"

    @patch("installer.check._platform.system")
    def test_macos(self, mock_sys):
        mock_sys.return_value = "Darwin"
        assert platform_name() == "darwin"


class TestProcessConfig:
    def test_known_processes_structure(self):
        assert set(KNOWN_OPENCODE_PROCESSES.keys()) == {"windows", "linux", "darwin"}
        assert isinstance(KNOWN_OPENCODE_PROCESSES["windows"], list)
        assert isinstance(KNOWN_OPENCODE_PROCESSES["linux"], list)
        assert isinstance(KNOWN_OPENCODE_PROCESSES["darwin"], list)
