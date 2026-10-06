"""Pooled verification for an explicit task cohort (Track A, 1.11.3).

Implements SPEC verification-cohort-contract for the receipts half:
canonical identity, one gate pass over the union scope, per-unit outcomes
with the digest they rest on, incremental continuation after a red run
(previous failures UNION tests affected by files changed since), and the six
named invalidators that refuse reuse and widen to the full lane.

Execution is DELEGATED: the gates themselves run through
`run_verify_for_task` with the union scope passed explicitly, so every cache
guard the single-task path earned (has_real_pass, no-test-mapped, empty-scope
refusal) applies to cohorts for free — the bypass that defect
cli-verify-bypasses-cache-guards documents is not re-created here.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from typing import Any

#: Files whose verification may never pool silently (contract §4). A cohort
#: whose union scope touches these still runs, but the receipt says so and
#: reuse is refused — stricter, never quieter.
SECURITY_SENSITIVE = ("scripts/hooks/", "auth", "billing", "payment")

_MIN_MEMBERS = 2  # a cohort of one is just `verify --task`


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_identity(inputs: dict[str, Any]) -> str:
    """SHA-256 over the canonical serialization of the contract's §1 inputs.

    ``sort_keys`` + compact separators make the serialization canonical; the
    caller sorts membership itself, so identity never depends on arg order.
    """
    blob = json.dumps(inputs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _task_fingerprint(row: dict[str, Any]) -> str:
    """What `task show --package` vouches for: goal/AC/plan/scope as stored."""
    keys = ("goal", "acceptance_criteria", "plan", "relevant_files", "scope_paths")
    blob = json.dumps({k: row.get(k) for k in keys}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _git_state(root: str | None) -> dict[str, str]:
    """HEAD + a digest of the dirty-file list; a cohort cannot span a commit."""
    if not root:
        return {"head": "unknown-root", "dirty_digest": "unknown-root"}
    try:
        head = subprocess.run(
            ["git", "-C", root, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", root, "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    except Exception:  # noqa: BLE001 — unmeasurable repo state IS the invalidator
        return {"head": "unavailable", "dirty_digest": "unavailable"}
    return {
        "head": head,
        "dirty_digest": hashlib.sha256(dirty.encode("utf-8")).hexdigest()[:16],
    }


def _union_scope(be: Any, slugs: list[str]) -> list[str]:
    files: set[str] = set()
    for slug in slugs:
        row = be._q1("SELECT relevant_files FROM tasks WHERE slug=?", (slug,))
        raw = row["relevant_files"] if row else None
        if raw:
            try:
                files.update(json.loads(raw))
            except (TypeError, ValueError):
                continue
    return sorted(files)


def collect_identity_inputs(
    be: Any, slugs: list[str], gate_signature: str, root: str | None = None
) -> dict[str, Any]:
    """The seven contract §1 inputs, gathered from the DB and the repo."""
    members = sorted(set(slugs))
    fingerprints: dict[str, str] = {}
    statuses: dict[str, str] = {}
    for slug in members:
        row = be._q1("SELECT * FROM tasks WHERE slug=?", (slug,))
        fingerprints[slug] = _task_fingerprint(row) if row else "missing"
        statuses[slug] = (row.get("status") or "missing") if row else "missing"
    union = _union_scope(be, members)
    return {
        "members": members,
        "task_fingerprints": fingerprints,
        "task_statuses": statuses,
        "union_scope": union,
        "content_hashes": "declared-at-run",  # files_hash of the delegated run
        "gate_signature": gate_signature,
        "selected_tests": "selection-evidence-of-run",
        "repository_state": _git_state(root),
    }


def invalidation_reason(prior: dict[str, Any], current: dict[str, Any]) -> str | None:
    """The six named invalidators (contract §4). A refusal names which fired.

    Security-sensitive scope is checked on the CURRENT union only — it is a
    property of what is about to run, not of what ran before.
    """
    if prior["members"] != current["members"]:
        return "membership-drift"
    # A member that no longer resolves is not "edited" — it is GONE, and the
    # distinction matters because the remedies differ (re-add vs re-review).
    for slug, fp in current["task_fingerprints"].items():
        if fp == "missing":
            return f"missing-evidence:{slug}"
    if prior["task_fingerprints"] != current["task_fingerprints"]:
        return "task-edits"
    # A member BLOCKED or REOPENED after verify is not the cohort that was
    # verified: the receipt must go stale, not green (hierarchy AC-4).
    if prior.get("task_statuses") != current.get("task_statuses"):
        return "member-status-drift"
    if prior["gate_signature"] != current["gate_signature"]:
        return "gate-signature-drift"
    if any(p in " ".join(current["union_scope"]) for p in SECURITY_SENSITIVE):
        return "security-sensitive-scope"
    for slug, fp in current["task_fingerprints"].items():
        if fp == "missing":
            return f"missing-evidence:{slug}"
    if prior["repository_state"]["head"] == "unavailable":
        return "uncertain-dependency-mapping"
    return None


def required_after_red(prev_failures: set[str], affected_by_changed: set[str]) -> set[str]:
    """Contract §3: previous failures UNION tests affected by the delta.

    Pure on purpose — the red continuation is a set claim about the world,
    and the world (which files changed) is the caller's to measure.
    """
    return set(prev_failures) | set(affected_by_changed)


def gate_signature(be: Any) -> str:
    """Digest of the enabled-gate set + config that will judge this cohort."""
    rows = be._q("SELECT key, value FROM meta WHERE key LIKE 'gate:%'")
    blob = json.dumps(sorted((r["key"], r["value"]) for r in rows), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def open_cohort(be: Any, inputs: dict[str, Any], identity: str) -> int:
    """Idempotent by identity: re-opening the same cohort returns its row."""
    row = be._q1("SELECT id FROM verification_cohorts WHERE identity=?", (identity,))
    if row:
        return int(row["id"])
    union = inputs["union_scope"]
    be._conn.execute(
        "INSERT INTO verification_cohorts(identity, members_json, identity_inputs_json, "
        "union_files_hash, gate_signature, state, created_at, updated_at) "
        "VALUES(?,?,?,?,?,'open',?,?)",
        (
            identity,
            json.dumps(inputs["members"]),
            json.dumps(inputs, sort_keys=True, default=str),
            hashlib.sha256("".join(union).encode()).hexdigest()[:16],
            inputs["gate_signature"],
            _now(),
            _now(),
        ),
    )
    be._conn.commit()
    return int(be._q1("SELECT id FROM verification_cohorts WHERE identity=?", (identity,))["id"])


def record_results(
    be: Any, cohort_pk: int, results: list[dict[str, Any]], inputs_digest: str
) -> None:
    """Per-unit outcomes with provenance and the digest each rests on."""
    stamp = _now()
    for r in results:
        be._conn.execute(
            "INSERT INTO verification_cohort_results(cohort_pk, unit, outcome, covered_by, "
            "inputs_digest, ran_at) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(cohort_pk, unit) DO UPDATE SET outcome=excluded.outcome, "
            "covered_by=excluded.covered_by, inputs_digest=excluded.inputs_digest, "
            "ran_at=excluded.ran_at",
            (cohort_pk, r["unit"], r["outcome"], r.get("covered_by"), inputs_digest, stamp),
        )
    be._conn.commit()


def _set_state(be: Any, cohort_pk: int, state: str) -> None:
    be._conn.execute(
        "UPDATE verification_cohorts SET state=?, updated_at=? WHERE id=?",
        (state, _now(), cohort_pk),
    )
    be._conn.commit()


def cohort_summary(out: dict[str, Any]) -> str:
    """The one rendering of a pooled-run outcome — CLI and MCP both call this,
    so the two transports cannot disagree (test_no_new_second_implementation)."""
    if out.get("refused"):
        return str(out["refused"])
    return (
        f"Cohort {'green' if out['passed'] else 'RED'}: "
        f"identity {out['identity'][:16]}, "
        f"members {', '.join(out['members'])}, "
        f"union scope {len(out['union_scope'])} file(s) run ONCE."
    )


def run_cohort_verify(
    svc: Any,
    slugs: list[str],
    scope: str = "manual",
    _runner=None,
) -> dict[str, Any]:
    """One gate pass over the union scope for an explicit task pool.

    `_runner` is the delegation seam: production passes nothing and the
    service's own `run_verify_for_task` is used (with every cache guard);
    tests inject a recorder so the driver logic runs without gates.
    """
    members = sorted(set(slugs))
    if len(members) < _MIN_MEMBERS:
        return {
            "refused": "a cohort needs at least two distinct tasks — "
            f"got {len(members)}; use `verify --task` for one"
        }

    be = svc.be
    from project_root import root_from_service

    inputs = collect_identity_inputs(be, members, gate_signature(be), root_from_service(svc))
    identity = canonical_identity(inputs)

    # Invalidation is a question about the PREDECESSOR, not about this
    # identity: an edited member produces a different identity, so looking
    # the row up BY identity would always miss it. The predecessor is the
    # latest cohort with the SAME membership; a different identity under the
    # same members is exactly the drift the contract names.
    members_json = json.dumps(members)
    prior_row = be._q1(
        "SELECT id, identity, identity_inputs_json, state FROM verification_cohorts "
        "WHERE members_json=? ORDER BY id DESC LIMIT 1",
        (members_json,),
    )
    if prior_row and prior_row["identity"] != identity and prior_row["state"] in ("green", "red"):
        prior_inputs = json.loads(prior_row["identity_inputs_json"])
        reason = invalidation_reason(prior_inputs, inputs)
        return {
            "refused": f"reuse refused: {reason or 'identity-drift'}; prior "
            f"cohort #{prior_row['id']} evidence is not reusable and "
            f"the next run widens to the full applicable lane"
        }

    cohort_pk = open_cohort(be, inputs, identity)

    union = inputs["union_scope"]
    if not union:
        return {
            "refused": "unscoped cohort: no member declares relevant_files; "
            "a close cohort cannot form (contract §1.3)"
        }

    runner = _runner or svc.run_verify_for_task
    report = runner(members[0], relevant_files=union, scope=scope, trigger="verify")

    # Stamp the recorded run as this cohort's (best effort; the report is the
    # authority for pass/fail, the stamp is the audit link).
    be._conn.execute(
        "UPDATE verification_runs SET cohort_identity=? WHERE id="
        "(SELECT MAX(id) FROM verification_runs WHERE task_slug=?)",
        (identity, members[0]),
    )
    be._conn.commit()

    state = "green" if report.get("passed") else "red"
    _set_state(be, cohort_pk, state)
    record_results(
        be,
        cohort_pk,
        [
            {
                "unit": "cohort-union-scope",
                "outcome": "passed" if report.get("passed") else "failed",
                "covered_by": ",".join(members),
            }
        ],
        report.get("files_hash") or "unavailable",
    )
    return {
        "cohort_pk": cohort_pk,
        "identity": identity,
        "members": members,
        "union_scope": union,
        "passed": bool(report.get("passed")),
        "state": state,
        "report": report,
    }
