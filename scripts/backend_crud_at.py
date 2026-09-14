"""TAUSIK AtCrudMixin -- RENAR AT (Acceptance Test) artifact CRUD.

Mixed into SQLiteBackend alongside ActzCrudMixin. Mirrors that module's shape
(header CRUD, FTS5 search) -- see backend_schema_at for what AT actually is
and why isolation/freshness live outside this layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import utcnow_iso


class AtCrudMixin:
    """CRUD for RENAR AT (Acceptance Test) artifacts."""

    if TYPE_CHECKING:

        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...

    def at_add(
        self,
        slug: str,
        tz_ref: str,
        tz_text: str,
        scenario: str,
        source_as_of: str,
        generated_by: str,
    ) -> int:
        """Insert an AT record; returns the new row id."""
        return self._ins(
            "INSERT INTO ats(slug, tz_ref, tz_text, scenario, source_as_of, "
            "generated_by, created_at) VALUES(?,?,?,?,?,?,?)",
            (slug, tz_ref, tz_text, scenario, source_as_of, generated_by, utcnow_iso()),
        )

    def at_get(self, slug: str) -> dict[str, Any] | None:
        """Return an AT row by slug, or None."""
        return self._q1("SELECT * FROM ats WHERE slug=?", (slug,))

    def at_list(self, tz_ref: str | None = None) -> list[dict[str, Any]]:
        """List AT records, optionally filtered by tz_ref, newest first."""
        if tz_ref:
            return self._q(
                "SELECT * FROM ats WHERE tz_ref=? ORDER BY created_at DESC, id DESC",
                (tz_ref,),
            )
        return self._q("SELECT * FROM ats ORDER BY created_at DESC, id DESC")

    def at_delete(self, slug: str) -> int:
        """Delete an AT record; returns affected row count."""
        return self._ex("DELETE FROM ats WHERE slug=?", (slug,))

    def at_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """FTS5 search over AT slug/tz_ref/tz_text/scenario, ranked by bm25."""
        return self._q(
            "SELECT a.*, snippet(fts_ats, 2, '>>>', '<<<', '...', 32) AS _snippet "
            "FROM ats a JOIN fts_ats f ON a.id=f.rowid "
            "WHERE fts_ats MATCH ? ORDER BY bm25(fts_ats, 5.0, 3.0, 10.0, 2.0) LIMIT ?",
            (query, limit),
        )

    # --- results (append-only outcome history, like verification_runs) ---

    def at_result_add(self, at_slug: str, outcome: str, note: str | None) -> int:
        """Record one observed trial outcome; returns the new row id."""
        return self._ins(
            "INSERT INTO at_results(at_slug, outcome, note, recorded_at) VALUES(?,?,?,?)",
            (at_slug, outcome, note, utcnow_iso()),
        )

    def at_results_for(self, at_slug: str) -> list[dict[str, Any]]:
        """All recorded trials for an AT, newest first."""
        return self._q(
            "SELECT * FROM at_results WHERE at_slug=? ORDER BY recorded_at DESC, id DESC",
            (at_slug,),
        )

    def at_latest_outcome(self, at_slug: str) -> dict[str, Any] | None:
        """The most recent trial for an AT, or None if never exercised."""
        return self._q1(
            "SELECT * FROM at_results WHERE at_slug=? ORDER BY recorded_at DESC, id DESC LIMIT 1",
            (at_slug,),
        )
