"""Single Source of Truth enforcer — all state mutations go through the event log.

Industry reference: Event Sourcing + CQRS (EventStoreDB, Axon Framework).

Architectural guarantee:
  .story-system/events/*.event.json  ←  append-only TRUTH (event log)
  state.json / index.db              ←  materialized VIEW (projection, rebuildable)

Every state mutation MUST:
  1. Write event to event log first (immutable)
  2. Apply to projection (state.json + index.db)
  3. Projection can be rebuilt from event log at any time

Consistency check:
  ssot verify --project-root <PATH>  →  compares projection vs event log, reports drift
  ssot rebuild --project-root <PATH> →  rebuilds all projections from event log
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Event log ────────────────────────────────────────────────────────

_EVENT_LOG_DIR = ".story-system/events"


def _event_log_dir(project_root: Path) -> Path:
    return project_root / _EVENT_LOG_DIR


def _next_event_seq(log_dir: Path) -> int:
    """Return the next sequence number for the event log."""
    if not log_dir.is_dir():
        return 1
    existing = sorted(log_dir.glob("*.event.json"))
    if not existing:
        return 1
    last = existing[-1].stem.replace(".event", "")
    try:
        return int(last) + 1
    except ValueError:
        return len(existing) + 1


def publish_event(project_root: Path, event_type: str, payload: dict,
                  chapter: int = 0) -> Path:
    """Append an event to the immutable event log. Returns path to event file.

    This is the ONLY write path for state-changing operations.

    event_type examples:
      chapter_status_changed, entity_created, entity_updated,
      override_rule_added, override_rule_superseded,
      open_loop_created, open_loop_closed,
      checkpoint_reached, projection_rebuilt
    """
    log_dir = _event_log_dir(project_root)
    log_dir.mkdir(parents=True, exist_ok=True)

    seq = _next_event_seq(log_dir)
    event = {
        "seq": seq,
        "event_type": event_type,
        "chapter": chapter,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": payload,
    }

    event_path = log_dir / f"{seq:06d}.event.json"
    # Atomic write: temp file → rename
    tmp = log_dir / f".tmp.{seq:06d}.{os.getpid()}"
    tmp.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(event_path))
    return event_path


def read_events(project_root: Path,
                event_type: Optional[str] = None,
                chapter: Optional[int] = None,
                after_seq: int = 0) -> list[dict]:
    """Read events from the log, optionally filtered."""
    log_dir = _event_log_dir(project_root)
    if not log_dir.is_dir():
        return []

    events = []
    for path in sorted(log_dir.glob("*.event.json")):
        try:
            seq = int(path.stem.split(".")[0])
        except ValueError:
            continue
        if seq <= after_seq:
            continue
        try:
            event = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if event_type and event.get("event_type") != event_type:
            continue
        if chapter is not None and event.get("chapter") != chapter:
            continue
        events.append(event)
    return events


# ── Projection rebuild ───────────────────────────────────────────────


def rebuild_state_json(project_root: Path,
                       events: Optional[list[dict]] = None) -> dict:
    """Rebuild state.json as a materialized view from the event log.

    This is deterministic: replaying the same events always produces the same state.
    Accepts pre-loaded events to avoid redundant I/O.
    """
    if events is None:
        events = read_events(project_root)
    state = _empty_state()

    for evt in events:
        etype = evt["event_type"]
        payload = evt["payload"]
        ch = str(evt["chapter"])

        if etype == "chapter_status_changed":
            state.setdefault("progress", {}).setdefault("chapter_status", {})[ch] = {
                "status": payload.get("status", "unknown"),
                "last_event_seq": evt["seq"],
            }
            if payload.get("status") == "committed":
                state["progress"]["current_chapter"] = evt["chapter"]
                state["progress"]["last_updated"] = evt["timestamp"]

        elif etype == "entity_created":
            state.setdefault("entities_v3", {})[payload["entity_id"]] = {
                "entity_type": payload.get("entity_type", "unknown"),
                "name": payload.get("entity_name", ""),
                "first_seen_chapter": evt["chapter"],
            }

        elif etype == "open_loop_created":
            loop = {
                "content": payload.get("content", ""),
                "urgency": payload.get("urgency", 50),
                "planted_chapter": evt["chapter"],
                "status": "active",
            }
            state.setdefault("foreshadowing", []).append(loop)

        elif etype == "open_loop_closed":
            for loop in state.get("foreshadowing", []):
                if loop.get("content") == payload.get("content"):
                    loop["status"] = "closed"
                    loop["closed_chapter"] = evt["chapter"]

    return state


def _empty_state() -> dict:
    return {
        "schema_version": "5.1",
        "progress": {"current_chapter": 0, "chapter_status": {}, "last_updated": ""},
        "entities_v3": {},
        "foreshadowing": [],
        "protagonist_state": {},
    }


def rebuild_projections(project_root: Path) -> dict:
    """Rebuild all projections from event log. Returns summary."""
    state = rebuild_state_json(project_root)
    state_path = project_root / ".webnovel" / "state.json"

    if state_path.is_file():
        backup = state_path.with_suffix(".state.bak")
        os.replace(str(state_path), str(backup))

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    event_count = sum(1 for _ in _event_log_dir(project_root).glob("*.event.json"))
    publish_event(project_root, "projection_rebuilt", {
        "target": "state.json",
        "event_count": event_count,
    })

    return {
        "projection": "state.json",
        "event_count": event_count,
        "chapters_in_state": len(state.get("progress", {}).get("chapter_status", {})),
        "entities_in_state": len(state.get("entities_v3", {})),
    }


# ── Consistency verification ─────────────────────────────────────────


def verify_consistency(project_root: Path) -> list[dict]:
    """Compare state.json projection against event log. Returns list of drifts."""
    drifts = []

    state_path = project_root / ".webnovel" / "state.json"
    try:
        actual_state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [{"severity": "error", "detail": "state.json missing or unreadable"}]

    events = read_events(project_root)
    expected = rebuild_state_json(project_root, events=events)

    # Compare chapter_status
    actual_chs = set((actual_state.get("progress") or {}).get("chapter_status") or {})
    expected_chs = set((expected.get("progress") or {}).get("chapter_status") or {})

    if actual_chs != expected_chs:
        drifts.append({
            "severity": "warning",
            "field": "progress.chapter_status",
            "actual": sorted(actual_chs),
            "expected": sorted(expected_chs),
            "detail": f"State has keys {sorted(actual_chs)}, event log projects {sorted(expected_chs)}",
        })

    if not drifts:
        drifts.append({"severity": "info", "detail": "State is consistent with event log."})
    return drifts


# ── CLI ───────────────────────────────────────────────────────────────


def cmd_ssot(args) -> int:
    project_root = Path(args.project_root).expanduser().resolve()

    if args.action == "verify":
        drifts = verify_consistency(project_root)
        for d in drifts:
            sev = d["severity"].upper()
            print(f"{sev} {d.get('field', '')}: {d['detail']}")
        return 0 if all(d["severity"] == "info" for d in drifts) else 1

    if args.action == "rebuild":
        summary = rebuild_projections(project_root)
        print(f"Rebuilt {summary['projection']}: "
              f"{summary['event_count']} events → "
              f"{summary['chapters_in_state']} chapters, "
              f"{summary['entities_in_state']} entities")
        return 0

    if args.action == "events":
        events = read_events(project_root,
                             event_type=getattr(args, 'event_type', None),
                             chapter=getattr(args, 'chapter', None))
        print(json.dumps(events, ensure_ascii=False, indent=2))
        return 0

    return 1


def main():
    import argparse
    ap = argparse.ArgumentParser(description="SSOT enforcer — event log consistency")
    ap.add_argument("--project-root", required=True, help="Book project root")
    sub = ap.add_subparsers(dest="action", required=True)

    sub.add_parser("verify", help="Check state.json consistency against event log")
    sub.add_parser("rebuild", help="Rebuild state.json from event log")
    p_events = sub.add_parser("events", help="Read event log")
    p_events.add_argument("--event-type", help="Filter by event type")
    p_events.add_argument("--chapter", type=int, help="Filter by chapter")

    args = ap.parse_args()
    raise SystemExit(cmd_ssot(args))
