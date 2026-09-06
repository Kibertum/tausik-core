"""RENAR drift detectors — drift-1 (schema) + drift-7 (TC↔requirement provenance).

RENAR §4.11 defines 8 classes of drift a conformant substrate must detect.
This module implements 2 of them as **warning-mode** read-only detectors over
TAUSIK's own RENAR artifact store (specs / adapts / task↔spec links):

  * **drift-1 — schema drift** (§4.11.1): a stored artifact violates a schema
    invariant. DB CHECK constraints catch enum membership *at insert time*, but
    cannot express cross-field rules (delta_n ↔ parent_adapt, signed ↔ dual
    signature) and do not re-validate legacy rows after a migration tightens the
    schema. This detector re-validates every row against the canonical closed
    lists + cross-field invariants, so direct-DB tampering or a migration gap
    surfaces instead of silently passing.

  * **drift-7 — TC↔requirement provenance drift** (§4.11.7): a verification's
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
fitting) are out of scope for this task — see RENAR §4.11 and docs/audit.
"""

from __future__ import annotations

import sqlite3
from typing import Any

# Closed lists — single source of truth lives in the service mixins. Importing
# (rather than re-declaring) means a future standard amendment that edits a
# closed list cannot silently desync the detector from the validator.
from service_adapts import (
    ADAPT_STATUSES,
    FINDING_CATEGORIES,
    HISTORICAL_SIGNATURE_ROLES,
    SIGNATURE_ROLES,
)
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
                _finding(
                    det,
                    "spec-type-invalid",
                    ref,
                    f"type {s['type']!r} not in the closed {len(SPEC_TYPES)}",
                )
            )
        if s["status"] not in SPEC_STATUSES:
            findings.append(
                _finding(
                    det,
                    "spec-status-invalid",
                    ref,
                    f"status {s['status']!r} not in the closed {len(SPEC_STATUSES)}",
                )
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
        if r["role"] == "client":
            # NAMED, NOT DELETED. ADR-011 withdrew the client signature under
            # ADAPT, and §7.5 now explains its absence — but a signature already
            # recorded is an audit record, and V1 forbids erasing it. So the row
            # survives and this says what it is: a record made under a norm the
            # standard has since withdrawn. Silence here would let a consumer's
            # database go on looking conformant with a rule that no longer exists.
            findings.append(
                _finding(
                    det,
                    "signature-role-withdrawn",
                    f"adapt:{r['adapt_slug']}",
                    "client signature recorded under a norm RENAR ADR-011 withdrew "
                    "(§7.5 now names the architect alone); the record is kept as "
                    "audit history and must not be rewritten — what the client "
                    "approves belongs in an ACTZ",
                )
            )
        elif r["role"] not in HISTORICAL_SIGNATURE_ROLES:
            findings.append(
                _finding(
                    det,
                    "signature-role-invalid",
                    f"adapt:{r['adapt_slug']}",
                    f"signature role {r['role']!r} not in {HISTORICAL_SIGNATURE_ROLES}",
                )
            )

    for a in _rows(conn, "SELECT slug, status, parent_adapt, delta_n FROM adapts"):
        ref = f"adapt:{a['slug']}"
        if a["status"] not in ADAPT_STATUSES:
            findings.append(
                _finding(
                    det,
                    "adapt-status-invalid",
                    ref,
                    f"status {a['status']!r} not in the closed {len(ADAPT_STATUSES)}",
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
        if a["status"] == "approved":
            have = sig_roles.get(a["slug"], set())
            missing = set(SIGNATURE_ROLES) - have
            if missing:
                findings.append(
                    _finding(
                        det,
                        "adapt-approved-incomplete-signature",
                        ref,
                        f"status=approved but missing signature: {sorted(missing)} (§7.5)",
                    )
                )

    for f in _rows(conn, "SELECT adapt_slug, category FROM adapt_findings"):
        if f["category"] not in FINDING_CATEGORIES:
            findings.append(
                _finding(
                    det,
                    "finding-category-invalid",
                    f"adapt:{f['adapt_slug']}",
                    f"finding category {f['category']!r} not in the closed {len(FINDING_CATEGORIES)}",
                )
            )

    return findings


# --- drift-7: TC↔requirement provenance drift -------------------------------


def detect_provenance_drift(conn: sqlite3.Connection) -> list[Finding]:
    """Detect stale task↔SPEC verification provenance.

    THE OPERAND, NOT THE ARITHMETIC, WAS WRONG (Sortula #49, our #10). This
    used to compare ``spec.updated_at`` against ``link.created_at`` and called
    that "a valid recency test". The claim is true about STRINGS and false
    about MEANING: ``task_specs.created_at`` is when the task was LINKED to the
    requirement, and it says nothing about when the task was verified. A task
    finished a day AFTER a SPEC edit was therefore declared stale, and the gate
    failed on every single ``task done``. Worse than noise: the false positive
    MASKED a real one, which surfaced at the consumer only once this was fixed.

    The honest reference point already existed in the schema — nothing here is
    invented: ``verification_runs.ran_at`` is when the task was ACTUALLY
    verified, which is precisely what this detector's name claims to be about.

    THE FALLBACK IS NAMED, NOT IMPLIED (a task with no verification run at
    all): ``tasks.completed_at`` — an honest second approximation, because a
    task cannot have been verified after it was closed. Falling back to
    ``link.created_at`` is FORBIDDEN: it is not a worse approximation, it is
    not an approximation of verification time at all, and reinstating it would
    return this defect wearing compatibility's clothes.

    A row datable by NEITHER is reported separately as ``undateable-
    verification`` rather than passing quietly. Silence there would be the very
    reading this release exists to remove: "could not be checked" is not
    "checked and fine" (SENAR 1.4 §8.6(e)).

    ISO timestamps are UTC and lexicographically ordered, so the string ``>``
    compare remains a valid recency test on the NEW operand. The compare stays
    STRICT, deliberately and unchanged: a spec verified and last-edited in the
    same instant is NOT flagged. ``stale-verification`` is scoped to ``active``
    specs only — a spec deprecated after a task finished is a settled
    requirement, not a stale verification (it would otherwise double-report
    alongside ``deprecated-requirement`` for in-flight tasks).
    """
    findings: list[Finding] = []
    det = "drift-7-provenance"

    # When the task was actually verified: the latest recorded run, else the
    # moment it was closed. Spelled once and reused by both queries so the
    # filter and the reported value can never disagree.
    _VERIFIED_AT = (
        "COALESCE("
        "(SELECT MAX(vr.ran_at) FROM verification_runs vr WHERE vr.task_slug = ts.task_slug),"
        " t.completed_at)"
    )

    stale = _rows(
        conn,
        f"""
        SELECT ts.task_slug AS task, ts.spec_slug AS spec,
               {_VERIFIED_AT} AS verified_at, s.updated_at AS spec_updated,
               s.version AS spec_version
          FROM task_specs ts
          JOIN specs s ON s.slug = ts.spec_slug
          JOIN tasks t ON t.slug = ts.task_slug
         WHERE t.status = 'done'
           AND s.status = 'active'
           AND {_VERIFIED_AT} IS NOT NULL
           AND s.updated_at > {_VERIFIED_AT}
        """,
    )
    for r in stale:
        findings.append(
            _finding(
                det,
                "stale-verification",
                f"task:{r['task']}->spec:{r['spec']}",
                (
                    f"done task last verified {r['verified_at']} against SPEC {r['spec']}, "
                    f"but SPEC was edited {r['spec_updated']} (now {r['spec_version']}) — "
                    "verification predates current requirement version"
                ),
            )
        )

    # Datable by neither a run nor a close time. Reported, not skipped: the
    # detector cannot say this verification is current, and saying nothing
    # would read as saying it is fine.
    undateable = _rows(
        conn,
        f"""
        SELECT ts.task_slug AS task, ts.spec_slug AS spec
          FROM task_specs ts
          JOIN specs s ON s.slug = ts.spec_slug
          JOIN tasks t ON t.slug = ts.task_slug
         WHERE t.status = 'done'
           AND s.status = 'active'
           AND {_VERIFIED_AT} IS NULL
        """,
    )
    for r in undateable:
        findings.append(
            _finding(
                det,
                "undateable-verification",
                f"task:{r['task']}->spec:{r['spec']}",
                (
                    "done task has neither a recorded verification run nor a completion "
                    f"time, so its verification against SPEC {r['spec']} cannot be dated — "
                    "provenance is unknown, not current"
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


# --- check-adapt-supersession: §10.11.1 control point, ADR-007's named gate ---

# The status a superseded ADAPT carries. Spelled once here and checked against
# the closed list by a test rather than by an `assert` at import: a value that
# drifts out of ADAPT_STATUSES must be a red test, not a production exception.
SUPERSEDED_STATUS = "superseded"


def detect_supersession_drift(conn: sqlite3.Connection) -> list[Finding]:
    """Detect supersession state that the substrate's own guards cannot express.

    ADR-007 promised a gate called `check-adapt-supersession` and §10.11.1
    (p.485) names the control point; neither existed. The task that carried this
    debt described the subject as a dangling `source.adapt` on a SPEC — and that
    subject does not exist: `specs` has none of the three provenance columns,
    and owner decision #307 rules that none will be added. A gate over a field
    that cannot hold a value is the degenerate control this release is spent
    removing, so THAT half is declared inapplicable
    (`renar_normative_inapplicability`) instead of being built.

    THE SUBJECT THAT DOES EXIST was found by reading the schema rather than the
    task title: `adapts.parent_adapt` is a foreign key from one ADAPT to
    another — a delta-ADAPT naming its parent (§7.6). Zero such rows exist
    today, and that is not the same as no subject: a column that exists can be
    filled tomorrow, a column that does not exist cannot.

    WHAT IS DELIBERATELY NOT CHECKED, and why (an inventory, not an oversight):

    * A `parent_adapt` naming an ADAPT that is not there. The runtime connection
      sets `PRAGMA foreign_keys=ON` (project_backend), and the state-import path
      already scans `PRAGMA foreign_key_list` for orphans. Re-checking it here
      would be a second source of truth for a guarantee that already holds.
    * That a NEW supersession carries a rationale. `backend_crud_adapts`
      refuses that write at the lowest primitive. What a primitive cannot do is
      repair rows already written — under an older schema, or by a rebuild
      migration that runs with foreign keys off — which is exactly what a
      detector over existing state is for, so the STATE is checked here while
      the WRITE stays guarded there.

    A missing `adapts` table is a forward-looking no-op (`_rows`). A missing
    `parent_adapt` COLUMN is not: it propagates, the gate degrades to
    could-not-run, and the reader is told the check did not happen. "Could not
    be checked" is not "checked and fine" (SENAR 1.4 §8.6(e)).
    """
    findings: list[Finding] = []
    det = "check-adapt-supersession"

    orphaned = _rows(
        conn,
        "SELECT c.slug AS child, c.parent_adapt AS parent, c.delta_n AS delta_n "
        "FROM adapts c JOIN adapts p ON p.slug = c.parent_adapt "
        "WHERE p.status = ? ORDER BY c.slug",
        (SUPERSEDED_STATUS,),
    )
    for row in orphaned:
        findings.append(
            _finding(
                det,
                "delta-of-superseded-parent",
                str(row["child"]),
                f"delta-ADAPT (delta_n={row['delta_n']}) names parent "
                f"{row['parent']!r}, which is {SUPERSEDED_STATUS} — §10.11.1: a "
                "change-set may not hang off a withdrawn ADAPT.",
            )
        )

    for row in _rows(
        conn,
        "SELECT slug, supersession_rationale FROM adapts WHERE status = ? ORDER BY slug",
        (SUPERSEDED_STATUS,),
    ):
        if _blank(row["supersession_rationale"]):
            findings.append(
                _finding(
                    det,
                    "supersession-without-rationale",
                    str(row["slug"]),
                    f"status is {SUPERSEDED_STATUS} with no rationale recorded — "
                    "the write path refuses this today, so the row predates the "
                    "guard or was written around it.",
                )
            )

    return findings


# --- aggregate + formatting --------------------------------------------------

_DETECTORS = {
    "schema": detect_schema_drift,
    "provenance": detect_provenance_drift,
    "supersession": detect_supersession_drift,
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
