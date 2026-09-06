"""TAUSIK ActzCrudMixin -- RENAR ACTZ-artifact CRUD.

Mixed into SQLiteBackend alongside AdaptsCrudMixin; relies on the composed
backend's ``_ins`` / ``_q`` / ``_q1`` / ``_ex`` helpers. Mirrors
``backend_crud_adapts.AdaptsCrudMixin`` in shape; see that module and
``backend_schema_actz`` for what differs and why (points instead of
interpretations/findings, ``decided_in`` instead of a bare link).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import utcnow_iso


class ActzCrudMixin:
    """CRUD for RENAR ACTZ artifacts, their points, signatures and links."""

    if TYPE_CHECKING:

        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...

    # --- header ---

    def actz_add(
        self,
        slug: str,
        title: str,
        tz_ref: str,
        status: str = "draft",
        parent_actz: str | None = None,
        delta_n: int = 0,
    ) -> int:
        """Insert an ACTZ header; returns the new row id."""
        now = utcnow_iso()
        return self._ins(
            "INSERT INTO actz(slug, title, tz_ref, status, parent_actz, "
            "delta_n, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (slug, title, tz_ref, status, parent_actz, delta_n, now, now),
        )

    def actz_get(self, slug: str) -> dict[str, Any] | None:
        """Return an ACTZ header row by slug, or None."""
        return self._q1("SELECT * FROM actz WHERE slug=?", (slug,))

    def actz_list(self, status: str | None = None) -> list[dict[str, Any]]:
        """List ACTZ headers, optionally filtered by status, newest first."""
        if status:
            return self._q(
                "SELECT * FROM actz WHERE status=? ORDER BY created_at DESC, id DESC",
                (status,),
            )
        return self._q("SELECT * FROM actz ORDER BY created_at DESC, id DESC")

    def actz_set_status(
        self, slug: str, status: str, supersession_rationale: str | None = None
    ) -> int:
        """Set ACTZ status; returns affected rows.

        Superseding requires a rationale, the same rule ``adapt_set_status``
        enforces for ADAPT and at the same layer -- the lowest primitive that
        writes the column.
        """
        if status == "superseded" and not (supersession_rationale or "").strip():
            raise ValueError(
                "Superseding an ACTZ requires supersession_rationale: a "
                "supersession that cannot cite a reason is an empty record."
            )
        return self._ex(
            "UPDATE actz SET status=?, "
            "supersession_rationale=COALESCE(?, supersession_rationale), "
            "updated_at=? WHERE slug=?",
            (status, supersession_rationale, utcnow_iso(), slug),
        )

    def actz_delete(self, slug: str) -> int:
        """Delete an ACTZ; child rows cascade (points/signatures/links/decided_in)."""
        return self._ex("DELETE FROM actz WHERE slug=?", (slug,))

    # --- points (numbered clauses of the protocol) ---

    def actz_point_add(self, actz_slug: str, point_no: int, tz_ref: str, text: str) -> int:
        """Insert a numbered point; UNIQUE(actz_slug, point_no) rejects a duplicate number.

        ``tz_ref`` (v53) names which clause of the original ТЗ (or a prior
        ACTZ point) this point clarifies -- final_tz_snapshot groups by it.
        """
        return self._ins(
            "INSERT INTO actz_points(actz_slug, point_no, tz_ref, text, created_at) "
            "VALUES(?,?,?,?,?)",
            (actz_slug, point_no, tz_ref, text, utcnow_iso()),
        )

    def points_for_actz(self, actz_slug: str) -> list[dict[str, Any]]:
        """Points of an ACTZ, in point_no order."""
        return self._q(
            "SELECT * FROM actz_points WHERE actz_slug=? ORDER BY point_no",
            (actz_slug,),
        )

    def actz_point_get(self, actz_slug: str, point_no: int) -> dict[str, Any] | None:
        """One point by (actz_slug, point_no), or None."""
        return self._q1(
            "SELECT * FROM actz_points WHERE actz_slug=? AND point_no=?",
            (actz_slug, point_no),
        )

    # --- signatures (Sec5.5.3: architect ed25519 + client name/timestamp) ---

    def actz_signature_set(
        self,
        actz_slug: str,
        role: str,
        signed_by: str,
        signed_at: str,
        key_fingerprint: str | None = None,
        signature: str | None = None,
    ) -> None:
        """Upsert a signature for (actz, role). A re-sign overwrites the prior row."""
        self._ex(
            "INSERT INTO actz_signatures(actz_slug, role, signed_by, signed_at, "
            "key_fingerprint, signature) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(actz_slug, role) DO UPDATE SET "
            "signed_by=excluded.signed_by, signed_at=excluded.signed_at, "
            "key_fingerprint=excluded.key_fingerprint, signature=excluded.signature",
            (actz_slug, role, signed_by, signed_at, key_fingerprint, signature),
        )

    def signatures_for_actz(self, actz_slug: str) -> list[dict[str, Any]]:
        """Signatures for an ACTZ (0..2 rows, one per role)."""
        return self._q(
            "SELECT * FROM actz_signatures WHERE actz_slug=? ORDER BY role",
            (actz_slug,),
        )

    # --- links (actz <-> task/spec, 0..N per ТЗ/SPEC) ---

    def actz_link(self, actz_slug: str, target_type: str, target_slug: str) -> int:
        """Link an ACTZ to a task or spec; returns the link rowid."""
        return self._ins(
            "INSERT INTO actz_links(actz_slug, target_type, target_slug, created_at) "
            "VALUES(?,?,?,?)",
            (actz_slug, target_type, target_slug, utcnow_iso()),
        )

    def actz_unlink(self, actz_slug: str, target_type: str, target_slug: str) -> int:
        """Remove an ACTZ<->target link; returns affected row count."""
        return self._ex(
            "DELETE FROM actz_links WHERE actz_slug=? AND target_type=? AND target_slug=?",
            (actz_slug, target_type, target_slug),
        )

    def links_for_actz(self, actz_slug: str) -> list[dict[str, Any]]:
        """All targets (task/spec) linked to an ACTZ, newest link first."""
        return self._q(
            "SELECT target_type, target_slug, created_at FROM actz_links "
            "WHERE actz_slug=? ORDER BY created_at DESC",
            (actz_slug,),
        )

    def actzs_for_target(self, target_type: str, target_slug: str) -> list[dict[str, Any]]:
        """ACTZ headers linked to a given task/spec, newest first."""
        return self._q(
            "SELECT a.slug, a.title, a.tz_ref, a.status "
            "FROM actz_links l JOIN actz a ON a.slug = l.actz_slug "
            "WHERE l.target_type=? AND l.target_slug=? ORDER BY l.created_at DESC",
            (target_type, target_slug),
        )

    # --- decided-in (ADAPT backward finding -> signed ACTZ point, WITH provenance) ---

    def decided_in_add(
        self,
        adapt_slug: str,
        finding_id: int,
        actz_slug: str,
        actz_point_no: int,
        linked_by: str,
    ) -> int:
        """Record that an ADAPT finding was decided-in an ACTZ point.

        ``linked_by`` is the provenance ``adapt_links`` never carried (§ see
        backend_schema_actz docstring) -- who recorded the edge, not just when.
        """
        return self._ins(
            "INSERT INTO actz_decided_in(adapt_slug, finding_id, actz_slug, "
            "actz_point_no, linked_by, created_at) VALUES(?,?,?,?,?,?)",
            (adapt_slug, finding_id, actz_slug, actz_point_no, linked_by, utcnow_iso()),
        )

    def decided_in_remove(
        self, adapt_slug: str, finding_id: int, actz_slug: str, actz_point_no: int
    ) -> int:
        """Remove a decided-in edge; returns affected row count."""
        return self._ex(
            "DELETE FROM actz_decided_in WHERE adapt_slug=? AND finding_id=? "
            "AND actz_slug=? AND actz_point_no=?",
            (adapt_slug, finding_id, actz_slug, actz_point_no),
        )

    def decided_in_for_finding(self, adapt_slug: str, finding_id: int) -> list[dict[str, Any]]:
        """ACTZ points a given ADAPT finding was decided-in."""
        return self._q(
            "SELECT * FROM actz_decided_in WHERE adapt_slug=? AND finding_id=? ORDER BY created_at",
            (adapt_slug, finding_id),
        )

    def decided_in_for_point(self, actz_slug: str, actz_point_no: int) -> list[dict[str, Any]]:
        """ADAPT findings decided-in a given ACTZ point (1..N per RENAR cardinality)."""
        return self._q(
            "SELECT * FROM actz_decided_in WHERE actz_slug=? AND actz_point_no=? "
            "ORDER BY created_at",
            (actz_slug, actz_point_no),
        )

    # --- final-TZ (RENAR §5A.4): derived from both-role-signed points ---

    def actz_points_with_completion(self) -> list[dict[str, Any]]:
        """Points of every ACTZ that reached BOTH-role signature coverage, each
        with its completion time (MAX(signed_at) across its two signature rows).

        Includes SUPERSEDED headers too, on purpose: a document once fully
        signed remains the governing text for any `as_of` before whatever
        later superseded it -- current header status alone cannot answer "what
        governed at time T", only "what governs now".
        """
        return self._q(
            "SELECT p.actz_slug, p.point_no, p.tz_ref, p.text, "
            "(SELECT MAX(s.signed_at) FROM actz_signatures s "
            " WHERE s.actz_slug = p.actz_slug) AS completed_at "
            "FROM actz_points p "
            "WHERE (SELECT COUNT(DISTINCT s.role) FROM actz_signatures s "
            "       WHERE s.actz_slug = p.actz_slug) = 2 "
            "ORDER BY p.tz_ref, completed_at"
        )

    def orphan_signed_points(self) -> list[dict[str, Any]]:
        """Points of a both-role-signed ACTZ with no actz_decided_in edge
        referencing them -- a signed decision not reflected in any ADAPT
        (§5A.4: an obligation outside requirements)."""
        return self._q(
            "SELECT p.actz_slug, p.point_no, p.tz_ref, p.text FROM actz_points p "
            "WHERE (SELECT COUNT(DISTINCT s.role) FROM actz_signatures s "
            "       WHERE s.actz_slug = p.actz_slug) = 2 "
            "AND NOT EXISTS (SELECT 1 FROM actz_decided_in d "
            "                WHERE d.actz_slug = p.actz_slug AND d.actz_point_no = p.point_no) "
            "ORDER BY p.actz_slug, p.point_no"
        )

    def actz_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """FTS5 search over ACTZ slug/title/tz_ref, ranked by bm25."""
        return self._q(
            "SELECT a.*, snippet(fts_actz, 1, '>>>', '<<<', '...', 32) AS _snippet "
            "FROM actz a JOIN fts_actz f ON a.id=f.rowid "
            "WHERE fts_actz MATCH ? ORDER BY bm25(fts_actz, 5.0, 10.0, 2.0) LIMIT ?",
            (query, limit),
        )
