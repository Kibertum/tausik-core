"""TAUSIK KnowledgeMixin -- memory, decisions, graph."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, validate_content, validate_length
from project_types import VALID_EDGE_RELATIONS, VALID_MEMORY_TYPES, VALID_NODE_TYPES

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


class KnowledgeMixin:
    """Memory, decisions, and graph relationships."""

    be: SQLiteBackend

    # --- Memory ---

    def memory_add(
        self,
        mem_type: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        task_slug: str | None = None,
    ) -> str:
        if mem_type not in VALID_MEMORY_TYPES:
            raise ServiceError(
                f"Invalid memory type '{mem_type}'. Valid: {', '.join(sorted(VALID_MEMORY_TYPES))}"
            )
        from tausik_utils import safe_single_line

        validate_length("title", title)
        validate_content("content", content)
        title = safe_single_line(title) or title
        mid = self.be.memory_add(mem_type, title, content, tags, task_slug)
        from brain_universality import emit_universality_hint

        emit_universality_hint(f"{title}\n{content}")
        return f"Memory #{mid} ({mem_type}) saved."

    def memory_list(
        self,
        mem_type: str | None = None,
        n: int = 50,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        return self.be.memory_list(mem_type, n, include_archived=include_archived)

    def memory_search(
        self,
        query: str,
        include_cq: bool = True,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """Search local memory + optional cq cross-project knowledge."""
        local = self.be.memory_search(query, include_archived=include_archived)
        if not include_cq:
            return local
        # Try cq if configured
        try:
            from cq_client import get_cq_client

            config = self._load_config()
            client = get_cq_client(config)
            if client:
                domains = query.lower().split()[:3]  # Use query words as domains
                cq_results = client.query(domains, limit=3)
                for u in cq_results:
                    insight = u.get("insight", {})
                    conf = u.get("evidence", {}).get("confidence", 0)
                    local.append(
                        {
                            "id": 0,
                            "type": "cq",
                            "title": f"[cq {conf:.0%}] {insight.get('summary', '')}",
                            "content": insight.get("detail", ""),
                            "tags": ",".join(u.get("domain", [])),
                        }
                    )
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            pass  # cq unavailable -- graceful degradation
        return local

    def _load_config(self) -> dict[str, Any]:
        """Load .tausik/config.json."""
        import json

        config_path = os.path.join(os.path.dirname(self.be.db_path), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return dict(data) if isinstance(data, dict) else {}
        return {}

    def memory_show(self, mid: int) -> dict[str, Any]:
        row = self.be.memory_get(mid)
        if not row:
            raise ServiceError(f"Memory #{mid} not found")
        return row

    def memory_delete(self, mid: int) -> str:
        if not self.be.memory_get(mid):
            raise ServiceError(f"Memory #{mid} not found")
        self.be.memory_delete(mid)
        return f"Memory #{mid} deleted."

    def memory_archive(self, before: str, confirm: bool = False) -> dict[str, Any]:
        """Thin delegator — real logic lives in service_knowledge_hygiene."""
        from service_knowledge_hygiene import archive_memory

        return archive_memory(self.be, before, confirm)

    def memory_dedupe(self, threshold: float = 0.85, n: int = 200) -> list[dict[str, Any]]:
        """Thin delegator — real logic lives in service_knowledge_hygiene."""
        from service_knowledge_hygiene import dedupe_memory

        return dedupe_memory(self.be, threshold, n)

    def memory_lint(self, apply: bool = False, n: int = 500) -> dict[str, Any]:
        """Thin delegator — real logic lives in service_knowledge_hygiene."""
        from service_knowledge_hygiene import lint_memory

        return lint_memory(self.be, apply=apply, n=n)

    # --- Decisions ---

    def decide(self, text: str, task_slug: str | None = None, rationale: str | None = None) -> str:
        validate_length("decision", text)

        # Task-linked decisions are inherently project-specific — never route to brain.
        if task_slug is not None:
            did = self.be.decision_add(text, task_slug, rationale)
            return (
                f"Decision #{did} recorded — saved to local (reason: linked to task {task_slug})."
            )

        from brain_classifier import classify
        from brain_config import load_brain, validate_brain

        cfg = load_brain()
        decision = classify(text, "decision", cfg=cfg)

        if decision.target == "brain" and cfg.get("enabled"):
            # Defect v14b-defect-brain-decisions-empty: when brain.enabled=true
            # but database_ids/token are empty, store_record silently returns
            # status=config_error and the local-fallback path runs with a quiet
            # "brain write failed" reason. Pre-validate so the user sees a loud,
            # actionable message instead of accumulating local-only decisions
            # that should have been mirrored to Notion.
            cfg_errors = validate_brain()
            if cfg_errors:
                did = self.be.decision_add(text, task_slug, rationale)
                error_lines = "\n".join(f"  - {e}" for e in cfg_errors)
                return (
                    f"⚠ Decision #{did} saved LOCALLY ONLY — brain mirror BLOCKED.\n\n"
                    f"Brain is enabled in .tausik/config.json but misconfigured:\n"
                    f"{error_lines}\n\n"
                    f"Fix one of:\n"
                    f"  1. Run `.tausik/tausik brain init` to complete setup, OR\n"
                    f"  2. Set `brain.enabled = false` in .tausik/config.json to disable.\n\n"
                    f"After fixing, migrate local-only decisions with "
                    f"`tausik brain move --to-brain`."
                )
            from brain_runtime import try_brain_write_decision

            ok, detail = try_brain_write_decision(text, rationale, cfg)
            if ok:
                return (
                    f"Decision recorded — saved to brain "
                    f"(reason: {decision.reason}). Page: {detail}"
                )
            did = self.be.decision_add(text, task_slug, rationale)
            return (
                f"Decision #{did} recorded — saved to local (reason: brain write failed: {detail})."
            )

        did = self.be.decision_add(text, task_slug, rationale)
        reason = decision.reason if decision.target == "local" else "brain not enabled"
        return f"Decision #{did} recorded — saved to local (reason: {reason})."

    def decisions(self, n: int = 20) -> list[dict[str, Any]]:
        return self.be.decision_list(n)

    def memory_block(
        self,
        max_decisions: int = 5,
        max_conventions: int = 10,
        max_deadends: int = 5,
        max_lines: int = 50,
        max_contexts: int = 5,
    ) -> str:
        """Thin delegator — real logic lives in service_knowledge_aggregates."""
        from service_knowledge_aggregates import build_memory_block

        return build_memory_block(
            self.be, max_decisions, max_conventions, max_deadends, max_lines, max_contexts
        )

    def memory_compact(self, last_n: int = 50) -> str:
        """Thin delegator — real logic lives in service_knowledge_aggregates."""
        from service_knowledge_aggregates import build_memory_compact

        return build_memory_compact(self.be, last_n)

    # --- Dead Ends (SENAR Rule 9.4) ---

    def dead_end(
        self,
        approach: str,
        reason: str,
        tags: list[str] | None = None,
        task_slug: str | None = None,
    ) -> str:
        """Document a dead end -- failed approach with reason."""
        validate_content("approach", approach)
        validate_content("reason", reason)
        title = approach[:100]
        content = f"Approach: {approach}\nReason: {reason}"
        mid = self.be.memory_add("dead_end", title, content, tags, task_slug)
        # Suggest cq publish if configured
        cq_hint = ""
        try:
            from cq_client import get_cq_client

            config = self._load_config()
            if get_cq_client(config):
                cq_hint = " Consider sharing via tausik_cq_publish for other projects."
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            pass
        return f"Dead end #{mid} documented.{cq_hint}"

    # --- Graph Memory (Graphiti-inspired) ---

    def _validate_node(self, node_type: str, node_id: int) -> None:
        """Validate node exists."""
        if node_type not in VALID_NODE_TYPES:
            raise ServiceError(
                f"Invalid node type '{node_type}'. Valid: {', '.join(sorted(VALID_NODE_TYPES))}"
            )
        if node_type == "memory":
            if not self.be.memory_get(node_id):
                raise ServiceError(f"Memory #{node_id} not found")
        elif node_type == "decision":
            if not self.be.decision_get(node_id):
                raise ServiceError(f"Decision #{node_id} not found")

    def memory_link(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        relation: str,
        confidence: float = 1.0,
        created_by: str | None = None,
    ) -> str:
        """Create a graph edge between two memory/decision nodes."""
        if relation not in VALID_EDGE_RELATIONS:
            raise ServiceError(
                f"Invalid relation '{relation}'. Valid: {', '.join(sorted(VALID_EDGE_RELATIONS))}"
            )
        if confidence < 0.0 or confidence > 1.0:
            raise ServiceError("Confidence must be between 0.0 and 1.0")
        self._validate_node(source_type, source_id)
        self._validate_node(target_type, target_id)
        if source_type == target_type and source_id == target_id:
            raise ServiceError("Cannot link a node to itself")
        # For 'supersedes': auto-invalidate existing edges of the same relation on target
        if relation == "supersedes":
            existing = self.be.edge_list(
                node_type=target_type,
                node_id=target_id,
                relation="supersedes",
                include_invalid=False,
            )
            eid = self.be.edge_add(
                source_type,
                source_id,
                target_type,
                target_id,
                relation,
                confidence,
                created_by,
            )
            for old_edge in existing:
                if old_edge["source_type"] == target_type and old_edge["source_id"] == target_id:
                    self.be.edge_invalidate(old_edge["id"], eid)
        else:
            eid = self.be.edge_add(
                source_type,
                source_id,
                target_type,
                target_id,
                relation,
                confidence,
                created_by,
            )
        return f"Edge #{eid} created: {source_type}#{source_id} --[{relation}]--> {target_type}#{target_id}"

    def memory_unlink(self, edge_id: int, replacement_id: int | None = None) -> str:
        """Soft-invalidate an edge (never deletes -- Graphiti approach)."""
        edge = self.be.edge_get(edge_id)
        if not edge:
            raise ServiceError(f"Edge #{edge_id} not found")
        if edge["valid_to"] is not None:
            raise ServiceError(f"Edge #{edge_id} already invalidated")
        rows = self.be.edge_invalidate(edge_id, replacement_id)
        if rows == 0:
            raise ServiceError(f"Edge #{edge_id} could not be invalidated")
        return f"Edge #{edge_id} invalidated."

    def memory_related(
        self,
        node_type: str,
        node_id: int,
        max_hops: int = 2,
        include_invalid: bool = False,
    ) -> list[dict[str, Any]]:
        """Find related nodes via graph traversal."""
        self._validate_node(node_type, node_id)
        refs = self.be.graph_related(node_type, node_id, max_hops, include_invalid)
        return self.be.graph_resolve_nodes(refs)

    def memory_graph(
        self,
        node_type: str | None = None,
        node_id: int | None = None,
        relation: str | None = None,
        include_invalid: bool = False,
        n: int = 50,
    ) -> list[dict[str, Any]]:
        """List graph edges, optionally filtered."""
        if relation and relation not in VALID_EDGE_RELATIONS:
            raise ServiceError(
                f"Invalid relation '{relation}'. Valid: {', '.join(sorted(VALID_EDGE_RELATIONS))}"
            )
        return self.be.edge_list(node_type, node_id, relation, include_invalid, n)

    def memory_find_similar(self, title: str, content: str, n: int = 5) -> list[dict[str, Any]]:
        """Find similar memory entries (for auto-suggest on add). Uses FTS5."""
        query = f"{title} {content}"[:200]
        return self.be.memory_search(query, n)

    # --- Explorations (SENAR Section 5.1) ---

    def exploration_start(self, title: str, time_limit_min: int = 30) -> str:
        from service_knowledge_exploration import exploration_start

        return exploration_start(self.be, title, time_limit_min)

    def exploration_end(self, summary: str | None = None, create_task: bool = False) -> str:
        from service_knowledge_exploration import exploration_end

        return exploration_end(self.be, summary, create_task)

    def exploration_current(self) -> dict[str, Any] | None:
        from service_knowledge_exploration import exploration_current

        return exploration_current(self.be)

    # --- Events ---

    def events_list(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        n: int = 50,
    ) -> list[dict[str, Any]]:
        return self.be.events_list(entity_type, entity_id, n)
