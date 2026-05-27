"""Detect and mark dirty entities in index.db — pinyin, snake_case, and other
non-CJK entity IDs that LLMs occasionally produce during extraction.

An entity is considered "clean" if its ID:
  - contains at least one CJK character (Chinese/Japanese/Korean unified ideograph)
  - uses standard separators: underscores, hyphens, or forward slashes between CJK parts

Dirty entity examples: "xiao_yan", "XiaoYan", "fire_spirit", "main_character"
Clean entity examples: "萧炎", "主角·萧炎", "火焰精灵"

Operation:
  --mark-invalid  Write dirty entities to invalid_facts table for manual review
"""

import sqlite3
import re
import sys
from pathlib import Path

_CJK_RANGE = re.compile(r'[一-鿿㐀-䶿豈-﫿]')


def _is_dirty(entity_id: str) -> bool:
    """An entity ID is dirty if it has no CJK characters."""
    if not entity_id or not isinstance(entity_id, str):
        return True
    return not bool(_CJK_RANGE.search(entity_id))


def _scan_dirty_entities(db_path: Path) -> list[dict]:
    """Return list of dirty entities from index.db entities table."""
    if not db_path.is_file():
        print(f"ERROR: index.db not found at {db_path}", file=sys.stderr)
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, entity_id, entity_type, entity_name, chapter_first_seen "
            "FROM entities ORDER BY chapter_first_seen"
        ).fetchall()

        dirty = []
        for row in rows:
            eid = row["entity_id"] or row["id"]
            if _is_dirty(eid):
                dirty.append({
                    "entity_id": eid,
                    "entity_type": row["entity_type"],
                    "entity_name": row["entity_name"],
                    "chapter_first_seen": row["chapter_first_seen"],
                })
        return dirty
    finally:
        conn.close()


def _mark_invalid(db_path: Path, entities: list[dict]) -> int:
    """Write dirty entities to invalid_facts table. Returns count written."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invalid_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT,
                entity_type TEXT,
                entity_name TEXT,
                chapter INTEGER,
                reason TEXT,
                marked_at TEXT DEFAULT (datetime('now')),
                resolved INTEGER DEFAULT 0
            )
        """)
        count = 0
        for e in entities:
            conn.execute(
                "INSERT INTO invalid_facts (entity_id, entity_type, entity_name, chapter, reason) "
                "VALUES (?, ?, ?, ?, ?)",
                (e["entity_id"], e["entity_type"], e["entity_name"],
                 e["chapter_first_seen"], "dirty_entity_id: non-CJK")
            )
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def cmd_entity_clean(args) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    db_path = project_root / ".webnovel" / "index.db"

    dirty = _scan_dirty_entities(db_path)
    if not dirty:
        print("No dirty entities found.")
        return 0

    print(f"Found {len(dirty)} dirty entities:")
    for e in dirty:
        print(f"  [{e['entity_type']}] {e['entity_id']} → {e['entity_name']} (ch{e['chapter_first_seen']})")

    if args.mark_invalid:
        count = _mark_invalid(db_path, dirty)
        print(f"\nMarked {count} entities in invalid_facts. Review manually, then re-extract affected chapters.")
    else:
        print("\nDry run. Use --mark-invalid to flag for review.")

    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Detect and mark non-CJK entity IDs in index.db")
    ap.add_argument("--project-root", required=True, help="Book project root")
    ap.add_argument("--mark-invalid", action="store_true", help="Write dirty entities to invalid_facts table")
    args = ap.parse_args()
    raise SystemExit(cmd_entity_clean(args))
