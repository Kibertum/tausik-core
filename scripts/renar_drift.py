"""RENAR drift detectors — drift-1 (schema) + drift-7 (TC↔requirement provenance).

RENAR §3.11 defines 8 classes of drift a conformant substrate must detect.
This module implements 2 of them as **warning-mode** read-only detectors over
TAUSIK's own RENAR artifact store (specs / adapts / task↔spec links):

  * **drift-1 — schema drift** (§3.11.1): a stored artifact violates a schema
    invariant. DB CHECK constraints catch enum membership *at insert time*, but
    cannot express cross-field rules (delta_n ↔ parent_adapt, signed ↔ dual
    signature) and do not re-validate legacy rows after a migration tightens the
    schema. This detector re-validates every row against the canonical closed
    lists + cross-field invariants, so direct-DB tampering or a migration gap
    surfaces instead of silently passing.

  * **drift-7 — TC↔requirement provenance drift** (§3.11.7): a verification's
    link to its requirement has gone stale. TAUSIK has no first-class TC table;
    the verification unit is a task (its acceptance_criteria == the "TC") linked
    to a SPEC (the requirement) via ``task_specs``. Two stale-provenance signals:
      - ``stale-verification``: a *done* task linked to a SPEC the SPEC was edited
        *after* the link was made → the passing verification predates the current
        requirement version.
      - ``deprecated-requirement``: an *in-flight* task linked to a *deprecated*
        SPEC → work proceeding against a retired requirement.

Both run as warn-only gates (never block) and via ``tausik drift``. Detectors are
PURE: they take a sqlite3.Connection and return a list of Finding dicts. They
never write. On a DB missing the artifact tables (older schema) they return [].

The other 6 drift classes (lifecycle / SoT / impl / terminology / order / test-
fitting) are out of scope for this task — see RENAR §3.11 and docs/audit.
"""

from __future__ import annotations

import sqlite3
from typing import Any

# Closed lists — single source of truth lives in the service mixins. Importing
# (rather than re-declaring) means a future standard amendment that edits a
# closed list cannot silently desync the detector from the validator.
from service_adapts import ADAPT_STATUSES, FINDING_CATEGORIES, SIGNATURE_ROLES
from service_specs import SPEC_STATUSES, SPEC_TYPES

Finding = dict[str, str]


def _finding(detector: str, kind: str, ref: str, message: str) -> Finding:
    return {
        "detector": detector,
        "kind": kind,
        "severity": "warn",
        "ref": ref,
        "message": message,
    }


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Run a read-only query, returning dict rows. [] if the table is absent.

    Older DBs predate the specs/adapts migrations; a missing table raises
    OperationalError ("no such table") which we treat as "nothing to validate"
    rather than an error — the detector is forward-looking.
    """
    try:
        cur = conn.execute(sql, params)
    except sqlite3.OperationalError as e:
        # Only "no such table" is the expected forward-looking no-op. A real SQL
        # error (bad column, typo) must propagate so the gate's degrade-to-skip
        # surfaces "drift check unavailable" instead of silently reporting clean.
        if "no such table" in str(e).lower():
            return []
        raise
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


# --- drift-1: schema drift --------------------------------------------------


def detect_schema_drift(conn: sqlite3.Connection) -> list[Finding]:
    """Re-validate specs + adapts against closed lists + cross-field invariants."""
    findings: list[Finding] = []
    det = "drift-1-schema"

    for s in _rows(conn, "SELECT slug, type, status, version, title FROM specs"):
        ref = f"spec:{s['slug']}"
        if s["type"] not in SPEC_TYPES:
            findings.append(
                _finding(det, "spec-type-invalid", ref, f"type {s['type']!r} not in closed-9")
            )
        if s["status"] not in SPEC_STATUSES:
            findings.append(
                _finding(det, "spec-status-invalid", ref, f"status {s['status']!r} not in closed-3")
            )
        if _blank(s["version"]):
            findings.append(_finding(det, "spec-version-missing", ref, "version is empty"))
        if _blank(s["title"]):
            findings.append(_finding(det, "spec-title-missing", ref, "title is empty"))

    # Pre-load signature roles per adapt so the signed↔dual-signature check is a
    # single query, not N+1.
    sig_roles: dict[str, set[str]] = {}
    for r in _rows(conn, "SELECT adapt_slug, role FROM adapt_signatures"):
        sig_roles.setdefault(r["adapt_slug"], set()).add(r["role"])
        if r["role"] not in SIGNATURE_ROLES:
            findings.append(
                _finding(
                    det,
                    "signature-role-invalid",
                    f"adapt:{r['adapt_slug']}",
                    f"signature role {r['role']!r} not in {SIGNATURE_ROLES}",
                )
            )

    for a in _rows(conn, "SELECT slug, status, parent_adapt, delta_n FROM adapts"):
        ref = f"adapt:{a['slug']}"
        if a["status"] not in ADAPT_STATUSES:
            findings.append(
                _finding(
                    det, "adapt-status-invalid", ref, f"status {a['status']!r} not in closed-3"
                )
            )
        # delta_n is SQLite-dynamic-typed; tolerate a numeric TEXT '2'. A truly
        # non-numeric value is itself drift — emit a finding instead of crashing
        # the detector (drift-1 exists to surface exactly this corruption). On
        # failure delta_n is None: skip the delta-relationship checks but still
        # run the signature check below — corruptions can co-occur.
        try:
            delta_n: int | None = int(a["delta_n"] or 0)
        except (ValueError, TypeError):
            findings.append(
                _finding(
                    det, "adapt-delta-invalid", ref, f"delta_n {a['delta_n']!r} is not an integer"
                )
            )
            delta_n = None
        if delta_n is not None:
            if delta_n < 0:
                findings.append(
                    _finding(det, "adapt-delta-negative", ref, f"delta_n={delta_n} < 0")
                )
            elif delta_n > 0 and not a["parent_adapt"]:
                findings.append(
                    _finding(
                        det,
                        "adapt-delta-orphan",
                        ref,
                        f"delta_n={delta_n} but parent_adapt is NULL",
                    )
                )
            elif delta_n == 0 and a["parent_adapt"]:
                findings.append(
                    _finding(
                        det,
                        "adapt-base-has-parent",
                        ref,
                        f"base adapt (delta_n=0) chains parent {a['parent_adapt']!r}",
                    )
                )
        if a["status"] == "signed":
            have = sig_roles.get(a["slug"], set())
            missing = set(SIGNATURE_ROLES) - have
            if missing:
                findings.append(
                    _finding(
                        det,
                        "adapt-signed-incomplete-signature",
                        ref,
                        f"status=signed but missing dual signature: {sorted(missing)}",
                    )
                )

    for f in _rows(conn, "SELECT adapt_slug, category FROM adapt_findings"):
        if f["category"] not in FINDING_CATEGORIES:
            findings.append(
                _finding(
                    det,
                    "finding-category-invalid",
                    f"adapt:{f['adapt_slug']}",
                    f"finding category {f['category']!r} not in closed-7",
                )
            )

    return findings


# --- drift-7: TC↔requirement provenance drift -------------------------------


def detect_provenance_drift(conn: sqlite3.Connection) -> list[Finding]:
    """Detect stale task↔SPEC verification provenance.

    ISO timestamps are UTC and lexicographically ordered, so a string ``>``
    compare on (spec.updated_at, link.created_at) is a valid recency test; the
    compare is strict, so a spec linked and last-edited in the same instant
    (updated_at == created_at) is NOT flagged. ``stale-verification`` is scoped
    to ``active`` specs only — a spec deprecated after a task finished is a
    settled requirement, not a stale verification (it would otherwise double-
    report alongside ``deprecated-requirement`` for in-flight tasks).
    """
    findings: list[Finding] = []
    det = "drift-7-provenance"

    stale = _rows(
        conn,
        """
        SELECT ts.task_slug AS task, ts.spec_slug AS spec,
               ts.created_at AS linked_at, s.updated_at AS spec_updated,
               s.version AS spec_version
          FROM task_specs ts
          JOIN specs s ON s.slug = ts.spec_slug
          JOIN tasks t ON t.slug = ts.task_slug
         WHERE t.status = 'done'
           AND s.status = 'active'
           AND s.updated_at > ts.created_at
        """,
    )
    for r in stale:
        findings.append(
            _finding(
                det,
                "stale-verification",
                f"task:{r['task']}->spec:{r['spec']}",
                (
                    f"done task verified against SPEC {r['spec']} linked {r['linked_at']}, "
                    f"but SPEC was edited {r['spec_updated']} (now {r['spec_version']}) — "
                    "verification predates current requirement version"
                ),
            )
        )

    deprecated = _rows(
        conn,
        """
        SELECT ts.task_slug AS task, ts.spec_slug AS spec, t.status AS task_status
          FROM task_specs ts
          JOIN specs s ON s.slug = ts.spec_slug
          JOIN tasks t ON t.slug = ts.task_slug
         WHERE s.status = 'deprecated'
           AND t.status != 'done'
        """,
    )
    for r in deprecated:
        findings.append(
            _finding(
                det,
                "deprecated-requirement",
                f"task:{r['task']}->spec:{r['spec']}",
                (
                    f"in-flight task ({r['task_status']}) links deprecated SPEC {r['spec']} — "
                    "work proceeding against a retired requirement"
                ),
            )
        )

    return findings


# --- aggregate + formatting --------------------------------------------------

_DETECTORS = {
    "schema": detect_schema_drift,
    "provenance": detect_provenance_drift,
}


def run_detector(conn: sqlite3.Connection, which: str) -> list[Finding]:
    """Run one detector by short name ('schema' | 'provenance')."""
    fn = _DETECTORS.get(which)
    if fn is None:
        raise ValueError(f"Unknown drift detector {which!r}. Valid: {sorted(_DETECTORS)}")
    return fn(conn)


def run_all(conn: sqlite3.Connection) -> list[Finding]:
    """Run every implemented detector and return the combined findings."""
    out: list[Finding] = []
    for fn in _DETECTORS.values():
        out.extend(fn(conn))
    return out


def format_findings(findings: list[Finding]) -> str:
    """One-line-per-finding human summary (laconic, for gate/CLI output)."""
    if not findings:
        return "No RENAR drift detected."
    lines = [f"{len(findings)} RENAR drift finding(s):"]
    for f in findings:
        lines.append(f"  [{f['detector']}/{f['kind']}] {f['ref']}: {f['message']}")
    return "\n".join(lines)
