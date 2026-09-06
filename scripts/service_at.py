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
