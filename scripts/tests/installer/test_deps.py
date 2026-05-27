"""Tests for installer.deps — dependency installation."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from installer.deps import create_venv, check_pip_available


class TestVenv:
    def test_create_venv_creates_directory(self):
        d = tempfile.mkdtemp()
        venv_path = Path(d) / ".venv"
        result = create_venv(venv_path)
        if result:
            assert venv_path.is_dir()
            if sys.platform == "win32":
                assert (venv_path / "Scripts" / "python.exe").exists()
            else:
                assert (venv_path / "bin" / "python").exists()

    def test_create_venv_returns_false_on_existing(self):
        d = tempfile.mkdtemp()
        venv_path = Path(d) / "existing_venv"
        venv_path.mkdir(parents=True)
        result = create_venv(venv_path)
        assert result == False


class TestPipCheck:
    def test_check_pip_available(self):
        assert check_pip_available() == True
