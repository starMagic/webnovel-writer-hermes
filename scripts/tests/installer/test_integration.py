"""Integration smoke tests for installer — verify modules compose correctly."""
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


class TestModuleImports:
    """All installer modules import without errors (pure stdlib guarantee)."""
    def test_import_ui(self):
        from installer import ui
        assert hasattr(ui, 'info')
        assert hasattr(ui, 'warn')
        assert hasattr(ui, 'error')
        assert hasattr(ui, 'success')
        assert hasattr(ui, 'step')
        assert hasattr(ui, 'step_ok')
        assert hasattr(ui, 'spinner')
        assert hasattr(ui, 'display_width')

    def test_import_check(self):
        from installer import check
        assert hasattr(check, 'check_python_version')
        assert hasattr(check, 'check_disk_space')
        assert hasattr(check, 'is_opencode_running')
        assert hasattr(check, 'run_preflight_checks')

    def test_import_fetch(self):
        from installer import fetch
        assert hasattr(fetch, 'download_with_fallback')
        assert hasattr(fetch, 'extract_opencode_from_zip')
        assert hasattr(fetch, 'build_urls')
        assert hasattr(fetch, 'REPO')
        assert hasattr(fetch, 'BRANCH')

    def test_import_update(self):
        from installer import update
        assert hasattr(update, 'compute_diff')
        assert hasattr(update, 'read_local_version')
        assert hasattr(update, 'write_version_file')
        assert hasattr(update, 'needs_update')

    def test_import_deps(self):
        from installer import deps
        assert hasattr(deps, 'create_venv')
        assert hasattr(deps, 'check_pip_available')
        assert hasattr(deps, 'install_core_deps')

    def test_import_preflight(self):
        from installer import preflight
        assert hasattr(preflight, 'run_install')
        assert hasattr(preflight, 'apply_staging')
        assert hasattr(preflight, 'verify_installation')


class TestEndToEndZipExtraction:
    """Verify the full extract flow works with a synthetic zip."""
    def test_full_extract_and_module_load(self):
        d = tempfile.mkdtemp()
        zip_path = Path(d) / "repo.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("repo-master/.opencode/installer/__init__.py", "")
            zf.writestr("repo-master/.opencode/installer/ui.py", "print('ui ok')")
            zf.writestr("repo-master/.opencode/scripts/webnovel.py", "print('ok')")

        from installer.fetch import extract_opencode_from_zip
        extract_dir = Path(d) / "workspace"
        extract_opencode_from_zip(zip_path, extract_dir)

        assert (extract_dir / "installer" / "__init__.py").exists()
        assert (extract_dir / "installer" / "ui.py").exists()
        assert (extract_dir / "scripts" / "webnovel.py").exists()
