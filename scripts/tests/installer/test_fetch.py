"""Tests for installer.fetch — download management."""
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from installer.fetch import (
    MIRRORS,
    build_urls,
    download_file,
    extract_opencode_from_zip,
    REPO,
    BRANCH,
)


class TestMirrors:
    def test_mirrors_list_not_empty(self):
        assert len(MIRRORS) > 0
        assert isinstance(MIRRORS, list)

    def test_build_urls_default(self):
        repo = "owner/repo"
        branch = "main"
        urls = build_urls(repo, branch)
        assert len(urls) > 0
        # First URL must be direct GitHub
        assert urls[0].startswith("https://github.com")
        assert "owner/repo" in urls[0]
        assert "main" in urls[0]

    def test_build_urls_with_custom_mirror(self):
        urls = build_urls("owner/repo", "main", mirrors=["https://example.com"])
        assert "https://example.com" in urls[-1]


class TestExtractOpenCode:
    def test_extract_opencode_from_real_zip(self):
        d = tempfile.mkdtemp()
        zip_path = Path(d) / "test.zip"
        extract_dir = Path(d) / "extracted"
        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("webnovel-writer-master/.opencode/skills/test.md", "hello")
            zf.writestr("webnovel-writer-master/.opencode/scripts/test.py", "pass")
            zf.writestr("webnovel-writer-master/README.md", "readme")

        extract_opencode_from_zip(zip_path, extract_dir)

        # Files extracted directly into extract_dir (no nested .opencode/)
        assert (extract_dir / "skills" / "test.md").exists()
        assert (extract_dir / "scripts" / "test.py").exists()
        # README should NOT be extracted (only .opencode/ contents)
        assert not (extract_dir / "README.md").exists()
