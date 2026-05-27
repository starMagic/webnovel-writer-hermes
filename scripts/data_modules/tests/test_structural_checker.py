#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for structural_checker.py"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from data_modules.structural_checker import run_checks


def _make_state(overrides=None):
    base = {
        "project_info": {"title": "测试", "genre": "修仙"},
        "progress": {"current_chapter": 21, "chapter_status": {}},
        "protagonist_state": {
            "name": "陈升",
            "location": {"current": "废弃工厂", "last_chapter": 20},
        },
        "strand_tracker": {
            "last_quest_chapter": 20,
            "last_fire_chapter": 15,
            "last_constellation_chapter": 18,
            "current_dominant": "quest",
            "chapters_since_switch": 3,
            "history": [
                {"chapter": 18, "dominant": "quest"},
                {"chapter": 19, "dominant": "quest"},
                {"chapter": 20, "dominant": "quest"},
            ],
        },
        "plot_threads": {
            "foreshadowing": [
                {"id": "f1", "status": "未回收", "planted_chapter": 1},
                {"id": "f2", "status": "未回收", "planted_chapter": 3},
                {"id": "f3", "status": "已回收", "planted_chapter": 5},
            ]
        },
    }
    if overrides:
        _deep_update(base, overrides)
    return base


def _deep_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v)
        else:
            d[k] = v


def _write_state(tmpdir, state):
    webnovel = tmpdir / ".webnovel"
    webnovel.mkdir()
    (webnovel / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _write_memory_scratchpad(tmpdir, entries):
    webnovel = tmpdir / ".webnovel"
    webnovel.mkdir(exist_ok=True)
    items = []
    for i, entry in enumerate(entries):
        item = {
            "id": f"mem-{i}",
            "layer": "semantic",
            "category": "character_state",
            "subject": "test",
            "field": "test",
            "value": "test",
            "status": entry.get("status", "active"),
            "source_chapter": 1,
            "evidence": [],
            "updated_at": "2026-05-01",
        }
        item.update(entry)
        items.append(item)
    # Match real format: dict of buckets
    data = {"character_state": items, "story_facts": [], "world_rules": [],
            "timeline": [], "open_loops": [], "reader_promises": [],
            "relationships": [], "meta": {}}
    (webnovel / "memory_scratchpad.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _write_contract(tmpdir, chapter):
    chapters = tmpdir / ".story-system" / "chapters"
    chapters.mkdir(parents=True)
    (chapters / f"chapter_{chapter:03d}.json").write_text("{}", encoding="utf-8")


def test_strand_quest_too_long():
    """quest 连续超过 5 章应 blocking"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state({
            "strand_tracker": {
                "chapters_since_switch": 6,
                "history": [
                    {"chapter": 16, "dominant": "quest"},
                    {"chapter": 17, "dominant": "quest"},
                    {"chapter": 18, "dominant": "quest"},
                    {"chapter": 19, "dominant": "quest"},
                    {"chapter": 20, "dominant": "quest"},
                    {"chapter": 21, "dominant": "quest"},
                ],
            }
        })
        _write_state(root, state)
        _write_contract(root, 22)
        result = run_checks(root, 22)
        check = _find_check(result, "strand_balance")
        assert check["passed"] is False
        assert check["severity"] == "blocking"


def test_strand_constellation_absent():
    """constellation 从未激活且超过 8 章应 blocking"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state({
            "strand_tracker": {
                "last_constellation_chapter": 0,
                "chapters_since_switch": 2,
            }
        })
        _write_state(root, state)
        _write_contract(root, 10)
        result = run_checks(root, 10)
        check = _find_check(result, "strand_balance")
        assert check["passed"] is False
        assert "从未激活" in check["detail"]


def test_strand_ok():
    """正常 strand 状态应通过"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state()
        _write_state(root, state)
        _write_contract(root, 22)
        result = run_checks(root, 22)
        check = _find_check(result, "strand_balance")
        assert check["passed"] is True


def test_entity_freshness_stale():
    """主角位置落后 >= 5 章且 current 为空应 blocking"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state({
            "protagonist_state": {
                "location": {"current": "", "last_chapter": 16},
            }
        })
        _write_state(root, state)
        _write_contract(root, 22)
        result = run_checks(root, 22)
        check = _find_check(result, "entity_freshness")
        assert check["passed"] is False
        assert check["severity"] == "blocking"


def test_entity_freshness_ok():
    """位置最近更新应通过"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state({
            "protagonist_state": {
                "location": {"current": "废弃工厂", "last_chapter": 21},
            }
        })
        _write_state(root, state)
        _write_contract(root, 22)
        result = run_checks(root, 22)
        check = _find_check(result, "entity_freshness")
        assert check["passed"] is True


def test_entity_freshness_gap2_ok():
    """位置 2 章未更新在新阈值下应通过"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state({
            "protagonist_state": {
                "location": {"current": "废弃工厂", "last_chapter": 20},
            }
        })
        _write_state(root, state)
        _write_contract(root, 22)
        result = run_checks(root, 22)
        check = _find_check(result, "entity_freshness")
        assert check["passed"] is True


def test_entity_freshness_stale_but_value_present():
    """位置值存在但 last_chapter 陈旧应降级为 warning"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state({
            "protagonist_state": {
                "location": {"current": "城西废墟", "last_chapter": 16},
            }
        })
        _write_state(root, state)
        _write_contract(root, 22)
        result = run_checks(root, 22)
        check = _find_check(result, "entity_freshness")
        assert check["passed"] is True
        assert check["severity"] == "warning"


def test_memory_bloat():
    """过期率超过 30% 应 warning"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state()
        _write_state(root, state)
        _write_contract(root, 22)
        entries = [{"status": "active"} for _ in range(10)] + [{"status": "outdated"} for _ in range(6)]
        _write_memory_scratchpad(root, entries)
        result = run_checks(root, 22)
        check = _find_check(result, "memory_bloat")
        assert check["passed"] is False
        assert check["severity"] == "warning"


def test_memory_bloat_ok():
    """过期率低于阈值应通过"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state()
        _write_state(root, state)
        _write_contract(root, 22)
        entries = [{"status": "active"} for _ in range(10)] + [{"status": "outdated"} for _ in range(2)]
        _write_memory_scratchpad(root, entries)
        result = run_checks(root, 22)
        check = _find_check(result, "memory_bloat")
        assert check["passed"] is True


def test_debt_burden():
    """未回收伏笔超过 5 条应 warning"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state({
            "plot_threads": {
                "foreshadowing": [
                    {"id": f"f{i}", "status": "未回收", "planted_chapter": i}
                    for i in range(1, 8)
                ]
            }
        })
        _write_state(root, state)
        _write_contract(root, 22)
        result = run_checks(root, 22)
        check = _find_check(result, "debt_burden")
        assert check["passed"] is False


def test_debt_burden_ok():
    """伏笔数量正常应通过"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state()
        _write_state(root, state)
        _write_contract(root, 22)
        result = run_checks(root, 22)
        check = _find_check(result, "debt_burden")
        assert check["passed"] is True


def test_contract_coverage_missing():
    """chapter contract 缺失应 blocking"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state()
        _write_state(root, state)
        # no contract written
        result = run_checks(root, 22)
        check = _find_check(result, "contract_coverage")
        assert check["passed"] is False
        assert check["severity"] == "blocking"


def test_all_pass():
    """健康项目全部通过"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = _make_state()
        _write_state(root, state)
        _write_contract(root, 22)
        entries = [{"status": "active"} for _ in range(5)]
        _write_memory_scratchpad(root, entries)
        result = run_checks(root, 22)
        assert result["passed"] is True
        for c in result["checks"]:
            assert c["passed"] is True, f"{c['name']} should pass but didn't: {c.get('detail','')}"


def _find_check(result, name):
    for c in result["checks"]:
        if c["name"] == name:
            return c
    raise KeyError(f"check '{name}' not found in {[c['name'] for c in result['checks']]}")
