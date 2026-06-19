"""TAUSIK AdaptsCrudMixin — RENAR ADAPT-artifact CRUD.

Extracted from backend_crud.py to keep it under the 400-line filesize cap
(v16r-adapt). Mixed into SQLiteBackend alongside BackendCrudMixin; relies on the
composed backend's ``_ins`` / ``_q`` / ``_q1`` / ``_ex`` helpers.

``category`` (findings) and ``role`` (signatures) are CLOSED lists enforced by
table CHECK constraints — an invalid value raises sqlite3.IntegrityError rather
than being stored.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import utcnow_iso


class AdaptsCrudMixin:
    """CRUD for RENAR ADAPT artifacts, their body parts, signatures and links."""

    # Type stubs for mixin -- actual methods provided by SQLiteBackend
    if TYPE_CHECKING:

        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...

    # --- header ---

    def adapt_add(
        self,
        slug: str,
        title: str,
        tz_ref: str,
        status: str = "draft",
        parent_adapt: str | None = None,
        delta_n: int = 0,
    ) -> int:
        """Insert an ADAPT header; returns the new row id.

        A duplicate ``slug`` raises IntegrityError on the UNIQUE index; an
        unknown ``parent_adapt`` raises IntegrityError on the self-FK.
        """
        now = utcnow_iso()
        return self._ins(
            "INSERT INTO adapts(slug, title, tz_ref, status, parent_adapt, "
            "delta_n, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (slug, title, tz_ref, status, parent_adapt, delta_n, now, now),
        )

    def adapt_get(self, slug: str) -> dict[str, Any] | None:
        """Return an ADAPT header row by slug, or None."""
        return self._q1("SELECT * FROM adapts WHERE slug=?", (slug,))

    def adapt_list(self, status: str | None = None) -> list[dict[str, Any]]:
        """List ADAPTs, optionally filtered by status, newest first."""
        if status:
            return self._q(
                "SELECT * FROM adapts WHERE status=? ORDER BY created_at DESC, id DESC",
                (status,),
            )
        return self._q("SELECT * FROM adapts ORDER BY created_at DESC, id DESC")

    def adapt_set_status(self, slug: str, status: str) -> int:
        """Set ADAPT status (draft|signed|superseded); returns affected rows."""
        return self._ex(
            "UPDATE adapts SET status=?, updated_at=? WHERE slug=?",
            (status, utcnow_iso(), slug),
        )

    def adapt_delete(self, slug: str) -> int:
        """Delete an ADAPT; child rows cascade (interpretations/findings/sigs/links)."""
        return self._ex("DELETE FROM adapts WHERE slug=?", (slug,))

    # --- forward interpretation (§7.4.3) ---

    def interp_add(
        self,
        adapt_slug: str,
        tz_ref: str,
        citation: str,
        engineering_interpretation: str,
        scope_in: str,
        scope_out: str,
        term_mapping: str | None = None,
        scenarios: str | None = None,
    ) -> int:
        """Insert a forward-interpretation entry; returns the new row id."""
        return self._ins(
            "INSERT INTO adapt_interpretations(adapt_slug, tz_ref, citation, "
            "engineering_interpretation, term_mapping, scenarios, scope_in, "
            "scope_out, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                adapt_slug,
                tz_ref,
                citation,
                engineering_interpretation,
                term_mapping,
                scenarios,
                scope_in,
                scope_out,
                utcnow_iso(),
            ),
        )

    def interps_for_adapt(self, adapt_slug: str) -> list[dict[str, Any]]:
        """Forward-interpretation entries for an ADAPT, insertion order."""
        return self._q(
            "SELECT * FROM adapt_interpretations WHERE adapt_slug=? ORDER BY id",
            (adapt_slug,),
        )

    # --- backward findings (closed-7 §7) ---

    def finding_add(
        self,
        adapt_slug: str,
        category: str,
        description: str,
        tz_ref: str | None = None,
        resolution: str | None = None,
    ) -> int:
        """Insert a backward finding; ``category`` enforced as closed-7 by CHECK."""
        return self._ins(
            "INSERT INTO adapt_findings(adapt_slug, category, description, tz_ref, "
            "resolution, created_at) VALUES(?,?,?,?,?,?)",
            (adapt_slug, category, description, tz_ref, resolution, utcnow_iso()),
        )

    def findings_for_adapt(self, adapt_slug: str) -> list[dict[str, Any]]:
        """Backward findings for an ADAPT, insertion order."""
        return self._q(
            "SELECT * FROM adapt_findings WHERE adapt_slug=? ORDER BY id",
            (adapt_slug,),
        )

    # --- dual signature (§7.5) ---

    def signature_set(
        self,
        adapt_slug: str,
        role: str,
        signed_by: str,
        signed_at: str,
        key_fingerprint: str | None = None,
        signature: str | None = None,
    ) -> None:
        """Upsert a signature for (adapt, role). ``role`` enforced by CHECK.

        A re-sign overwrites the prior signature for that role (idempotent
        identity = adapt_slug + role).
        """
        self._ex(
            "INSERT INTO adapt_signatures(adapt_slug, role, signed_by, signed_at, "
            "key_fingerprint, signature) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(adapt_slug, role) DO UPDATE SET "
            "signed_by=excluded.signed_by, signed_at=excluded.signed_at, "
            "key_fingerprint=excluded.key_fingerprint, signature=excluded.signature",
            (adapt_slug, role, signed_by, signed_at, key_fingerprint, signature),
        )

    def signatures_for_adapt(self, adapt_slug: str) -> list[dict[str, Any]]:
        """Signatures for an ADAPT (0..2 rows, one per role)."""
        return self._q(
            "SELECT * FROM adapt_signatures WHERE adapt_slug=? ORDER BY role",
            (adapt_slug,),
        )

    # --- links (adapt ↔ task/spec) ---

    def adapt_link(self, adapt_slug: str, target_type: str, target_slug: str) -> int:
        """Link an ADAPT to a task or spec; returns the link rowid.

        ``target_type`` is a closed list ('task'|'spec') enforced by CHECK; the
        PRIMARY KEY makes a duplicate link raise IntegrityError.
        """
        return self._ins(
            "INSERT INTO adapt_links(adapt_slug, target_type, target_slug, created_at) "
            "VALUES(?,?,?,?)",
            (adapt_slug, target_type, target_slug, utcnow_iso()),
        )

    def adapt_unlink(self, adapt_slug: str, target_type: str, target_slug: str) -> int:
        """Remove an ADAPT↔target link; returns affected row count."""
        return self._ex(
            "DELETE FROM adapt_links WHERE adapt_slug=? AND target_type=? AND target_slug=?",
            (adapt_slug, target_type, target_slug),
        )

    def links_for_adapt(self, adapt_slug: str) -> list[dict[str, Any]]:
        """All targets (task/spec) linked to an ADAPT, newest link first."""
        return self._q(
            "SELECT target_type, target_slug, created_at FROM adapt_links "
            "WHERE adapt_slug=? ORDER BY created_at DESC",
            (adapt_slug,),
        )

    def adapts_for_target(self, target_type: str, target_slug: str) -> list[dict[str, Any]]:
        """ADAPTs linked to a given task/spec, with header fields, newest first."""
        return self._q(
            "SELECT a.slug, a.title, a.tz_ref, a.status "
            "FROM adapt_links l JOIN adapts a ON a.slug = l.adapt_slug "
            "WHERE l.target_type=? AND l.target_slug=? ORDER BY l.created_at DESC",
            (target_type, target_slug),
        )

    def adapt_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """FTS5 search over ADAPT slug/title/tz_ref, ranked by bm25."""
        return self._q(
            "SELECT a.*, snippet(fts_adapts, 1, '>>>', '<<<', '...', 32) AS _snippet "
            "FROM adapts a JOIN fts_adapts f ON a.id=f.rowid "
            "WHERE fts_adapts MATCH ? ORDER BY bm25(fts_adapts, 5.0, 10.0, 2.0) LIMIT ?",
            (query, limit),
        )
