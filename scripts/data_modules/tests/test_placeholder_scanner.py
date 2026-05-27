#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys

import pytest

from data_modules.placeholder_scanner import scan_placeholders, load_known_placeholders


def test_placeholder_scanner_finds_pending_marks(tmp_path):
    outline_dir = tmp_path / "大纲"
    settings_dir = tmp_path / "设定集"
    outline_dir.mkdir()
    settings_dir.mkdir()
    (outline_dir / "第1卷-卷纲.md").write_text(
        "第一位女主（暂名）| [待章纲拆分时具体设计]\n",
        encoding="utf-8",
    )
    (settings_dir / "主角卡.md").write_text("- 兄弟：{占位}\n", encoding="utf-8")

    results = scan_placeholders(tmp_path)

    assert len(results) == 3
    assert any(item["pattern"] == "（暂名）" for item in results)
    assert any(item["pattern"].startswith("[待章纲") for item in results)
    assert any(item["pattern"] == "{占位}" for item in results)


def test_webnovel_placeholder_scan_cli_forwards_project_root(monkeypatch, tmp_path, capsys):
    import data_modules.webnovel as webnovel_module

    project_root = tmp_path / "book"
    (project_root / ".webnovel").mkdir(parents=True)
    (project_root / ".webnovel" / "state.json").write_text("{}", encoding="utf-8")
    (project_root / "大纲").mkdir()
    (project_root / "大纲" / "总纲.md").write_text("[待补充]\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["webnovel", "--project-root", str(project_root), "placeholder-scan"])

    with pytest.raises(SystemExit) as exc:
        webnovel_module.main()

    assert int(exc.value.code or 0) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["placeholders"][0]["file"] == "大纲/总纲.md"


def test_load_known_placeholders_returns_set(tmp_path):
    webnovel = tmp_path / ".webnovel"
    webnovel.mkdir()
    data = {
        "ignored": [
            {"file": "大纲/总纲.md", "line": 4, "text": "（暂名）", "reason": "暂时未命名"},
            {"file": "设定集/主角卡.md", "line": 1, "text": "{占位}", "reason": "待补充"},
        ]
    }
    (webnovel / "known_placeholders.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    result = load_known_placeholders(tmp_path)
    expected = {("大纲/总纲.md", 4, "（暂名）"), ("设定集/主角卡.md", 1, "{占位}")}
    assert result == expected


def test_load_known_placeholders_missing_file(tmp_path):
    assert load_known_placeholders(tmp_path) == set()


def test_load_known_placeholders_malformed(tmp_path):
    webnovel = tmp_path / ".webnovel"
    webnovel.mkdir()
    (webnovel / "known_placeholders.json").write_text(
        "not valid json", encoding="utf-8"
    )
    assert load_known_placeholders(tmp_path) == set()


def test_placeholder_scan_filters_known(tmp_path, monkeypatch):
    """已知占位应被过滤掉。"""
    outline_dir = tmp_path / "大纲"
    settings_dir = tmp_path / "设定集"
    outline_dir.mkdir()
    settings_dir.mkdir()
    (outline_dir / "第1卷-卷纲.md").write_text(
        "第一位女主（暂名）\n", encoding="utf-8"
    )
    (settings_dir / "主角卡.md").write_text("- 兄弟：{占位}\n", encoding="utf-8")

    # 创建忽略文件
    webnovel = tmp_path / ".webnovel"
    webnovel.mkdir()
    ignore_data = {
        "ignored": [
            {"file": "大纲/第1卷-卷纲.md", "line": 1, "text": "（暂名）", "reason": "已知"},
        ]
    }
    (webnovel / "known_placeholders.json").write_text(
        json.dumps(ignore_data, ensure_ascii=False), encoding="utf-8"
    )

    results = scan_placeholders(tmp_path)
    assert len(results) == 2  # both placeholders found

    # 现在测试通过 main() 调用过滤
    import io
    from data_modules.placeholder_scanner import main as ps_main

    monkeypatch.setattr(
        sys, "argv",
        ["placeholder-scan", "--project-root", str(tmp_path), "--format", "text"],
    )
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    with pytest.raises(SystemExit):
        ps_main()
    monkeypatch.undo()

    output = captured.getvalue()
    assert "（暂名）" not in output
    assert "{占位}" in output


def test_placeholder_scan_exits_nonzero_when_placeholders_found(tmp_path, monkeypatch):
    """当存在占位时，CLI 应返回退出码 1"""
    import io
    from data_modules.placeholder_scanner import main as ps_main

    outline_dir = tmp_path / "大纲"
    outline_dir.mkdir()
    (tmp_path / ".webnovel").mkdir()
    (tmp_path / ".webnovel" / "state.json").write_text("{}", encoding="utf-8")
    (outline_dir / "总纲.md").write_text("[待补充]\n", encoding="utf-8")

    monkeypatch.setattr(
        sys, "argv",
        ["placeholder-scan", "--project-root", str(tmp_path), "--format", "json"],
    )
    with pytest.raises(SystemExit) as exc:
        ps_main()
    assert exc.value.code == 1
