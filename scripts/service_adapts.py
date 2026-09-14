"""TAUSIK AdaptsMixin — RENAR ADAPT-artifact service methods (v16r-adapt full §7).

An ADAPT is the architect's reconciliation of a client TZ with engineering
reality (renar.tech v1.0-draft §7): a forward interpretation (§7.4.3), backward
findings drawn from a closed category list (§7.4.4), and the architect's
signature (§7.5 — the client's was withdrawn by ADR-011). Deltas (§7.6)
supersede a prior ADAPT and a link to a superseded ADAPT is FATAL (§7.6.4).

Closed lists (finding category, signature role, link target) are validated here
(friendly error) and again by DB CHECK constraints (hard guarantee). The
architect signature is an ed25519 signature (v15-crypto) over the canonical
ADAPT body; the client signature is a recorded name + timestamp. Mixed into
ProjectService.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import sqlite3

from tausik_utils import ServiceError, utcnow_iso, validate_length, validate_slug

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

# The closed lists RENAR fixes live in `adapt_closed_lists` — declarations the
# standard governs, kept apart from the behaviour here. Re-exported so every
# existing `from service_adapts import FINDING_CATEGORIES` keeps working: a
# constant moving house is nobody else's business.
from adapt_closed_lists import (  # noqa: E402,F401
    ADAPT_BODY_SCHEMA,
    ADAPT_STATUSES,
    FINDING_CATEGORIES,
    HISTORICAL_SIGNATURE_ROLES,
    LINK_TARGETS,
    SIGNATURE_ROLES,
)


class AdaptsMixin:
    """Manage RENAR ADAPT artifacts, body parts, the architect signature and deltas."""

    be: SQLiteBackend

    # --- header ---

    def adapt_create(
        self,
        slug: str,
        title: str,
        tz_ref: str,
        parent_adapt: str | None = None,
        delta_n: int = 0,
        trigger_stage: str | None = None,
    ) -> str:
        """Create an ADAPT header. ``tz_ref`` (source TZ) is mandatory (§7.4.3).

        ``trigger_stage`` (ADR-007) records WHICH stage triggered this ADAPT —
        the field by which the standard tells several ADAPTs of one ТЗ apart.
        Optional: cardinality 0..N is not violated by a single ADAPT, but
        without the column we could not express the distinction at all.
        """
        try:
            validate_slug(slug)
            if not title:
                raise ValueError("ADAPT title is required.")
            validate_length("title", title)
            if not tz_ref:
                raise ValueError("ADAPT tz_ref (source TZ) is required.")
            validate_length("tz_ref", tz_ref, 128)
        except ValueError as e:
            raise ServiceError(str(e)) from e
        if self.be.adapt_get(slug):
            raise ServiceError(f"ADAPT '{slug}' already exists.")
        if parent_adapt and not self.be.adapt_get(parent_adapt):
            raise ServiceError(f"Parent ADAPT '{parent_adapt}' not found.")
        try:
            self.be.adapt_add(slug, title, tz_ref, "draft", parent_adapt, delta_n, trigger_stage)
        except sqlite3.IntegrityError as e:
            raise ServiceError(f"Could not create ADAPT '{slug}': {e}") from e
        return f"ADAPT '{slug}' created (tz_ref={tz_ref}, status=draft)."

    def adapt_list(self, status: str | None = None) -> list[dict[str, Any]]:
        """List ADAPTs, optionally filtered by status."""
        if status and status not in ADAPT_STATUSES:
            raise ServiceError(f"Invalid status '{status}'. Valid: {', '.join(ADAPT_STATUSES)}")
        return self.be.adapt_list(status)

    def adapt_show(self, slug: str) -> dict[str, Any]:
        """Return an ADAPT with its interpretations, findings, signatures, links."""
        adapt = self.be.adapt_get(slug)
        if not adapt:
            raise ServiceError(f"ADAPT '{slug}' not found")
        adapt["interpretations"] = self.be.interps_for_adapt(slug)
        adapt["findings"] = self.be.findings_for_adapt(slug)
        adapt["signatures"] = self.be.signatures_for_adapt(slug)
        adapt["links"] = self.be.links_for_adapt(slug)
        return adapt

    def adapt_delete(self, slug: str) -> str:
        """Delete an ADAPT and cascade-remove its body parts, signatures, links."""
        if not self.be.adapt_get(slug):
            raise ServiceError(f"ADAPT '{slug}' not found")
        self.be.adapt_delete(slug)
        return f"ADAPT '{slug}' deleted."

    # --- forward interpretation (§7.4.3) ---

    def adapt_interpret(
        self,
        adapt_slug: str,
        tz_ref: str,
        citation: str,
        engineering_interpretation: str,
        scope_in: str,
        scope_out: str,
        term_mapping: str | None = None,
        scenarios: str | None = None,
    ) -> str:
        """Add a forward-interpretation entry. tz_ref/citation/interpretation/
        scope_in/scope_out are MANDATORY per §7.4.3."""
        self._require_draft(adapt_slug)
        for name, val in (
            ("tz_ref", tz_ref),
            ("citation", citation),
            ("engineering_interpretation", engineering_interpretation),
            ("scope_in", scope_in),
            ("scope_out", scope_out),
        ):
            if not val or not val.strip():
                raise ServiceError(f"Forward interpretation field '{name}' is mandatory (§7.4.3).")
        self.be.interp_add(
            adapt_slug,
            tz_ref,
            citation,
            engineering_interpretation,
            scope_in,
            scope_out,
            term_mapping,
            scenarios,
        )
        return f"Interpretation for {tz_ref} added to ADAPT '{adapt_slug}'."

    # --- backward findings (closed category list, §7) ---

    def adapt_finding(
        self,
        adapt_slug: str,
        category: str,
        description: str,
        tz_ref: str | None = None,
        resolution: str | None = None,
    ) -> str:
        """Add a backward finding. ``category`` must be in FINDING_CATEGORIES."""
        self._require_draft(adapt_slug)
        if category not in FINDING_CATEGORIES:
            raise ServiceError(
                f"Invalid finding category '{category}'. "
                f"Valid (closed list of {len(FINDING_CATEGORIES)}): "
                f"{', '.join(FINDING_CATEGORIES)}"
            )
        if not description or not description.strip():
            raise ServiceError("Finding description is required.")
        self.be.finding_add(adapt_slug, category, description, tz_ref, resolution)
        return f"Finding ({category}) added to ADAPT '{adapt_slug}'."

    # --- architect signature (§7.5) ---

    def adapt_sign(
        self, slug: str, role: str, signed_by: str, project_dir: str | None = None
    ) -> str:
        """Record the architect's signature — ed25519 over the canonical body.

        Present ⇒ status 'approved' (§13.3.3 p.77: the findings-present branch
        requires 'approved' WITH an Architect signature; the signature itself
        stays in adapt_signatures — status and signature are separate facts).

        A CLIENT SIGNATURE IS REFUSED, and the refusal names why: ADR-011
        withdrew it as a fiction, and §7.5 now carries a paragraph on its
        absence. What the client approves lives in ACTZ, an artifact of its
        own; this method used to accept the role and this project used to
        advertise it in `adapt sign --help`, which is publishing a withdrawn
        norm as current.

        Signing an architect role without a project key is a friendly ServiceError,
        never a traceback (the key lives at .tausik/keys/, gitignored by design).
        """
        adapt = self.be.adapt_get(slug)
        if not adapt:
            raise ServiceError(f"ADAPT '{slug}' not found")
        if adapt["status"] == "superseded":
            raise ServiceError(f"ADAPT '{slug}' is superseded — cannot sign (§7.6.4).")
        if adapt["status"] == "approved":
            # Approved + body frozen — re-signing would silently overwrite a
            # sealed record. Amend via a delta instead (§7.6).
            raise ServiceError(
                f"ADAPT '{slug}' is already approved — create a delta to amend it (§7.6)."
            )
        if role == "client":
            raise ServiceError(
                "The client signature under ADAPT was withdrawn by RENAR ADR-011 and "
                "§7.5 now names only the architect: the client was signing an "
                "engineering document they had not read. What the client approves "
                "belongs in an ACTZ, not here. Existing client signatures are kept "
                "as audit records and are never rewritten."
            )
        if role not in SIGNATURE_ROLES:
            raise ServiceError(f"Invalid role '{role}'. Valid: {', '.join(SIGNATURE_ROLES)}")
        if not signed_by or not signed_by.strip():
            raise ServiceError("signed_by (signer identity) is required.")
        now = utcnow_iso()
        fingerprint: str | None = None
        signature: str | None = None
        if role == "architect":
            fingerprint, signature = self._architect_sign(slug, project_dir or os.getcwd())
        try:
            self.be.signature_set(slug, role, signed_by, now, fingerprint, signature)
        except sqlite3.IntegrityError as e:
            raise ServiceError(f"Could not record {role} signature for '{slug}': {e}") from e
        roles = {s["role"] for s in self.be.signatures_for_adapt(slug)}
        if roles >= set(SIGNATURE_ROLES):
            self.be.adapt_set_status(slug, "approved")
            return (
                f"ADAPT '{slug}' signed by {role} — architect signature recorded, "
                "status=approved (§7.5, §13.3.3 p.77)."
            )
        # Unreachable while SIGNATURE_ROLES holds one role, and kept rather than
        # deleted: it is the branch that runs if the standard ever adds a second
        # signer, and removing it would hide that this method decides `approved`
        # from the ROLE SET and not from a count.
        return f"ADAPT '{slug}' signed by {role} (awaiting {sorted(set(SIGNATURE_ROLES) - roles)})."

    def adapt_verify(self, slug: str, project_dir: str | None = None) -> dict[str, Any]:
        """Verify the architect ed25519 signature against the current body.

        Returns {signed: bool, valid: bool, reason: str}. A body edited after
        signing fails verification — the signature covers the canonical body.
        """
        if not self.be.adapt_get(slug):
            raise ServiceError(f"ADAPT '{slug}' not found")
        sig_row = next(
            (s for s in self.be.signatures_for_adapt(slug) if s["role"] == "architect"), None
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
        payload = canonical_bytes(self._canonical_body(slug))
        try:
            ok = ed25519.verify(public, payload, bytes.fromhex(sig_row["signature"]))
        except ValueError:
            ok = False
        return {"signed": True, "valid": ok, "reason": "ok" if ok else "signature mismatch"}

    # --- delta workflow (§7.6) ---

    def adapt_delta(
        self,
        parent_slug: str,
        new_slug: str,
        title: str,
        tz_ref: str,
        supersession_rationale: str | None = None,
    ) -> str:
        """Create a delta-ADAPT superseding ``parent_slug`` (§7.6).

        The parent's status becomes 'superseded'; subsequent links to it are
        FATAL (§7.6.4). The new ADAPT carries parent_adapt + an incremented
        delta_n and starts in 'draft' for its own architect signature.

        ``supersession_rationale`` is MANDATORY (ADR-007 p.108) — this is the
        only path into 'superseded'. Declared keyword-optional in the signature
        so the refusal is a ServiceError naming the standard rather than a
        TypeError naming Python; the backend enforces it regardless.

        A REFUSAL IS A NON-EVENT — with one condition, stated because the
        unconditional version would be a promise this cannot keep. Both writes
        share a transaction, so when this call OWNS that transaction a refusal
        leaves neither the supersession nor the delta header behind. When the
        caller already had one open, ownership stays with the caller: the
        header is written into THEIR transaction and only their rollback
        removes it. Undoing just our own part would take a SAVEPOINT, which
        this backend does not offer.
        """
        parent = self.be.adapt_get(parent_slug)
        if not parent:
            raise ServiceError(f"Parent ADAPT '{parent_slug}' not found")
        if self.be.adapt_get(new_slug):
            raise ServiceError(f"ADAPT '{new_slug}' already exists.")
        # BOTH WRITES IN ONE TRANSACTION, and that is the whole point. The
        # rationale guard lives in `adapt_set_status`, the lowest primitive
        # that writes the column, so it necessarily refuses AFTER the delta
        # header has been written. While the two steps auto-committed
        # separately, that refusal was a HALF-WRITE: the parent stayed live
        # (correct, and the only half the tests asserted) while the child
        # survived as an orphan carrying delta_n>0 and status='draft'. It then
        # blocked its own repair, because `adapt_create` refuses a slug that
        # exists -- so retrying the SAME slug with a proper rationale failed
        # forever. It also counted as a live change-set in the RENAR manifest,
        # whose `delta_adapts_count` selects `delta_n > 0 AND status !=
        # 'superseded'`. A refusal has to be a NON-EVENT, not a partial write.
        #
        # `or 0` guards a NULL delta_n (defensive — column is NOT NULL DEFAULT 0,
        # but a hand-edited / pre-migration row must not crash with a TypeError).
        # OWNERSHIP IS THE BACKEND'S JOB, NOT THIS FUNCTION'S. `begin_tx`
        # no-ops inside an open transaction, but `commit_tx`/`rollback_tx` do
        # not, so unwinding a transaction we did not open would discard the
        # CALLER's rows and hand back a closed transaction it still believes it
        # owns -- measured, not feared: an outer `begin_tx` + `epic_add` lost
        # its epic to a refused delta nested inside it, with no exception to
        # say so. `transaction()` keeps that accounting once (and, nested,
        # unwinds only OUR part via SAVEPOINT, which the hand-written guard
        # here could not do -- it could only leave the header for the caller
        # to roll back). Refusal stays a NON-EVENT either way.
        try:
            with self.be.transaction():
                msg = self.adapt_create(
                    new_slug,
                    title,
                    tz_ref,
                    parent_adapt=parent_slug,
                    delta_n=(parent["delta_n"] or 0) + 1,
                )
                self.be.adapt_set_status(parent_slug, "superseded", supersession_rationale)
        except ValueError as e:
            # The guard spoke: a supersession without a reason must not be
            # recorded, and neither must its delta.
            raise ServiceError(str(e)) from e
        return f"{msg} Parent ADAPT '{parent_slug}' superseded (§7.6)."

    # --- links (adapt ↔ task/spec) ---

    def adapt_link(self, adapt_slug: str, target_type: str, target_slug: str) -> str:
        """Link an ADAPT to a task/spec it produced or constrains.

        A link to a SUPERSEDED ADAPT is FATAL (§7.6.4 dangling-ref guard) — the
        canonical reference must point at the live delta, never the dead parent.
        """
        if target_type not in LINK_TARGETS:
            raise ServiceError(
                f"Invalid target_type '{target_type}'. Valid: {', '.join(LINK_TARGETS)}"
            )
        adapt = self.be.adapt_get(adapt_slug)
        if not adapt:
            raise ServiceError(f"ADAPT '{adapt_slug}' not found")
        if adapt["status"] == "superseded":
            raise ServiceError(
                f"ADAPT '{adapt_slug}' is superseded — linking to it is a FATAL "
                "dangling reference (§7.6.4). Link the live delta instead."
            )
        if target_type == "task" and not self.be.task_get(target_slug):
            raise ServiceError(f"Task '{target_slug}' not found")
        if target_type == "spec" and not self.be.spec_get(target_slug):
            raise ServiceError(f"SPEC '{target_slug}' not found")
        try:
            self.be.adapt_link(adapt_slug, target_type, target_slug)
        except sqlite3.IntegrityError:
            raise ServiceError(
                f"ADAPT '{adapt_slug}' already links to {target_type} '{target_slug}'."
            ) from None
        return f"ADAPT '{adapt_slug}' linked to {target_type} '{target_slug}'."

    def adapt_unlink(self, adapt_slug: str, target_type: str, target_slug: str) -> str:
        """Remove an ADAPT↔target link."""
        n = self.be.adapt_unlink(adapt_slug, target_type, target_slug)
        if not n:
            raise ServiceError(
                f"No link between ADAPT '{adapt_slug}' and {target_type} '{target_slug}'."
            )
        return f"Unlinked ADAPT '{adapt_slug}' from {target_type} '{target_slug}'."

    def adapts_for_target(self, target_type: str, target_slug: str) -> list[dict[str, Any]]:
        """ADAPTs linked to a task/spec."""
        return self.be.adapts_for_target(target_type, target_slug)

    def adapt_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """FTS5 search over ADAPTs. A malformed FTS5 query is a friendly error."""
        limit = max(1, min(int(limit), 200))
        try:
            return self.be.adapt_search(query, limit)
        except sqlite3.OperationalError as e:
            raise ServiceError(f"Invalid search query '{query}': {e}") from e

    # --- internals ---

    def _require_draft(self, slug: str) -> None:
        """Body parts may only be added while the ADAPT is mutable (not signed/superseded)."""
        adapt = self.be.adapt_get(slug)
        if not adapt:
            raise ServiceError(f"ADAPT '{slug}' not found")
        if adapt["status"] != "draft":
            raise ServiceError(
                f"ADAPT '{slug}' is '{adapt['status']}' — body is frozen; "
                "create a delta to amend it (§7.6)."
            )

    def _canonical_body(self, slug: str) -> dict[str, Any]:
        """Deterministic ADAPT body — the signing payload. Lists are id-ordered."""
        a = self.be.adapt_get(slug) or {}
        interps = [
            {
                k: i[k]
                for k in (
                    "tz_ref",
                    "citation",
                    "engineering_interpretation",
                    "term_mapping",
                    "scenarios",
                    "scope_in",
                    "scope_out",
                )
            }
            for i in self.be.interps_for_adapt(slug)
        ]
        findings = [
            {k: f[k] for k in ("category", "description", "tz_ref", "resolution")}
            for f in self.be.findings_for_adapt(slug)
        ]
        return {
            "schema": ADAPT_BODY_SCHEMA,
            "slug": a.get("slug"),
            "title": a.get("title"),
            "tz_ref": a.get("tz_ref"),
            "parent_adapt": a.get("parent_adapt"),
            "delta_n": a.get("delta_n"),
            "interpretations": interps,
            "findings": findings,
        }

    def _architect_sign(self, slug: str, project_dir: str) -> tuple[str, str]:
        """Return (fingerprint, signature_hex) for the architect ed25519 signature."""
        import crypto_ed25519 as ed25519
        import crypto_keys
        from crypto_receipt import ReceiptError, canonical_bytes

        try:
            seed = crypto_keys.load_seed(project_dir)
        except crypto_keys.KeyError_ as e:
            raise ServiceError(f"architect signature needs a project key: {e}") from e
        try:
            payload = canonical_bytes(self._canonical_body(slug))
        except ReceiptError as e:
            raise ServiceError(f"ADAPT body is not canonicalizable: {e}") from e
        public = ed25519.public_from_seed(seed)
        signature = ed25519.sign(seed, payload)
        return crypto_keys.fingerprint(public), signature.hex()
