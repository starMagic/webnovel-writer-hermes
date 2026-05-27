"""Workflow checkpoint engine — fine-grained chapter stage tracking.

Industry reference: Saga/Checkpoint pattern (Temporal, Cadence, AWS Step Functions).

Each chapter progresses through defined stages:
  PLANNING   → outline loaded, context assembled
  DRAFTING   → AI writing first draft
  REVIEWING  → code checkers + 6 parallel LLM reviewers
  REVISING   → applying fix suggestions
  COMMITTED  → chapter-commit + projections updated

Each transition records: {stage, timestamp, chapter, metadata}
On interruption, read the last checkpoint to determine:
  - which stage the chapter was in
  - whether the stage completed or was mid-execution
  - what needs to be redone vs continued

Storage: .webnovel/workflow_checkpoints.json (append-only, compact per-chapter)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Stage ordering for progress tracking
STAGES = ("PLANNING", "DRAFTING", "REVIEWING", "REVISING", "COMMITTED")
_STAGE_INDEX = {s: i for i, s in enumerate(STAGES)}


def _checkpoint_path(project_root: Path) -> Path:
    return project_root / ".webnovel" / "workflow_checkpoints.json"


def _read_checkpoints(project_root: Path) -> dict:
    path = _checkpoint_path(project_root)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_checkpoints(project_root: Path, data: dict) -> None:
    path = _checkpoint_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(path))


def checkpoint(chapter: int, stage: str, project_root: Path,
               metadata: Optional[dict] = None) -> None:
    """Record a stage transition for a chapter."""
    if stage not in _STAGE_INDEX:
        raise ValueError(f"Unknown stage: {stage}. Must be one of {STAGES}")

    data = _read_checkpoints(project_root)
    ch_key = str(chapter)

    entry = {
        "stage": stage,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if metadata:
        entry["metadata"] = metadata

    data.setdefault(ch_key, []).append(entry)
    _write_checkpoints(project_root, data)


def current_stage(chapter: int, project_root: Path) -> Optional[str]:
    """Return the last recorded stage for a chapter, or None."""
    data = _read_checkpoints(project_root)
    entries = data.get(str(chapter), [])
    if not entries:
        return None
    return entries[-1]["stage"]


def stage_progress(chapter: int, project_root: Path) -> dict:
    """Return complete stage history and progress for a chapter."""
    data = _read_checkpoints(project_root)
    entries = data.get(str(chapter), [])
    last_stage = entries[-1]["stage"] if entries else None

    return {
        "chapter": chapter,
        "current_stage": last_stage,
        "completed_stages": [e["stage"] for e in entries],
        "total_steps": len(entries),
        "is_complete": last_stage == "COMMITTED",
        "next_stage": _next_stage(last_stage) if last_stage and last_stage != "COMMITTED" else None,
    }


def _next_stage(stage: str) -> Optional[str]:
    idx = _STAGE_INDEX.get(stage, -1)
    if idx < 0 or idx >= len(STAGES) - 1:
        return None
    return STAGES[idx + 1]


def all_chapters_progress(project_root: Path) -> dict:
    """Return progress summary for all chapters with checkpoints."""
    data = _read_checkpoints(project_root)
    summary = {}
    for ch, entries in sorted(data.items(), key=lambda x: int(x[0])):
        last = entries[-1]["stage"] if entries else None
        summary[int(ch)] = {
            "stage": last,
            "complete": last == "COMMITTED",
            "steps": len(entries),
        }
    return summary


def find_interrupted(project_root: Path,
                     progress: Optional[dict] = None) -> list[int]:
    """Find chapters that started but didn't reach COMMITTED."""
    if progress is None:
        progress = all_chapters_progress(project_root)
    return [ch for ch, info in progress.items()
            if not info["complete"]]


# ── CLI ───────────────────────────────────────────────────────────────


def cmd_workflow(args) -> int:
    project_root = Path(args.project_root).expanduser().resolve()

    if args.action == "checkpoint":
        checkpoint(args.chapter, args.stage, project_root,
                   metadata=json.loads(args.metadata) if getattr(args, 'metadata', None) else None)
        print(f"Chapter {args.chapter}: checkpointed {args.stage}")
        return 0

    if args.action == "status":
        if args.chapter:
            info = stage_progress(args.chapter, project_root)
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            info = all_chapters_progress(project_root)
            print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0

    if args.action == "interrupted":
        progress = all_chapters_progress(project_root)
        interrupted = find_interrupted(project_root, progress=progress)
        if interrupted:
            print(f"Interrupted chapters: {interrupted}")
            for ch in interrupted:
                info = stage_progress(ch, project_root)
                print(f"  Chapter {ch}: stage={info['current_stage']}, "
                      f"next={info['next_stage']}")
        else:
            print("No interrupted chapters.")
        return 0

    return 1


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Workflow checkpoint engine for chapter stage tracking")
    ap.add_argument("--project-root", required=True, help="Book project root")
    sub = ap.add_subparsers(dest="action", required=True)

    p_check = sub.add_parser("checkpoint", help="Record a stage transition")
    p_check.add_argument("--chapter", type=int, required=True)
    p_check.add_argument("--stage", choices=STAGES, required=True)
    p_check.add_argument("--metadata", help="JSON metadata")

    p_status = sub.add_parser("status", help="Show progress for chapters")
    p_status.add_argument("--chapter", type=int, help="Specific chapter, or all if omitted")

    sub.add_parser("interrupted", help="Find interrupted chapters")

    args = ap.parse_args()
    raise SystemExit(cmd_workflow(args))
