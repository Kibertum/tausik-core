"""TAUSIK ActzMixin -- RENAR ACTZ-artifact service methods.

ACTZ (RENAR Sec5A, ADR-011, accepted) is the contractual clarification
protocol -- "Протокол уточнения ТЗ N N" -- the client-facing artifact whose
signature carries contractual weight (unlike ADAPT, an internal document the
client never sees). Lifecycle draft -> sent -> signed -> superseded (Sec5.5.3):
status is COMPUTED from signature-role coverage, never written as an
independent fact. Mixed into ProjectService alongside AdaptsMixin.

See backend_schema_actz for the signature design (one project ed25519 key,
architect signs for real, client records name+timestamp only) and
actz_closed_lists for the closed lists this module re-exports.
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, utcnow_iso, validate_length, validate_slug

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

from actz_closed_lists import (  # noqa: E402,F401
    ACTZ_BODY_SCHEMA,
    ACTZ_STATUSES,
    LINK_TARGETS,
    REQUIRED_SIGNATURE_ROLES,
    SIGNATURE_ROLES,
)

# The forbidden word, matched by DECLENSION SUFFIX with a word boundary at the
# END only -- see actz_closed_lists / AC-1. "акт", "акта", "акту", "актом",
# "акте", "акты", "актов", "актам", "актами", "актах" match; "актив",
# "активный", "фактор", "контракт", "факт" do not, because none of them ends
# right after one of these suffixes -- no allowlist needed, the shape of the
# word itself is the discriminator.
FORBIDDEN_WORD_RE = re.compile(r"\bакт(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b", re.IGNORECASE)


def display_name(actz_row: dict[str, Any]) -> str:
    """The contractual name (Sec5A): 'Протокол уточнения ТЗ N {id}'. Computed, never stored."""
    return f"Протокол уточнения ТЗ № {actz_row['id']}"


class ActzMixin:
    """Manage RENAR ACTZ artifacts, their points, signatures, links and deltas."""

    be: SQLiteBackend

    # --- header ---

    def actz_create(
        self,
        slug: str,
        title: str,
        tz_ref: str,
        parent_actz: str | None = None,
        delta_n: int = 0,
    ) -> str:
        """Create an ACTZ header. A late protocol (dated after other work) is
        the NORMAL case (Sec5A), not an anomaly -- creation carries no check
        against other tasks' or ADAPTs' dates."""
        try:
            validate_slug(slug)
            if not title:
                raise ValueError("ACTZ title is required.")
            validate_length("title", title)
            if not tz_ref:
                raise ValueError("ACTZ tz_ref (source TZ) is required.")
            validate_length("tz_ref", tz_ref, 128)
        except ValueError as e:
            raise ServiceError(str(e)) from e
        if self.be.actz_get(slug):
            raise ServiceError(f"ACTZ '{slug}' already exists.")
        if parent_actz and not self.be.actz_get(parent_actz):
            raise ServiceError(f"Parent ACTZ '{parent_actz}' not found.")
        try:
            self.be.actz_add(slug, title, tz_ref, "draft", parent_actz, delta_n)
        except sqlite3.IntegrityError as e:
            raise ServiceError(f"Could not create ACTZ '{slug}': {e}") from e
        return f"ACTZ '{slug}' created (tz_ref={tz_ref}, status=draft)."

    def actz_list(self, status: str | None = None) -> list[dict[str, Any]]:
        """List ACTZ headers, optionally filtered by status."""
        if status and status not in ACTZ_STATUSES:
            raise ServiceError(f"Invalid status '{status}'. Valid: {', '.join(ACTZ_STATUSES)}")
        rows = self.be.actz_list(status)
        for r in rows:
            r["display_name"] = display_name(r)
        return rows

    def actz_show(self, slug: str) -> dict[str, Any]:
        """Return an ACTZ with its points, signatures, links (JSON-ready)."""
        actz = self.be.actz_get(slug)
        if not actz:
            raise ServiceError(f"ACTZ '{slug}' not found")
        actz["display_name"] = display_name(actz)
        actz["points"] = self.be.points_for_actz(slug)
        actz["signatures"] = self.be.signatures_for_actz(slug)
        actz["links"] = self.be.links_for_actz(slug)
        return actz

    def actz_delete(self, slug: str) -> str:
        """Delete an ACTZ and cascade-remove its points, signatures, links, decided-in edges."""
        if not self.be.actz_get(slug):
            raise ServiceError(f"ACTZ '{slug}' not found")
        self.be.actz_delete(slug)
        return f"ACTZ '{slug}' deleted."

    # --- points ---

    def actz_point_add(self, actz_slug: str, point_no: int, tz_ref: str, text: str) -> str:
        """Add a numbered point. Points may only be added while the ACTZ is
        'draft' -- the same freeze rule ADAPT applies to its body parts.

        ``tz_ref`` (v53) names the clause of the original ТЗ (or a prior ACTZ
        point) this point clarifies -- mandatory, same shape as
        adapt_interpretations.tz_ref: final_tz_snapshot groups by it.
        """
        self._actz_require_draft(actz_slug)
        if point_no < 1:
            raise ServiceError("point_no must be >= 1.")
        if not tz_ref or not tz_ref.strip():
            raise ServiceError("Point tz_ref (which ТЗ clause this clarifies) is required.")
        if not text or not text.strip():
            raise ServiceError("Point text is required.")
        try:
            self.be.actz_point_add(actz_slug, point_no, tz_ref, text)
        except sqlite3.IntegrityError as e:
            raise ServiceError(f"ACTZ '{actz_slug}' already has a point {point_no}: {e}") from e
        return f"Point {point_no} added to ACTZ '{actz_slug}'."

    # --- signatures (Sec5.5.3) ---

    def actz_sign(
        self, slug: str, role: str, signed_by: str, project_dir: str | None = None
    ) -> str:
        """Record a signature. architect = real ed25519 over the canonical
        body (like ADAPT). client = signed_by + signed_at ONLY, no signature/
        fingerprint -- see module docstring for why this is not the fiction
        ADR-011 withdrew from ADAPT.

        Status is computed from role coverage: first signature -> 'sent',
        both roles -> 'signed'.
        """
        actz = self.be.actz_get(slug)
        if not actz:
            raise ServiceError(f"ACTZ '{slug}' not found")
        if actz["status"] == "superseded":
            raise ServiceError(f"ACTZ '{slug}' is superseded — cannot sign.")
        if actz["status"] == "signed":
            raise ServiceError(f"ACTZ '{slug}' is already signed — create a delta to amend it.")
        if role not in SIGNATURE_ROLES:
            raise ServiceError(f"Invalid role '{role}'. Valid: {', '.join(SIGNATURE_ROLES)}")
        if not signed_by or not signed_by.strip():
            raise ServiceError("signed_by (signer identity) is required.")
        now = utcnow_iso()
        fingerprint: str | None = None
        signature: str | None = None
        if role == "architect":
            fingerprint, signature = self._actz_architect_sign(slug, project_dir or os.getcwd())
        try:
            self.be.actz_signature_set(slug, role, signed_by, now, fingerprint, signature)
        except sqlite3.IntegrityError as e:
            raise ServiceError(f"Could not record {role} signature for '{slug}': {e}") from e
        roles = {s["role"] for s in self.be.signatures_for_actz(slug)}
        if roles >= set(REQUIRED_SIGNATURE_ROLES):
            self.be.actz_set_status(slug, "signed")
            return f"ACTZ '{slug}' signed by {role} — both roles present, status=signed (§5.5.3)."
        self.be.actz_set_status(slug, "sent")
        missing = sorted(set(REQUIRED_SIGNATURE_ROLES) - roles)
        return f"ACTZ '{slug}' signed by {role} — status=sent (awaiting {missing})."

    def actz_verify(self, slug: str, project_dir: str | None = None) -> dict[str, Any]:
        """Verify the architect ed25519 signature against the current body.

        The client role has no cryptographic signature to verify (see module
        docstring) -- this checks the architect role only, same shape as
        ``adapt_verify``.
        """
        if not self.be.actz_get(slug):
            raise ServiceError(f"ACTZ '{slug}' not found")
        sig_row = next(
            (s for s in self.be.signatures_for_actz(slug) if s["role"] == "architect"), None
        )
        if not sig_row or not sig_row.get("signature"):
            return {"signed": False, "valid": False, "reason": "no architect signature"}
        import crypto_ed25519 as ed25519
        import crypto_keys
        from crypto_receipt import canonical_bytes

        try:
            public = crypto_keys.load_public(project_dir or os.getcwd())
        except crypto_keys.KeyError_ as e:
            raise ServiceError(str(e)) from e
        payload = canonical_bytes(self._actz_canonical_body(slug))
        try:
            ok = ed25519.verify(public, payload, bytes.fromhex(sig_row["signature"]))
        except ValueError:
            ok = False
        return {"signed": True, "valid": ok, "reason": "ok" if ok else "signature mismatch"}

    # --- delta (amend a signed/superseded ACTZ) ---

    def actz_delta(
        self,
        parent_slug: str,
        new_slug: str,
        title: str,
        tz_ref: str,
        supersession_rationale: str | None = None,
    ) -> str:
        """Create a delta-ACTZ superseding ``parent_slug``. Same transaction-
        ownership shape as ``adapt_delta`` -- a refusal (missing rationale)
        must be a non-event, not a half-write."""
        parent = self.be.actz_get(parent_slug)
        if not parent:
            raise ServiceError(f"Parent ACTZ '{parent_slug}' not found")
        if self.be.actz_get(new_slug):
            raise ServiceError(f"ACTZ '{new_slug}' already exists.")
        try:
            with self.be.transaction():
                msg = self.actz_create(
                    new_slug,
                    title,
                    tz_ref,
                    parent_actz=parent_slug,
                    delta_n=(parent["delta_n"] or 0) + 1,
                )
                self.be.actz_set_status(parent_slug, "superseded", supersession_rationale)
        except ValueError as e:
            raise ServiceError(str(e)) from e
        return f"{msg} Parent ACTZ '{parent_slug}' superseded."

    # --- links (actz <-> task/spec) ---

    def actz_link(self, actz_slug: str, target_type: str, target_slug: str) -> str:
        """Link an ACTZ to a task/spec it produced or constrains."""
        if target_type not in LINK_TARGETS:
            raise ServiceError(
                f"Invalid target_type '{target_type}'. Valid: {', '.join(LINK_TARGETS)}"
            )
        actz = self.be.actz_get(actz_slug)
        if not actz:
            raise ServiceError(f"ACTZ '{actz_slug}' not found")
        if actz["status"] == "superseded":
            raise ServiceError(
                f"ACTZ '{actz_slug}' is superseded — linking to it is a dangling reference. "
                "Link the live delta instead."
            )
        if target_type == "task" and not self.be.task_get(target_slug):
            raise ServiceError(f"Task '{target_slug}' not found")
        if target_type == "spec" and not self.be.spec_get(target_slug):
            raise ServiceError(f"SPEC '{target_slug}' not found")
        try:
            self.be.actz_link(actz_slug, target_type, target_slug)
        except sqlite3.IntegrityError:
            raise ServiceError(
                f"ACTZ '{actz_slug}' already links to {target_type} '{target_slug}'."
            ) from None
        return f"ACTZ '{actz_slug}' linked to {target_type} '{target_slug}'."

    def actz_unlink(self, actz_slug: str, target_type: str, target_slug: str) -> str:
        """Remove an ACTZ<->target link."""
        n = self.be.actz_unlink(actz_slug, target_type, target_slug)
        if not n:
            raise ServiceError(
                f"No link between ACTZ '{actz_slug}' and {target_type} '{target_slug}'."
            )
        return f"Unlinked ACTZ '{actz_slug}' from {target_type} '{target_slug}'."

    def actzs_for_target(self, target_type: str, target_slug: str) -> list[dict[str, Any]]:
        """ACTZ headers linked to a task/spec."""
        return self.be.actzs_for_target(target_type, target_slug)

    def actz_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """FTS5 search over ACTZ headers. A malformed FTS5 query is a friendly error."""
        limit = max(1, min(int(limit), 200))
        try:
            return self.be.actz_search(query, limit)
        except sqlite3.OperationalError as e:
            raise ServiceError(f"Invalid search query '{query}': {e}") from e

    # --- final-TZ (RENAR §5A.4): derived, not a third copy of the text ---

    def final_tz_snapshot(self, as_of: str | None = None) -> list[dict[str, Any]]:
        """The acceptance reference: per tz_ref, the LATEST both-role-signed
        ACTZ point (§5A.4 — priority to the later signed document), naming
        what it superseded. ``as_of`` (ISO-8601) shows it at any past moment:
        only points whose completion (max signed_at of both roles) is <=
        as_of are considered. Read-only projection over actz/actz_points/
        actz_signatures — nothing new is stored; ADAPT never enters the
        reference (§5A.4: that is what keeps acceptance legally clean).
        """
        rows = self.be.actz_points_with_completion()
        if as_of:
            rows = [r for r in rows if r["completed_at"] and r["completed_at"] <= as_of]
        by_ref: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            by_ref.setdefault(r["tz_ref"], []).append(r)
        snapshot: list[dict[str, Any]] = []
        for tz_ref in sorted(by_ref):
            points = sorted(by_ref[tz_ref], key=lambda r: r["completed_at"] or "")
            governing, superseded = points[-1], points[:-1]
            snapshot.append(
                {
                    "tz_ref": tz_ref,
                    "governing_actz": governing["actz_slug"],
                    "governing_point_no": governing["point_no"],
                    "governing_text": governing["text"],
                    "completed_at": governing["completed_at"],
                    "overridden": [
                        {
                            "actz_slug": p["actz_slug"],
                            "point_no": p["point_no"],
                            "completed_at": p["completed_at"],
                        }
                        for p in superseded
                    ],
                }
            )
        return snapshot

    def orphan_signed_points(self) -> list[dict[str, Any]]:
        """Signed decisions no ADAPT reflects — an obligation outside
        requirements (§5A.4, fatal), found by QUERY rather than by eye."""
        return self.be.orphan_signed_points()

    # --- decided-in (ADAPT backward finding -> a POINT of a SIGNED ACTZ) ---

    def actz_decided_in(
        self, adapt_slug: str, finding_id: int, actz_slug: str, actz_point_no: int, linked_by: str
    ) -> str:
        """Record that an ADAPT finding was decided-in a point of a SIGNED
        ACTZ. Refuses a draft/sent target: citing a not-yet-contractual point
        as the decision would misrepresent what actually binds anything."""
        if not self.be.adapt_get(adapt_slug):
            raise ServiceError(f"ADAPT '{adapt_slug}' not found")
        finding = next(
            (f for f in self.be.findings_for_adapt(adapt_slug) if f["id"] == finding_id), None
        )
        if not finding:
            raise ServiceError(f"Finding {finding_id} not found on ADAPT '{adapt_slug}'")
        actz = self.be.actz_get(actz_slug)
        if not actz:
            raise ServiceError(f"ACTZ '{actz_slug}' not found")
        if actz["status"] != "signed":
            raise ServiceError(
                f"ACTZ '{actz_slug}' is '{actz['status']}' — decided-in requires a SIGNED "
                "point (an unsigned point carries no contractual weight yet)."
            )
        if not self.be.actz_point_get(actz_slug, actz_point_no):
            raise ServiceError(f"ACTZ '{actz_slug}' has no point {actz_point_no}.")
        if not linked_by or not linked_by.strip():
            raise ServiceError("linked_by (who recorded this edge) is required.")
        try:
            self.be.decided_in_add(adapt_slug, finding_id, actz_slug, actz_point_no, linked_by)
        except sqlite3.IntegrityError:
            raise ServiceError("That decided-in edge is already recorded.") from None
        return (
            f"Finding {finding_id} of ADAPT '{adapt_slug}' decided-in point "
            f"{actz_point_no} of ACTZ '{actz_slug}'."
        )

    def actz_decided_in_remove(
        self, adapt_slug: str, finding_id: int, actz_slug: str, actz_point_no: int
    ) -> str:
        """Remove a decided-in edge."""
        n = self.be.decided_in_remove(adapt_slug, finding_id, actz_slug, actz_point_no)
        if not n:
            raise ServiceError("No such decided-in edge.")
        return (
            f"Removed decided-in edge: finding {finding_id} of ADAPT '{adapt_slug}' <-> "
            f"point {actz_point_no} of ACTZ '{actz_slug}'."
        )

    # --- internals ---

    def _actz_require_draft(self, slug: str) -> None:
        """Points may only be added while the ACTZ is mutable (still 'draft')."""
        actz = self.be.actz_get(slug)
        if not actz:
            raise ServiceError(f"ACTZ '{slug}' not found")
        if actz["status"] != "draft":
            raise ServiceError(
                f"ACTZ '{slug}' is '{actz['status']}' — body is frozen; create a delta to amend it."
            )

    def _actz_canonical_body(self, slug: str) -> dict[str, Any]:
        """Deterministic ACTZ body -- the architect's signing payload. Points are point_no-ordered."""
        a = self.be.actz_get(slug) or {}
        points = [
            {"point_no": p["point_no"], "tz_ref": p["tz_ref"], "text": p["text"]}
            for p in self.be.points_for_actz(slug)
        ]
        return {
            "schema": ACTZ_BODY_SCHEMA,
            "slug": a.get("slug"),
            "title": a.get("title"),
            "tz_ref": a.get("tz_ref"),
            "parent_actz": a.get("parent_actz"),
            "delta_n": a.get("delta_n"),
            "points": points,
        }

    def _actz_architect_sign(self, slug: str, project_dir: str) -> tuple[str, str]:
        """Return (fingerprint, signature_hex) for the architect ed25519 signature."""
        import crypto_ed25519 as ed25519
        import crypto_keys
        from crypto_receipt import ReceiptError, canonical_bytes

        try:
            seed = crypto_keys.load_seed(project_dir)
        except crypto_keys.KeyError_ as e:
            raise ServiceError(f"architect signature needs a project key: {e}") from e
        try:
            payload = canonical_bytes(self._actz_canonical_body(slug))
        except ReceiptError as e:
            raise ServiceError(f"ACTZ body is not canonicalizable: {e}") from e
        public = ed25519.public_from_seed(seed)
        signature = ed25519.sign(seed, payload)
        return crypto_keys.fingerprint(public), signature.hex()
