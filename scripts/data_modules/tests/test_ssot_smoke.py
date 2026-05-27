"""Smoke tests for SSOT enforcer event log."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest


class TestSSOTEventLog:
    def test_publish_and_read_events(self, tmp_path):
        from data_modules.ssot_enforcer import publish_event, read_events

        publish_event(tmp_path, "test_event", {"key": "value"}, chapter=1)
        events = read_events(tmp_path)
        assert len(events) == 1
        assert events[0]["event_type"] == "test_event"
        assert events[0]["chapter"] == 1
        assert events[0]["payload"]["key"] == "value"

    def test_publish_multiple_events_sequential_seq(self, tmp_path):
        from data_modules.ssot_enforcer import publish_event, read_events

        publish_event(tmp_path, "event_a", {}, chapter=1)
        publish_event(tmp_path, "event_b", {}, chapter=2)
        events = read_events(tmp_path)
        assert len(events) == 2
        assert events[0]["seq"] == 1
        assert events[1]["seq"] == 2

    def test_read_events_filter_by_type(self, tmp_path):
        from data_modules.ssot_enforcer import publish_event, read_events

        publish_event(tmp_path, "type_a", {}, chapter=1)
        publish_event(tmp_path, "type_b", {}, chapter=2)

        a_events = read_events(tmp_path, event_type="type_a")
        assert len(a_events) == 1
        assert a_events[0]["event_type"] == "type_a"

    def test_read_events_filter_by_chapter(self, tmp_path):
        from data_modules.ssot_enforcer import publish_event, read_events

        publish_event(tmp_path, "event", {}, chapter=1)
        publish_event(tmp_path, "event", {}, chapter=5)

        ch1 = read_events(tmp_path, chapter=1)
        assert len(ch1) == 1
        assert ch1[0]["chapter"] == 1

    def test_rebuild_state_json_from_events(self, tmp_path):
        from data_modules.ssot_enforcer import publish_event, rebuild_state_json

        publish_event(tmp_path, "chapter_status_changed",
                      {"status": "committed"}, chapter=1)
        publish_event(tmp_path, "chapter_status_changed",
                      {"status": "committed"}, chapter=2)
        publish_event(tmp_path, "entity_created",
                      {"entity_id": "萧炎", "entity_type": "角色", "entity_name": "萧炎"},
                      chapter=1)

        state = rebuild_state_json(tmp_path)
        ch_status = state["progress"]["chapter_status"]
        assert "1" in ch_status
        assert "2" in ch_status
        assert state["progress"]["current_chapter"] == 2
        assert "萧炎" in state["entities_v3"]

    def test_verify_consistency_clean(self, tmp_path):
        from data_modules.ssot_enforcer import publish_event, rebuild_state_json, verify_consistency

        # Manually build state.json the same way rebuild does
        publish_event(tmp_path, "chapter_status_changed",
                      {"status": "committed"}, chapter=1)
        state = rebuild_state_json(tmp_path)
        (tmp_path / ".webnovel").mkdir(exist_ok=True)
        (tmp_path / ".webnovel" / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        result = verify_consistency(tmp_path)
        assert result[0]["severity"] == "info"
