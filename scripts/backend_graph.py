"""TAUSIK BackendGraphMixin -- graph memory (memory_edges) + explorations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import utcnow_iso


class BackendGraphMixin:
    """Graph memory edges and exploration lifecycle. Mixed into SQLiteBackend."""

    # Type stubs for mixin -- actual methods provided by SQLiteBackend
    if TYPE_CHECKING:

        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...
        def _project_write(self, table: str, slug: str) -> None: ...

    # --- graph memory (memory_edges) ---

    def edge_add(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        relation: str,
        confidence: float = 1.0,
        created_by: str | None = None,
    ) -> int:
        """Add a graph edge between two memory/decision nodes."""
        now = utcnow_iso()
        return self._ins(
            "INSERT INTO memory_edges(source_type,source_id,target_type,target_id,"
            "relation,confidence,created_by,valid_from,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (
                source_type,
                source_id,
                target_type,
                target_id,
                relation,
                confidence,
                created_by,
                now,
                now,
            ),
        )

    def edge_invalidate(self, edge_id: int, replacement_id: int | None = None) -> int:
        """Soft-invalidate an edge (Graphiti approach: never delete)."""
        return self._ex(
            "UPDATE memory_edges SET valid_to=?, invalidated_by=? WHERE id=? AND valid_to IS NULL",
            (utcnow_iso(), replacement_id, edge_id),
        )

    def memory_archive_ids(self, ids: list[int]) -> int:
        """Stamp ``archived_at`` on the given memory ids (idempotent).

        Used by ``memory lint --apply`` to archive superseded entries.
        Already-archived rows are skipped. Returns rows newly archived.
        """
        if not ids:
            return 0
        now = utcnow_iso()
        placeholders = ",".join("?" for _ in ids)
        archived = self._ex(
            f"UPDATE memory SET archived_at=?, updated_at=? "
            f"WHERE id IN ({placeholders}) AND archived_at IS NULL",
            (now, now, *ids),
        )
        # The departure is HERE, so the edges end here. Left alive they make the orphan
        # sweep re-serialize the same sources on every future departure, forever.
        if archived:
            self._edges_invalidate_to("memory", ids)
        return archived

    def _end_edges_for_departure(self, table: str, row_id: int) -> int:
        """End the edges pointing at a row that is about to be deleted.

        Takes the TABLE name because the caller is the generic delete path and holds one;
        the kind mapping lives here so that path stays a single line — it sits at its own
        500-line ceiling, and a mapping is not worth displacing a rule.
        """
        kinds = {"memory": "memory", "decisions": "decision"}
        return self._edges_invalidate_to(kinds[table], [int(row_id)]) if table in kinds else 0

    def _edges_invalidate_to(self, kind: str, ids: list[int]) -> int:
        """Soft-invalidate live edges whose TARGET is leaving. Returns rows stamped.

        THE CONVERGENCE FIX. The orphan sweep in `state_triggers` asks the data "which
        live edges point outside the projection" and re-serializes their SOURCES — which
        never touches `memory_edges`, so the predicate never clears. MEASURED before this
        existed, on 2000 memory rows with 40 orphans: three consecutive sweeps returned
        40, 0, 0 while each re-serialized 40 files and left 40 orphans behind. Forty
        serializations that changed nothing, on every departure, forever.

        SOFT, not a DELETE: the row stays with `valid_to` stamped. The graph is a record
        of what was linked, and a link that existed and ended is a different fact from a
        link that never was — `edge_get` can still answer about it, and the history the
        `--at` queries read stays whole.

        IRREVERSIBLE BY CONSTRUCTION, and that is safe only because nothing un-archives:
        the project has no `memory_unarchive` and no path that clears `archived_at`. If
        one is ever added, it has to decide what happens to edges stamped here — it
        cannot simply clear `archived_at` and expect the graph to come back.

        Called at every DEPARTURE rather than from the projection trigger: the trigger is
        fail-open and downstream of the write, so a database mutation there would be a
        write from something whose contract is to never raise.
        """
        if not ids or kind not in ("memory", "decision"):
            return 0
        clean = [int(i) for i in ids]
        placeholders = ",".join("?" for _ in clean)
        # SOURCES FIRST, because after the stamp the predicate no longer selects them and
        # there is nothing left to re-project. Their files spell the edge out, so a stamp
        # without a re-projection leaves the tree claiming a live link the DB has ended —
        # which is the divergence the projection hook exists to remove, sign flipped. The
        # orphan sweep used to cover this by accident; it no longer finds these rows.
        sources = self._q(
            "SELECT DISTINCT source_type, source_id FROM memory_edges "
            f"WHERE valid_to IS NULL AND target_type=? AND target_id IN ({placeholders})",
            (kind, *clean),
        )
        stamped = self._ex(
            "UPDATE memory_edges SET valid_to=? "
            f"WHERE valid_to IS NULL AND target_type=? AND target_id IN ({placeholders})",
            (utcnow_iso(), kind, *clean),
        )
        for row in sources if stamped else []:
            table = "memory" if row["source_type"] == "memory" else "decisions"
            slug = (
                self._q1(
                    f"SELECT slug FROM {table} WHERE id=?",  # ruff-not-enabled: S608
                    (int(row["source_id"]),),
                )
                or {}
            ).get("slug")
            if slug:
                self._project_write(table, str(slug))
        return stamped

    def edge_get(self, edge_id: int) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM memory_edges WHERE id=?", (edge_id,))

    def edge_list(
        self,
        node_type: str | None = None,
        node_id: int | None = None,
        relation: str | None = None,
        include_invalid: bool = False,
        n: int = 50,
    ) -> list[dict[str, Any]]:
        """List edges, optionally filtered by node or relation."""
        sql = "SELECT * FROM memory_edges WHERE 1=1"
        params: list[Any] = []
        if not include_invalid:
            sql += " AND valid_to IS NULL"
        if node_type and node_id is not None:
            sql += " AND ((source_type=? AND source_id=?) OR (target_type=? AND target_id=?))"
            params.extend([node_type, node_id, node_type, node_id])
        if relation:
            sql += " AND relation=?"
            params.append(relation)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(n)
        return self._q(sql, tuple(params))

    def edge_list_for_node(
        self, node_type: str, node_id: int, include_invalid: bool = False
    ) -> list[dict[str, Any]]:
        """All edges connected to a specific node."""
        sql = (
            "SELECT * FROM memory_edges WHERE "
            "((source_type=? AND source_id=?) OR (target_type=? AND target_id=?))"
        )
        params: list[Any] = [node_type, node_id, node_type, node_id]
        if not include_invalid:
            sql += " AND valid_to IS NULL"
        sql += " ORDER BY created_at DESC"
        return self._q(sql, tuple(params))

    # --- explorations ---

    def exploration_start(self, title: str, time_limit_min: int = 30) -> int:
        now = utcnow_iso()
        return self._ins(
            "INSERT INTO explorations(title,time_limit_min,started_at,created_at) VALUES(?,?,?,?)",
            (title, time_limit_min, now, now),
        )

    def exploration_current(self) -> dict[str, Any] | None:
        return self._q1(
            "SELECT * FROM explorations WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1",
        )

    def exploration_end(
        self, eid: int, summary: str | None = None, task_slug: str | None = None
    ) -> None:
        self._ex(
            "UPDATE explorations SET ended_at=?, summary=?, task_slug=? WHERE id=?",
            (utcnow_iso(), summary, task_slug, eid),
        )
