"""Tests for installer.update — version management."""
import sys
import json
import tempfile
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from installer.update import (
    compute_diff,
    read_local_version,
    write_version_file,
    current_repo_version,
)


class TestVersionFile:
    def test_write_and_read(self):
        d = tempfile.mkdtemp()
        vf = Path(d) / "version.json"
        write_version_file(vf, "v1.2.0")
        assert vf.exists()
        data = json.loads(vf.read_text(encoding="utf-8"))
        assert data["version"] == "v1.2.0"
        assert data["channel"] == "install.py"
        assert "installed_at" in data

    def test_read_nonexistent(self):
        d = tempfile.mkdtemp()
        vf = Path(d) / "nonexistent.json"
        result = read_local_version(vf)
        assert result["version"] == "unknown"


class TestComputeDiff:
    def test_new_file_added(self):
        manifest = {
            "version": "v2.0.0",
            "files": {
                ".opencode/new_skill/SKILL.md": {"sha256": "abc", "size": 100}
            }
        }
        local_dir = tempfile.mkdtemp()
        diff = compute_diff(manifest, Path(local_dir))
        assert len(diff) == 1
        assert diff[0] == (".opencode/new_skill/SKILL.md", "add")

    def test_unchanged_file_skipped(self):
        d = tempfile.mkdtemp()
        p = Path(d) / ".opencode" / "test.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        content = b"hello world"
        p.write_bytes(content)
        sha = hashlib.sha256(content).hexdigest()

        manifest = {
            "version": "v1.0.0",
            "files": {
                ".opencode/test.txt": {"sha256": sha, "size": len(content)}
            }
        }
        diff = compute_diff(manifest, Path(d))
        assert len(diff) == 0

    def test_modified_file_detected(self):
        d = tempfile.mkdtemp()
        p = Path(d) / ".opencode" / "test.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"old content")

        manifest = {
            "version": "v1.0.0",
            "files": {
                ".opencode/test.txt": {"sha256": "different_hash_value", "size": 50}
            }
        }
        diff = compute_diff(manifest, Path(d))
        assert len(diff) == 1
        assert diff[0] == (".opencode/test.txt", "update")
