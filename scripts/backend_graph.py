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
        def _q(
            self, sql: str, params: tuple[Any, ...] = ()
        ) -> list[dict[str, Any]]: ...
        def _q1(
            self, sql: str, params: tuple[Any, ...] = ()
        ) -> dict[str, Any] | None: ...

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
