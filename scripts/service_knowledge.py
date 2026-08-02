"""TAUSIK KnowledgeMixin -- memory, decisions, graph."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, cast

from tausik_utils import (
    ServiceError,
    validate_content,
    validate_length,
)
from project_types import VALID_EDGE_RELATIONS, VALID_MEMORY_TYPES, VALID_NODE_TYPES

# CQ_SOURCE + build_cq_row live in service_cq_row (filesize cap); re-exported here
# so `from service_knowledge import CQ_SOURCE, build_cq_row` keeps working.
from service_cq_row import CQ_SOURCE, build_cq_row  # noqa: F401


if TYPE_CHECKING:
    from project_backend import SQLiteBackend
    from project_service import ProjectService


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
        to_global: bool = False,
    ) -> str:
        if mem_type not in VALID_MEMORY_TYPES:
            raise ServiceError(
                f"Invalid memory type '{mem_type}'. Valid: {', '.join(sorted(VALID_MEMORY_TYPES))}"
            )
        from tausik_utils import safe_single_line

        validate_length("title", title)
        validate_content("content", content)
        title = safe_single_line(title) or title

        # Validation above is shared on purpose — a shared entry is held to the
        # same shape as a project one. Everything BELOW is project-specific and
        # is skipped rather than adapted: the projection writes into this
        # repository's tree, and the universality hint asks a question the flag
        # has already answered. `write_memory` raises rather than falling back,
        # so a failure here can never end up in the project database instead.
        if to_global:
            from knowledge_write import write_memory

            return write_memory(mem_type, title, content, tags, task_slug)

        mid = self.be.memory_add(mem_type, title, content, tags, task_slug)
        from brain_universality import emit_universality_hint

        emit_universality_hint(f"{title}\n{content}")
        from state_triggers import auto_export_by_id  # state-git-triggers (fail-open)

        # `self` is a KnowledgeMixin here but always a composed ProjectService at
        # runtime (the mixins only exist assembled) — cast the facade, don't widen
        # the helper's honest ProjectService signature.
        auto_export_by_id(cast("ProjectService", self), "memory", mid)
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
        """Search this project's memory, the shared store, and optionally cq.

        Order is deliberate: project hits first, then shared, then cq. Each
        later group is strictly less local than the one before it, and a reader
        scanning top-down meets the most specific answers first. Shared rows are
        addressless and labelled (`knowledge_read`), so they can never be
        mistaken for a row of THIS project's memory.

        A shared store that cannot be read records a warning for the renderer
        to surface — `knowledge_read.pop_last_warning`. It is kept there rather
        than returned here so that every existing caller of this method keeps
        working unchanged, and a renderer that forgets to ask simply prints no
        warning instead of printing a corrupt hit.
        """
        local = self.be.memory_search(query, include_archived=include_archived)

        from knowledge_read import search_shared_memory

        shared, _warning = search_shared_memory(query, limit=5)
        local.extend(shared)

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
                # Per-unit, not a generator under the outer except: a single
                # malformed unit used to abort the whole remaining batch
                # silently, dropping legitimate hits that followed it.
                for u in cq_results:
                    try:
                        local.append(build_cq_row(u))
                    except Exception:  # noqa: BLE001 — one bad unit must not cost the rest
                        continue
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
        row = self.be.memory_get(mid)
        if not row:
            raise ServiceError(f"Memory #{mid} not found")
        # Read the slug BEFORE the delete: the projection is keyed by slug, and
        # after the row is gone there is nothing left to derive it from. Skipping
        # this left a ghost file describing a row the DB no longer had.
        slug = row.get("slug")
        self.be.memory_delete(mid)
        if slug:
            from state_triggers import auto_export_entity  # fail-open

            auto_export_entity(cast("ProjectService", self), "memory", slug)
        return f"Memory #{mid} deleted."

    def memory_archive(self, before: str, confirm: bool = False) -> dict[str, Any]:
        """Thin delegator — real logic lives in service_knowledge_hygiene.

        The projection excludes archived memory, so an applied archive must REMOVE
        those files. `archive_memory` reports which rows it took (by id, read
        before the write — afterwards the candidate query no longer returns them).
        """
        from service_knowledge_hygiene import archive_memory

        result = archive_memory(self.be, before, confirm)
        if result.get("applied"):
            from state_triggers import auto_export_by_id  # fail-open

            for mid in result.get("archived_ids") or []:
                auto_export_by_id(cast("ProjectService", self), "memory", mid)
        return result

    def memory_dedupe(self, threshold: float = 0.85, n: int = 200) -> list[dict[str, Any]]:
        """Thin delegator — real logic lives in service_knowledge_hygiene."""
        from service_knowledge_hygiene import dedupe_memory

        return dedupe_memory(self.be, threshold, n)

    def memory_lint(self, apply: bool = False, n: int = 500) -> dict[str, Any]:
        """Thin delegator — real logic lives in service_knowledge_hygiene."""
        from service_knowledge_hygiene import lint_memory

        return lint_memory(self.be, apply=apply, n=n)

    # --- Decisions ---

    def decide(
        self,
        text: str,
        task_slug: str | None = None,
        rationale: str | None = None,
        to_global: bool = False,
    ) -> str:
        """Thin delegator — the two guarantees live in service_decide."""
        from service_decide import record

        return record(cast("ProjectService", self), text, task_slug, rationale, to_global)

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
        from state_triggers import auto_export_by_id  # fail-open

        auto_export_by_id(cast("ProjectService", self), "memory", mid)
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
            # 'supersedes' also invalidates edges where the TARGET is the source,
            # so that entity's `edges:` block changed too.
            self._export_node(target_type, target_id)
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
        self._export_node(source_type, source_id)
        return f"Edge #{eid} created: {source_type}#{source_id} --[{relation}]--> {target_type}#{target_id}"

    def _export_node(self, node_type: str, node_id: int) -> None:
        """Re-project the file of a graph node whose outgoing edges changed.

        `edges:` in a memory/decision file is a projection of the edges where that
        entity is the SOURCE, so an edge write changes the source's file — not the
        target's. Fail-open like every trigger.
        """
        kind = "memory" if node_type == "memory" else "decisions"
        from state_triggers import auto_export_by_id  # fail-open

        auto_export_by_id(cast("ProjectService", self), kind, node_id)

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
        self._export_node(edge["source_type"], edge["source_id"])
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
