"""TAUSIK AtMixin -- RENAR AT (Acceptance Test) artifact service methods.

AT (RENAR Sec8A, ADR-012, accepted) closes the one class of defect
traceability (TC -> SR -> ADAPT -> ТЗ) cannot catch: a wrong interpretation
makes every TC pass because the system perfectly matches the wrong reading.
See backend_schema_at for the three mandatory properties (isolated generation,
regeneration before trial, verbatim tz_text) and why this module enforces the
third directly but only RECORDS provenance for the first two -- TAUSIK is
stdlib-only, so isolation and generation are a documented procedure
(docs/en/at-generation-procedure.md), not code here.

Mixed into ProjectService alongside ActzMixin -- ``self.final_tz_snapshot()``
is reachable directly, no import needed.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, validate_length, validate_slug

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

_OUTCOMES = ("red", "green")

# §8A.4 / §10.4.3: the four-cell matrix, MACHINE-DERIVED from two outcomes,
# never a table written out in a doc. A MODULE-LEVEL function, not an
# AtMixin method -- it is pure (two strings in, one dict out), needs no
# instance state, and class_surface's ratchet has already turned three times
# this session for genuinely new instance methods; a stateless helper does
# not belong on the composed class any more than
# project_service.normalize_usage_time_bound does, for the same reason.
_MATRIX: dict[tuple[str, str], tuple[str, str | None]] = {
    ("red", "green"): (
        "interpretation error — AT fails a client-approved clause while TC (the "
        "provisional stand-in, see module docstring) is green: the code matches "
        "an interpretation the client never signed off on",
        "ADAPT",
    ),
    ("red", "red"): ("code defect — both levels disagree with the contract", "code"),
    ("green", "red"): (
        "stale test OR an internal norm stricter than the contract — both named, "
        "neither chosen for the reader: TC failing while the client-approved "
        "clause holds does not by itself say which",
        "review",
    ),
    ("green", "green"): ("no divergence", None),
}


def route_at_tc(at_outcome: str, tc_outcome: str) -> dict[str, Any]:
    """§8A.4/§10.4.3's routing matrix. TC here is WHATEVER the caller supplies
    -- TAUSIK has no first-class TC artifact yet (renar_tc_premise.py), so
    this function never reads pytest/verification_runs itself and never
    silently stands in for that missing entity. It only routes two already-
    named outcomes; getting `tc_outcome` honestly is the caller's job.
    """
    if at_outcome not in _OUTCOMES:
        raise ValueError(f"at_outcome must be one of {_OUTCOMES}, got {at_outcome!r}")
    if tc_outcome not in _OUTCOMES:
        raise ValueError(f"tc_outcome must be one of {_OUTCOMES}, got {tc_outcome!r}")
    diagnosis, routes_to = _MATRIX[(at_outcome, tc_outcome)]
    return {
        "at_outcome": at_outcome,
        "tc_outcome": tc_outcome,
        "diagnosis": diagnosis,
        "routes_to": routes_to,
    }


class AtMixin:
    """Manage RENAR AT (Acceptance Test) artifacts and their freshness."""

    be: SQLiteBackend

    def at_create(
        self,
        slug: str,
        tz_ref: str,
        tz_text: str,
        scenario: str,
        source_as_of: str,
        generated_by: str,
    ) -> str:
        """Record an AT. ``tz_text`` (Sec8A property 3, verbatim quote) and
        ``generated_by`` (who/what produced it -- the orchestrator, per
        docs/en/at-generation-procedure.md, never the isolated agent itself)
        are both mandatory: an AT without either cannot be audited."""
        try:
            validate_slug(slug)
            if not tz_ref or not tz_ref.strip():
                raise ValueError("AT tz_ref is required.")
            validate_length("tz_ref", tz_ref, 128)
            if not tz_text or not tz_text.strip():
                raise ValueError("AT tz_text (verbatim contract quote, §8A) is required.")
            if not scenario or not scenario.strip():
                raise ValueError("AT scenario is required.")
            if not source_as_of or not source_as_of.strip():
                raise ValueError(
                    "AT source_as_of (which final-TZ moment this derives from) is required."
                )
            if not generated_by or not generated_by.strip():
                raise ValueError(
                    "AT generated_by (who recorded this, §8A isolation audit) is required."
                )
        except ValueError as e:
            raise ServiceError(str(e)) from e
        if self.be.at_get(slug):
            raise ServiceError(f"AT '{slug}' already exists.")
        try:
            self.be.at_add(slug, tz_ref, tz_text, scenario, source_as_of, generated_by)
        except sqlite3.IntegrityError as e:
            raise ServiceError(f"Could not create AT '{slug}': {e}") from e
        return f"AT '{slug}' recorded (tz_ref={tz_ref})."

    def at_show(self, slug: str) -> dict[str, Any]:
        """Return an AT record."""
        at = self.be.at_get(slug)
        if not at:
            raise ServiceError(f"AT '{slug}' not found")
        return at

    def at_list(self, tz_ref: str | None = None) -> list[dict[str, Any]]:
        """List AT records, optionally filtered by tz_ref."""
        return self.be.at_list(tz_ref)

    def at_delete(self, slug: str) -> str:
        """Delete an AT record."""
        if not self.be.at_get(slug):
            raise ServiceError(f"AT '{slug}' not found")
        self.be.at_delete(slug)
        return f"AT '{slug}' deleted."

    def at_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """FTS5 search over AT records. A malformed FTS5 query is a friendly error."""
        limit = max(1, min(int(limit), 200))
        try:
            return self.be.at_search(query, limit)
        except sqlite3.OperationalError as e:
            raise ServiceError(f"Invalid search query '{query}': {e}") from e

    def at_check_freshness(self, slug: str | None = None) -> list[dict[str, Any]]:
        """Which AT records are STALE against the current final_tz_snapshot
        for their tz_ref (§8A property 2). Returns only the stale ones --
        an empty list is "nothing to regenerate", not "nothing was checked".
        """
        if slug:
            row = self.be.at_get(slug)
            if not row:
                raise ServiceError(f"AT '{slug}' not found")
            ats = [row]
        else:
            ats = self.be.at_list()
        if not ats:
            return []
        current_by_ref = {row["tz_ref"]: row for row in self.final_tz_snapshot()}  # type: ignore[attr-defined]
        stale: list[dict[str, Any]] = []
        for a in ats:
            current = current_by_ref.get(a["tz_ref"])
            if current is None:
                stale.append(
                    {
                        "slug": a["slug"],
                        "tz_ref": a["tz_ref"],
                        "reason": "no signed governing point for this tz_ref anymore",
                    }
                )
                continue
            if current["completed_at"] != a["source_as_of"]:
                stale.append(
                    {
                        "slug": a["slug"],
                        "tz_ref": a["tz_ref"],
                        "reason": (
                            f"governing point changed: AT derived as of {a['source_as_of']}, "
                            f"now {current['completed_at']} "
                            f"({current['governing_actz']}#{current['governing_point_no']})"
                        ),
                    }
                )
        return stale

    # --- results, diagnosis, release readiness (§8A.4 / §10.4.3) ---

    def at_record_result(self, at_slug: str, outcome: str, note: str | None = None) -> str:
        """Record one observed trial of an AT. Append-only: a re-run is a new
        row, never an overwrite of the last one (§8A.4 needs the history to
        answer "what governed at time T", the same reason final_tz_snapshot
        keeps superseded ACTZ points instead of discarding them)."""
        if not self.be.at_get(at_slug):
            raise ServiceError(f"AT '{at_slug}' not found")
        if outcome not in _OUTCOMES:
            raise ServiceError(f"Invalid outcome '{outcome}'. Valid: {', '.join(_OUTCOMES)}")
        self.be.at_result_add(at_slug, outcome, note)
        return f"AT '{at_slug}' result recorded: {outcome}."

    def at_diagnose(self, at_slug: str, tc_outcome: str) -> dict[str, Any]:
        """Route an AT's LATEST recorded outcome against a caller-supplied
        tc_outcome (§8A.4/§10.4.3). Refuses an AT never exercised — there is
        no outcome to route, and guessing one would fabricate evidence."""
        latest = self.be.at_latest_outcome(at_slug)
        if not latest:
            raise ServiceError(
                f"AT '{at_slug}' has no recorded trial — run `at record-result` first."
            )
        try:
            result = route_at_tc(latest["outcome"], tc_outcome)
        except ValueError as e:
            raise ServiceError(str(e)) from e
        result["at_slug"] = at_slug
        result["at_recorded_at"] = latest["recorded_at"]
        return result

    def at_release_readiness(self) -> dict[str, Any]:
        """Sec8A.4's release gate: ready only when EVERY AT's latest outcome
        is green AND fresh against the current final-TZ. Deliberately reads
        NO tc_outcome — the standard's release condition is stated purely in
        terms of AT and the final-TZ, not TC (see class docstring on why TC
        cannot enter this project's gates yet). Distinct from QG-4, which is
        optional and measures business outcome, not contract conformance.
        """
        blocking: list[dict[str, Any]] = []
        stale_by_slug = {s["slug"]: s["reason"] for s in self.at_check_freshness()}
        for a in self.be.at_list():
            slug = a["slug"]
            latest = self.be.at_latest_outcome(slug)
            if not latest:
                blocking.append({"slug": slug, "reason": "never exercised — no recorded trial"})
            elif latest["outcome"] != "green":
                blocking.append(
                    {"slug": slug, "reason": f"latest outcome is '{latest['outcome']}'"}
                )
            if slug in stale_by_slug:
                blocking.append({"slug": slug, "reason": f"stale: {stale_by_slug[slug]}"})
        return {"ready": not blocking, "blocking": blocking}
