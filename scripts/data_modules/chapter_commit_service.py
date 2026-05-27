#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from chapter_outline_loader import volume_num_for_chapter_from_state

from .config import DataModulesConfig
from .event_log_store import EventLogStore
from .event_projection_router import EventProjectionRouter
from .story_contracts import write_json
from .index_manager import IndexManager
from .override_ledger_service import (
    AmendProposalTrigger,
    ensure_override_ledger_columns,
    persist_amend_proposals,
)

# 伏笔默认偿还章数：创建债务时默认要求 10 章内偿还
_FORESHADOW_DUE_OFFSET = 10


class ChapterCommitService:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        state_file = self.project_root / ".webnovel" / "state.json"
        if not state_file.is_file():
            raise FileNotFoundError(
                f"无效的项目根目录: {self.project_root}（缺少 .webnovel/state.json）。"
                "请确认 --project-root 指向正确的书项目目录。"
            )

    def build_commit(
        self,
        chapter: int,
        review_result: Dict[str, Any],
        fulfillment_result: Dict[str, Any],
        disambiguation_result: Dict[str, Any],
        extraction_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        rejected = bool(review_result.get("blocking_count")) or bool(
            fulfillment_result.get("missed_nodes")
        ) or bool(disambiguation_result.get("pending"))
        status = "rejected" if rejected else "accepted"
        volume = volume_num_for_chapter_from_state(self.project_root, chapter) or 1
        return {
            "meta": {
                "schema_version": "story-system/v1",
                "chapter": chapter,
                "status": status,
            },
            "contract_refs": {
                "master": ".story-system/MASTER_SETTING.json",
                "volume": f".story-system/volumes/volume_{volume:03d}.json",
                "chapter": f".story-system/chapters/chapter_{chapter:03d}.json",
                "review": f".story-system/reviews/chapter_{chapter:03d}.review.json",
            },
            "provenance": {
                "write_fact_role": "chapter_commit",
                "projection_role": "derived_read_models",
                "legacy_state_role": "projection_only",
            },
            "outline_snapshot": {
                "planned_nodes": fulfillment_result.get("planned_nodes", []),
                "covered_nodes": fulfillment_result.get("covered_nodes", []),
                "missed_nodes": fulfillment_result.get("missed_nodes", []),
                "extra_nodes": fulfillment_result.get("extra_nodes", []),
            },
            "review_result": review_result,
            "fulfillment_result": fulfillment_result,
            "disambiguation_result": disambiguation_result,
            "accepted_events": extraction_result.get("accepted_events", []),
            "state_deltas": extraction_result.get("state_deltas", []),
            "entity_deltas": extraction_result.get("entity_deltas", []),
            "entities_appeared": extraction_result.get("entities_appeared", []),
            "scenes": extraction_result.get("scenes", []),
            "chapter_meta": extraction_result.get("chapter_meta", {}),
            "dominant_strand": extraction_result.get("dominant_strand", ""),
            "summary_text": extraction_result.get("summary_text", ""),
            "projection_status": {
                "state": "pending",
                "index": "pending",
                "summary": "pending",
                "memory": "pending",
                "vector": "pending",
            },
        }

    def persist_commit(self, payload: Dict[str, Any]) -> Path:
        target = self.project_root / ".story-system" / "commits"
        target.mkdir(parents=True, exist_ok=True)
        path = target / f"chapter_{int(payload['meta']['chapter']):03d}.commit.json"
        write_json(path, payload)
        return path

    def _sync_foreshadowing(self, commit_payload: dict) -> None:
        """Sync foreshadowing events from commit payload to debt tracker."""
        events = commit_payload.get("accepted_events", [])
        if not events:
            return
        chapter = int(commit_payload.get("meta", {}).get("chapter", 0))
        if chapter <= 0:
            return
        idx = IndexManager(DataModulesConfig.from_project_root(str(self.project_root)))
        for evt in events:
            if not isinstance(evt, dict):
                continue
            etype = evt.get("event_type", "")
            payload = evt.get("payload") or {}
            subject = evt.get("subject", payload.get("subject", ""))
            content = payload.get("content", "")
            if etype == "open_loop_created":
                due = chapter + _FORESHADOW_DUE_OFFSET
                note = content or subject or f"ch{chapter} foreshadowing"
                idx.create_simple_debt(
                    debt_type="foreshadowing",
                    source_chapter=chapter,
                    due_chapter=due,
                    note=note,
                    subject=subject,
                )
            elif etype in ("open_loop_closed", "promise_paid_off"):
                idx.resolve_debt_by_subject(subject=subject, chapter=chapter)

    def apply_projections(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if payload["meta"]["status"] != "accepted":
            return payload

        chapter = int((payload.get("meta") or {}).get("chapter") or 0)
        EventLogStore(self.project_root).write_events(chapter, payload.get("accepted_events", []))

        proposals = AmendProposalTrigger().check(chapter, payload.get("accepted_events", []))
        if proposals:
            manager = IndexManager(DataModulesConfig.from_project_root(self.project_root))
            with manager._get_conn() as conn:
                ensure_override_ledger_columns(conn)
                persist_amend_proposals(conn, chapter, proposals)
                conn.commit()

        from .index_projection_writer import IndexProjectionWriter
        from .memory_projection_writer import MemoryProjectionWriter
        from .state_projection_writer import StateProjectionWriter
        from .summary_projection_writer import SummaryProjectionWriter
        from .vector_projection_writer import VectorProjectionWriter

        writers = {
            "state": StateProjectionWriter(self.project_root),
            "index": IndexProjectionWriter(self.project_root),
            "summary": SummaryProjectionWriter(self.project_root),
            "memory": MemoryProjectionWriter(self.project_root),
            "vector": VectorProjectionWriter(self.project_root),
        }
        required_writers = set(EventProjectionRouter().required_writers(payload))
        for name, writer in writers.items():
            if name not in required_writers:
                payload["projection_status"][name] = "skipped"
                continue
            try:
                result = writer.apply(payload)
                payload["projection_status"][name] = "done" if result.get("applied") else "skipped"
            except Exception as exc:
                payload["projection_status"][name] = f"failed:{exc}"
        self.persist_commit(payload)
        self._sync_foreshadowing(payload)
        return payload
