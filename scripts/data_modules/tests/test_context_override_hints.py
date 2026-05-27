"""Test override hints integration in context manager."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest


class TestOverrideHintsInjection:
    def test_load_override_hints_empty_when_no_contracts(self, tmp_path, monkeypatch):
        from data_modules.config import DataModulesConfig
        from data_modules.context_manager import ContextManager

        project = tmp_path / "book"
        (project / ".webnovel").mkdir(parents=True)
        (project / ".webnovel" / "state.json").write_text(
            json.dumps({"schema_version": "5.1", "progress": {}}), encoding="utf-8"
        )
        (project / "正文").mkdir(exist_ok=True)
        monkeypatch.setenv("WEBNOVEL_PROJECT_ROOT", str(project))

        config = DataModulesConfig(project_root=project)
        cm = ContextManager(config)
        hints = cm._load_override_hints(1)
        assert hints == ""

    def test_load_override_hints_returns_text_when_contracts_exist(self, tmp_path):
        from data_modules.config import DataModulesConfig
        from data_modules.context_manager import ContextManager
        from data_modules.override_contract_engine import add_override

        project = tmp_path / "book"
        (project / ".webnovel").mkdir(parents=True)
        (project / ".webnovel" / "state.json").write_text(
            json.dumps({"schema_version": "5.1", "progress": {}}), encoding="utf-8"
        )
        (project / "正文").mkdir(exist_ok=True)

        add_override(project, "power.flight",
                     "金丹期修士不能飞行", "获得混沌珠后可飞行",
                     "主角吸收混沌珠能量", chapter=5, domain="world_rule")

        config = DataModulesConfig(project_root=project)
        cm = ContextManager(config)
        hints = cm._load_override_hints(6)
        assert "power.flight" in hints
        assert "混沌珠" in hints

    def test_load_override_hints_excludes_future_overrides(self, tmp_path):
        from data_modules.config import DataModulesConfig
        from data_modules.context_manager import ContextManager
        from data_modules.override_contract_engine import add_override

        project = tmp_path / "book"
        (project / ".webnovel").mkdir(parents=True)
        (project / ".webnovel" / "state.json").write_text(
            json.dumps({"schema_version": "5.1", "progress": {}}), encoding="utf-8"
        )
        (project / "正文").mkdir(exist_ok=True)

        add_override(project, "power.flight",
                     "金丹期修士不能飞行", "获得混沌珠后可飞行",
                     "主角吸收混沌珠能量", chapter=10, domain="world_rule")

        config = DataModulesConfig(project_root=project)
        cm = ContextManager(config)
        hints = cm._load_override_hints(3)
        assert hints == ""  # override at ch10, not yet effective at ch3
