#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for review_pipeline.py"""

import sys
from pathlib import Path

import pytest


def test_clean_reviewer_output_handles_chinese_quotes():
    """reviewer 输出中的中文引号不应破坏 JSON 解析"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from review_pipeline import clean_reviewer_output

    raw = '{"description": "陈升回答能量剩余“二十二”次"}'
    result = clean_reviewer_output(raw)
    assert isinstance(result, dict)
    assert "二十二" in result.get("description", "")
