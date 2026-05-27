"""Tests for installer.preflight — orchestration."""
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from installer.preflight import apply_staging, verify_installation


class TestApplyStaging:
    def test_no_staging_directory(self):
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                result = apply_staging()
                assert result == False
            finally:
                os.chdir(cwd)

    def test_staging_replaces_opencode(self):
        d = tempfile.mkdtemp()
        cwd = os.getcwd()
        os.chdir(d)
        try:
            staging = Path(d) / ".opencode_staging"
            staging.mkdir()
            (staging / "test_file.txt").write_text("new content")
            result = apply_staging()
            assert result == True
            assert (Path(d) / ".opencode").is_dir()
            assert (Path(d) / ".opencode" / "test_file.txt").read_text() == "new content"
            assert not staging.exists()
        finally:
            os.chdir(cwd)


class TestVerifyInstallation:
    def test_verify_scripts_exist(self):
        """In the dev repo, .opencode/scripts/ exists so verify passes."""
        assert verify_installation() == True
