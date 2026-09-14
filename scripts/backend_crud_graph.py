"""CRUD for the artifact graph. Mixed into SQLiteBackend.

Nothing here decides WHAT an edge means -- that is the builders' business. This
layer only refuses to store an edge that cannot say where it came from, and the
refusal is the schema's (`layer` NOT NULL with a closed list), not a check
written twice.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

from tausik_utils import utcnow_iso


class GraphCrudMixin:
    """Artifacts, their symbols, and the edges between them."""

    if TYPE_CHECKING:

        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...

    # --- artifacts ---

    def artifact_upsert(self, path: str, kind: str, content_hash: str) -> int:
        """Record an artifact at its CURRENT fingerprint, returning its id.

        Re-indexing an unchanged file rewrites the same hash and moves
        `indexed_at`; re-indexing a changed one replaces the fingerprint. Either
        way the row afterwards describes what was on disk at index time, which
        is what staleness is later measured against.
        """
        self._ex(
            "INSERT INTO artifacts(path, kind, content_hash, indexed_at) VALUES(?,?,?,?) "
            "ON CONFLICT(path) DO UPDATE SET kind=excluded.kind, "
            "content_hash=excluded.content_hash, indexed_at=excluded.indexed_at",
            (path, kind, content_hash, utcnow_iso()),
        )
        row = self._q1("SELECT id FROM artifacts WHERE path = ?", (path,))
        return int(row["id"]) if row else 0

    def artifact_get(self, path: str) -> dict[str, Any] | None:
        return self._q1(
            "SELECT id, path, kind, content_hash, indexed_at FROM artifacts WHERE path = ?",
            (path,),
        )

    def artifact_list(self, kind: str | None = None) -> list[dict[str, Any]]:
        if kind:
            return self._q(
                "SELECT id, path, kind, content_hash, indexed_at FROM artifacts "
                "WHERE kind = ? ORDER BY path",
                (kind,),
            )
        return self._q(
            "SELECT id, path, kind, content_hash, indexed_at FROM artifacts ORDER BY path"
        )

    # --- symbols ---

    def artifact_symbol_add(self, artifact_id: int, name: str, line: int | None = None) -> int:
        return self._ins(
            "INSERT OR IGNORE INTO artifact_symbols(artifact_id, name, line) VALUES(?,?,?)",
            (artifact_id, name, line),
        )

    def symbols_for_artifact(self, artifact_id: int) -> list[dict[str, Any]]:
        return self._q(
            "SELECT id, name, line FROM artifact_symbols WHERE artifact_id = ? ORDER BY name",
            (artifact_id,),
        )

    # --- edges ---

    def artifact_edge_add(
        self,
        source_id: int,
        target_id: int,
        relation: str,
        layer: str,
        confidence: float,
        *,
        observations: int = 1,
        source_ref: str | None = None,
    ) -> int:
        """Store one edge. Re-observing the same (pair, relation, LAYER) updates
        its strength rather than adding a duplicate.

        The layer is part of the identity on purpose: the same two files may be
        both co-changed AND declared, and those are two claims, not one seen
        twice. Collapsing them would erase the distinction the graph exists for.
        """
        self._ex(
            "INSERT INTO artifact_edges(source_artifact_id, target_artifact_id, relation, "
            "layer, confidence, observations, source_ref, created_at) VALUES(?,?,?,?,?,?,?,?) "
            "ON CONFLICT(source_artifact_id, target_artifact_id, relation, layer) DO UPDATE SET "
            "confidence=excluded.confidence, observations=excluded.observations, "
            "source_ref=COALESCE(excluded.source_ref, artifact_edges.source_ref)",
            (
                source_id,
                target_id,
                relation,
                layer,
                confidence,
                observations,
                source_ref,
                utcnow_iso(),
            ),
        )
        row = self._q1(
            "SELECT id FROM artifact_edges WHERE source_artifact_id=? AND target_artifact_id=? "
            "AND relation=? AND layer=?",
            (source_id, target_id, relation, layer),
        )
        return int(row["id"]) if row else 0

    def edges_from_artifact(self, artifact_id: int) -> list[dict[str, Any]]:
        """Edges LEAVING an artifact, each carrying the layer that produced it."""
        return self._q(
            "SELECT e.id, e.relation, e.layer, e.confidence, e.observations, e.source_ref, "
            "a.path AS target_path, a.content_hash AS target_hash, a.id AS target_id "
            "FROM artifact_edges e JOIN artifacts a ON a.id = e.target_artifact_id "
            "WHERE e.source_artifact_id = ? "
            "ORDER BY e.confidence DESC, a.path",
            (artifact_id,),
        )

    def edges_touching_artifact(self, artifact_id: int) -> list[dict[str, Any]]:
        """Edges on EITHER side of an artifact, with the other end as the target.

        Direction is a storage detail for the symmetric relations. Co-change is
        stored once, on the alphabetically first path, so asking `edges_from`
        about the second one answered "nothing" for a file that co-changes with
        half the tree — measured on this repository, where the busiest module
        came back with zero neighbours. A caller asking "what relates to this"
        means both directions, and only the storage ever cared which column a
        row landed in.

        `direction` is still reported, because for `covers` or `documents` the
        arrow carries meaning the caller may need.
        """
        return self._q(
            "SELECT e.id, e.relation, e.layer, e.confidence, e.observations, e.source_ref, "
            "'out' AS direction, "
            "a.path AS target_path, a.content_hash AS target_hash, a.id AS target_id "
            "FROM artifact_edges e JOIN artifacts a ON a.id = e.target_artifact_id "
            "WHERE e.source_artifact_id = ? "
            "UNION ALL "
            "SELECT e.id, e.relation, e.layer, e.confidence, e.observations, e.source_ref, "
            "'in' AS direction, "
            "a.path AS target_path, a.content_hash AS target_hash, a.id AS target_id "
            "FROM artifact_edges e JOIN artifacts a ON a.id = e.source_artifact_id "
            "WHERE e.target_artifact_id = ? "
            "ORDER BY confidence DESC, target_path",
            (artifact_id, artifact_id),
        )

    def graph_counts(self) -> dict[str, int]:
        """How much the graph actually holds, per table.

        Exists because "the graph is empty" and "the graph is fine" were
        indistinguishable from outside: for a day after the substrate shipped,
        all three tables held zero rows in the repository that authored them and
        nothing said so. A count is the cheapest way for that to be visible.
        """
        out: dict[str, int] = {}
        # Per-layer edge counts live here rather than in a method of their own:
        # `edge_count_by_layer` existed with no caller anywhere in the tree, and
        # a second entry point for the same question would have grown the public
        # surface the class-surface ratchet guards without answering anything new.
        try:
            for row in self._q("SELECT layer, COUNT(*) AS n FROM artifact_edges GROUP BY layer"):
                out[f"edges:{row['layer']}"] = int(row["n"])
        except sqlite3.Error:
            pass  # absence, reported below as -1 rather than raised here
        for key, table in (
            ("artifacts", "artifacts"),
            ("symbols", "artifact_symbols"),
            ("edges", "artifact_edges"),
        ):
            try:
                # A name of its own: the loop above binds `row` from `_q`, which
                # always yields a dict, while `_q1` may yield None. Reusing the
                # name made one variable hold two types.
                count_row = self._q1(f"SELECT COUNT(*) AS n FROM {table}")
                out[key] = int(count_row["n"]) if count_row else 0
            except sqlite3.Error:
                # A table that cannot be read reports absence, not zero: those
                # are different facts and only one of them is about the graph.
                out[key] = -1
        return out

    def graph_clear(self) -> int:
        """Drop every artifact (edges and symbols cascade), returning how many.

        Returns the count rather than None so a rebuild can say what it threw
        away. A destructive step that reports nothing gives the operator no way
        to notice it destroyed more than intended.
        """
        try:
            before = self.graph_counts().get("artifacts", 0)
            self._ex("DELETE FROM artifacts")
            return max(before, 0)
        except sqlite3.Error:
            return 0
