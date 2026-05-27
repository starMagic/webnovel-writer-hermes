#!/usr/bin/env python3
"""Chapter collector — scan 正文/ for chapter files, validate, extract titles."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, NamedTuple


class ChapterInfo(NamedTuple):
    index: int
    title: str
    path: Path
    volume: int


def collect_chapters(
    project_root: Path,
    range_spec: Optional[str] = None,
    volume: Optional[int] = None,
) -> list[ChapterInfo]:
    """Scan 正文/ for chapter files, return sorted list with metadata."""
    chapters_dir = project_root / "正文"
    if not chapters_dir.is_dir():
        return []

    try:
        from chapter_paths import extract_chapter_num_from_filename
    except ImportError:
        from scripts.chapter_paths import extract_chapter_num_from_filename

    candidates: list[tuple[int, Path]] = []
    for f in sorted(chapters_dir.rglob("第*章*.md")):
        num = extract_chapter_num_from_filename(f.name)
        if num is not None:
            candidates.append((num, f))

    candidates.sort(key=lambda x: x[0])

    if volume is not None:
        filtered: list[tuple[int, Path]] = []
        for n, f in candidates:
            vol = _resolve_volume_from_path(f, project_root)
            if vol == volume:
                filtered.append((n, f))
        candidates = filtered

    if range_spec and range_spec != "all":
        max_num = max(c[0] for c in candidates) if candidates else 0
        allowed = _parse_range(range_spec, max_num=max_num)
        candidates = [(n, f) for n, f in candidates if n in allowed]

    total = len(candidates)
    result: list[ChapterInfo] = []
    for i, (num, path) in enumerate(candidates, 1):
        title = _extract_title(path)
        vol = _resolve_volume_from_path(path, project_root)
        result.append(ChapterInfo(index=num, title=title, path=path, volume=vol))
        print(f"  [{i}/{total}] 第{num}章 {title}")

    _validate(result)

    return result


def _resolve_volume_from_path(path: Path, project_root: Path) -> int:
    rel = path.relative_to(project_root)
    for part in rel.parts:
        m = re.match(r"第(\d+)卷", part)
        if m:
            return int(m.group(1))

    try:
        from chapter_paths import extract_chapter_num_from_filename, volume_num_for_chapter
    except ImportError:
        from scripts.chapter_paths import extract_chapter_num_from_filename, volume_num_for_chapter

    num = extract_chapter_num_from_filename(path.name)
    if num is not None:
        return volume_num_for_chapter(num)
    return 1


def _extract_title(path: Path) -> str:
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                m = re.match(r"^#{1,3}\s+(.*)", stripped)
                if m:
                    return m.group(1).strip()
                return stripped
    except Exception:
        return "无标题"

    # No non-empty content — fallback to filename
    try:
        from chapter_paths import extract_chapter_num_from_filename
    except ImportError:
        from scripts.chapter_paths import extract_chapter_num_from_filename
    num = extract_chapter_num_from_filename(path.name)
    return f"第{num}章" if num else "无标题"


def _validate(chapters: list[ChapterInfo]) -> None:
    if not chapters:
        return
    indices = [ch.index for ch in chapters]  # already sorted
    seen: set[int] = set()
    dups: set[int] = set()
    for idx in indices:
        if idx in seen:
            dups.add(idx)
        seen.add(idx)
    if dups:
        dup_str = ", ".join(str(d) for d in sorted(dups))
        print(f"错误: 存在重复章节号: {dup_str}")
        raise SystemExit(1)

    missing_count = 0
    for i in range(indices[0], indices[-1]):
        if i not in seen:
            if missing_count == 0:
                print(f"警告: 第{i}章缺失")
            missing_count += 1
            if missing_count > 20:
                print("  ... (超过 20 章缺失，省略后续警告)")
                break


def _parse_range(spec: str, max_num: int = 0) -> set[int]:
    """Parse range string: '1-50', '1,3,5', 'all'."""
    allowed: set[int] = set()
    try:
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                lo_s, hi_s = part.split("-", 1)
                lo, hi = int(lo_s.strip()), int(hi_s.strip())
                allowed.update(range(lo, hi + 1))
            else:
                allowed.add(int(part))
    except ValueError:
        print(f"错误: 章节范围格式无效，预期格式: 1-50 / 1,3,5，实际收到: {spec}")
        return set()
    if max_num > 0:
        before = len(allowed)
        allowed = {n for n in allowed if 1 <= n <= max_num}
        dropped = before - len(allowed)
        if dropped > 0:
            print(f"警告: {dropped} 个章节号超出实际范围(1-{max_num})，已忽略")
    return allowed
