"""RENAR-CONFORMANCE.yaml self-assessment generator (v16r-conformance-yaml).

Generates a RENAR conformance manifest (§13.4.2) whose level is computed
**honestly from live DB state**, never declared. The RENAR adoption audit — a
document the corpus no longer carries, so it is cited by name rather than by an
anchor that cannot resolve — found kai's hand-written manifest stuck at
pre-adoption; deriving every signal from the DB keeps the claim from drifting
from reality.

Honesty contract (§13.4.3): a level is claimed only when ALL seven mandatory
clauses (§13.3) hold AND every observable signal that level requires
(§11.4.3–§11.8.2) is met on real data. One unmet clause yields
``pre_adoption: true`` + ``level: null`` rather than an overstatement — a level
below RENAR-1 is not in the closed list, so "not yet conformant" is expressed as
pre-adoption. Ahead of all of that sits the §1.5 applicability precondition: see
SCOPE_EXCLUSION.

Machinery vs data: some clauses are *capabilities* the running framework
guarantees (V1–V6 over git+sqlite, task-before-code and verify-first); others
are *data* facts measured on the rows and the schema in hand (reactive ADAPT,
the closed lists as the substrate's CHECK constraints enforce them); one is
judged over the manifest's own quality-gates declaration; one is vacuous. The
basis of each verdict is published beside it — see renar_mandatory_clauses —
and any confirmation the measurer has NOT earned is disclosed separately in
renar_measurer_caveats.

Read-only: queries the DB, never writes (the CLI's optional --write touches only
RENAR-CONFORMANCE.yaml at the project root).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any


from renar_clause_reactive_adapt import assess as assess_reactive_adapt

# Serialization split out for the filesize gate; re-exported so every existing
# `from renar_conformance import ...` keeps working -- renar_export takes
# _require_yaml from here, and the test module takes render_yaml plus
# MANDATORY_FIELDS. (project_cli_renar used to take render_yaml too, to
# re-render a manifest after patching `replaces` onto it; it now passes the
# link into `generate` and renders once.)
from renar_conformance_yaml import (  # noqa: F401
    MANDATORY_FIELDS,
    _require_yaml,
    render_yaml,
)
from renar_clause_closed_lists import assess_closed_lists, assess_spec_types
from renar_mandatory_clauses import (  # noqa: F401 — eval_mandatory_clauses is re-exported
    QUALITY_GATES_DECLARED,
    basis_section,
    eval_mandatory_clauses,
)
from renar_measurer_caveats import caveats_section
from renar_normative_inapplicability import section as inapplicability_section
from renar_tc_premise import pairing_clause
from service_specs import SPEC_TYPES

# v1.1 since session #250 (decision #364): the corpus moved to v1.1 at c3dd6b0 and
# §13.4.3 makes a minor edition a re-assessment trigger; the eighth clause
# §13.3.8 is assessed in renar_br_premise.
RENAR_VERSION = "1.1"
SENAR_VERSION = "1.3"

# Derived from the canonical closed list (single source) → "SPEC-<TYPE>" labels.
SPEC_TYPES_SUPPORTED = [f"SPEC-{t}" for t in SPEC_TYPES]

# Observable-signal keys required at each level, cumulative (§11.4.3 RENAR-1,
# §11.5.3 RENAR-2, §11.6.2 RENAR-3, §11.7.2 RENAR-4, §11.8.2 RENAR-5). A
# level is reachable only when every key for it and all lower levels is met.
# Keys map to booleans produced by gather_signals(); see _LEVEL_REQUIRED.
_LEVEL_REQUIRED: dict[str, list[str]] = {
    "RENAR-1": ["substrate_v1_v6", "adapt_per_tz"],
    "RENAR-2": ["frontmatter_structured", "tz_immutable", "delta_tz_artifact"],
    "RENAR-3": [
        "schema_validation_hook",
        "lifecycle_statuses_used",
        "coverage_autogen",
        "reference_validation_hook",
        "verifies_version_pin",
        "qg0_enforced",
    ],
    "RENAR-4": [
        "verified_by_100pct",
        "pos_neg_pairing",
        "qg2_enforced",
        "ai_provenance",
        "source_citation",
        "continuous_reconciliation",
    ],
    "RENAR-5": [
        "adversarial_gate",
        "multi_model_must",
        "knowledge_graph_primary",
        "hallucination_rate_tracked",
    ],
}
_LEVEL_ORDER = ["RENAR-1", "RENAR-2", "RENAR-3", "RENAR-4", "RENAR-5"]

# --- §1.5 applicability precondition (scope, not signals) -------------------
# A conformance level has TWO conditions, and they live in different documents.
# The VALUE — do the signals hold? — lives in our own data and is read here.
# The RIGHT — is this project inside the standard's scope of application at
# all? — lives in the standard's §1.5. A generator that reads only its own data
# sees the first and is blind to the second BY CONSTRUCTION. That blindness is
# what put a fact into an external tracker that had to be withdrawn an hour
# later (session #198). So the right is evaluated FIRST, ahead of the ladder.
#
# Set to None the moment the exclusion stops holding (an ACTZ signed by two
# independent persons appears → §1.5.4 itself routes the project into §1.4.2).
# Do not weaken it any other way: §13.9.2 forbids claiming a level above the
# one actually held, and a level claimed outside §1.5 is not "above" — it is
# not a claim the standard recognises at all.
SCOPE_EXCLUSION: dict[str, str] | None = {
    "clause": "§1.5.4",
    "scenario": "Internal product без external client",
    "finding": (
        "no independent client representative exists, so the two-party ACTZ "
        "signature (§5.5.3) is structurally impossible; §1.5.4 withholds the "
        "right to claim RENAR-N and requires the manifest to declare "
        "non-conformance explicitly"
    ),
    "decided-in": "decisions#292",
    "supersedes": (
        "decisions#109 core-mode — the mechanism it rested on was removed by "
        "ADR-005; zero occurrences remain in standard/, guide/, reference/"
    ),
}

# §13.8.2 step 2 sentinel. Borrowed as the ENCODING for "no level is held" —
# the §13.4.2 schema offers no other representation. NOT a claim that the
# §13.8 loss-of-conformance procedure was executed: this is the withdrawal of
# a claim made outside the scope of applicability, not the downgrade of a
# claim once validly held.
UNKNOWN_STATE_SENTINEL = "<unknown-state>"


def scope_exclusion() -> dict[str, str] | None:
    """The §1.5 exclusion in force, or None when the project is in scope."""
    return dict(SCOPE_EXCLUSION) if SCOPE_EXCLUSION else None


def _scalar(conn: sqlite3.Connection, sql: str) -> int:
    """COUNT-style scalar query; 0 if the table is absent (forward-looking)."""
    try:
        row = conn.execute(sql).fetchone()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            import sys

            print(f"# renar conformance: skipped (table absent): {sql}", file=sys.stderr)
            return 0
        raise
    return int(row[0]) if row and row[0] is not None else 0


def gather_signals(conn: sqlite3.Connection) -> dict[str, Any]:
    """Collect raw counts + derived level-signal booleans from the live DB.

    Capability signals (schema_validation_hook, qg*_enforced, closed lists,
    knowledge_graph, adversarial_gate) reflect TAUSIK machinery that exists
    regardless of artifact data; data signals are derived from actual rows.
    """
    specs = _scalar(conn, "SELECT COUNT(*) FROM specs")
    # Actively transitioned specs — at least one out of the initial 'draft'
    # state. The bare "status IN (closed-set)" is a tautology (DB CHECK already
    # guarantees it); §11.6.2 wants statuses *used*, i.e. real transitions.
    specs_transitioned = _scalar(conn, "SELECT COUNT(*) FROM specs WHERE status != 'draft'")
    adapts = _scalar(conn, "SELECT COUNT(*) FROM adapts")
    adapts_approved = _scalar(conn, "SELECT COUNT(*) FROM adapts WHERE status='approved'")
    # Non-superseded delta-ADAPT — a superseded delta is not a current change-set (§7.6).
    deltas = _scalar(
        conn, "SELECT COUNT(*) FROM adapts WHERE delta_n > 0 AND status != 'superseded'"
    )
    task_specs = _scalar(conn, "SELECT COUNT(*) FROM task_specs")
    reasoning = _scalar(conn, "SELECT COUNT(DISTINCT task_slug) FROM reasoning_steps")
    mem_edges = _scalar(conn, "SELECT COUNT(*) FROM memory_edges")
    verifs = _scalar(conn, "SELECT COUNT(*) FROM verification_runs")
    clause_333 = assess_reactive_adapt(conn)
    clause_335 = pairing_clause(conn)

    raw = {
        "specs_count": specs,
        "adapts_count": adapts,
        "adapts_approved_count": adapts_approved,
        "delta_adapts_count": deltas,
        "task_specs_count": task_specs,
        "reasoning_tasks_count": reasoning,
        "memory_edges_count": mem_edges,
        "verification_runs_count": verifs,
    }

    # Level-signal booleans (§11.4.3–§11.8.2). Machinery-backed signals are True
    # because the running framework provides the hook/closed-list/gate.
    signals = {
        # mandatory / RENAR-1
        "substrate_v1_v6": True,  # git + sqlite WAL: V1–V6 (machinery)
        # §13.3.3 named sub-checks, NOT a row count (renar_clause_reactive_adapt)
        "adapt_per_tz": clause_333["confirmed"],
        # RENAR-2
        "frontmatter_structured": specs > 0,  # specs carry typed structured fields
        "tz_immutable": adapts_approved > 0,  # §7.5: a draft ADAPT is not a fixed TZ
        "delta_tz_artifact": deltas > 0,  # non-superseded delta-ADAPT change-set (§7.6)
        # RENAR-3
        "schema_validation_hook": True,  # drift-1 detector (renar_drift.py) — machinery
        "lifecycle_statuses_used": specs_transitioned > 0,  # §11.6.2: statuses really used
        "coverage_autogen": False,  # no COVERAGE artifact in TAUSIK yet
        "reference_validation_hook": True,  # spec_link/adapt dangling-guard — machinery
        "verifies_version_pin": False,  # task_specs has no requirement-version pin (V5)
        "qg0_enforced": True,  # QG-0 Context Gate enforced (task_start) — machinery
        # RENAR-4
        "verified_by_100pct": False,  # no TC↔artifact verified-by linkage
        "pos_neg_pairing": False,  # no first-class TC artifacts
        "qg2_enforced": True,  # QG-2 Verify-First enforced — machinery
        "ai_provenance": False,  # specs/adapts carry no ai-provenance frontmatter
        "source_citation": False,
        "continuous_reconciliation": False,  # no reconciliation cadence (§12.3.10)
        # RENAR-5
        "adversarial_gate": False,  # tausik-reviewer exists but not an artifact promote-gate
        "multi_model_must": False,
        # row existence ≠ graph-first enforcement (§11.8.2); honest False
        "knowledge_graph_primary": False,
        "hallucination_rate_tracked": False,
    }
    return {
        "raw": raw,
        "signals": signals,
        "clause_13_3_3": clause_333,
        # §13.3.4 / §13.3.7 — the substrate's CHECK constraints against the
        # declared closed lists, plus the rows (renar_clause_closed_lists).
        "clause_13_3_4": assess_spec_types(conn),
        "clause_13_3_5": clause_335,
        "clause_13_3_7": assess_closed_lists(conn),
        # Obligations with no subject here, declared out loud. Gathered with the
        # rest of the DB-derived facts so `build_manifest` stays a function of
        # the bundle and never needs a connection of its own.
        "normative_inapplicability": inapplicability_section(conn),
    }


# The seven mandatory verdicts live in renar_mandatory_clauses (imported above):
# each carries the BASIS it rests on, and five of them were constants here.


def infer_level(bundle: dict[str, Any], clauses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return {level, pre_adoption, unmet_clauses, blocked_at, reason}.

    pre_adoption when any mandatory clause is unmet (§13.4.3). Otherwise the
    level is the highest RENAR-N whose cumulative observable signals all hold
    (§11.4.3–§11.8.2).
    """
    excl = scope_exclusion()
    if excl is not None:
        return {
            "level": None,
            "pre_adoption": False,
            "unmet_clauses": [],
            "blocked_at": "scope-applicability",
            "scope_exclusion": excl,
            "reason": (
                f"outside the standard's scope of application ({excl['clause']}) — "
                "no RENAR-N may be claimed regardless of signals"
            ),
        }

    signals = bundle["signals"]
    unmet = [name for name, c in clauses.items() if not c["confirmed"]]
    if unmet:
        return {
            "level": None,
            "pre_adoption": True,
            "unmet_clauses": unmet,
            "blocked_at": "mandatory-clauses",
            "reason": f"{len(unmet)} mandatory clause(s) unmet → conformance absent (§13.4.3)",
        }

    achieved: str | None = None
    for lvl in _LEVEL_ORDER:
        missing = [k for k in _LEVEL_REQUIRED[lvl] if not signals.get(k)]
        if missing:
            return {
                "level": achieved,
                "pre_adoption": achieved is None,
                "unmet_clauses": [],
                "blocked_at": lvl,
                "reason": f"{lvl} blocked by unmet signals: {missing}",
            }
        achieved = lvl
    return {
        "level": achieved,
        "pre_adoption": False,
        "unmet_clauses": [],
        "blocked_at": None,
        "reason": "all levels satisfied",
    }


def _next_level_target(verdict: dict[str, Any]) -> str | None:
    """The next level to aim for: RENAR-1 from pre-adoption, else level+1, None at top."""
    if verdict.get("scope_exclusion"):
        # Not a path-planning target: re-entry runs through §1.4.2, not the ladder.
        return None
    if verdict["pre_adoption"]:
        return "RENAR-1"
    level = verdict["level"]
    if level is None:  # blocked before RENAR-1 without pre_adoption — no target
        return "RENAR-1"
    idx = _LEVEL_ORDER.index(level)
    return _LEVEL_ORDER[idx + 1] if idx + 1 < len(_LEVEL_ORDER) else None


def build_manifest(
    bundle: dict[str, Any],
    clauses: dict[str, dict[str, Any]],
    verdict: dict[str, Any],
    assessor_id: str,
    assessment_date: str,
    manifest_version: int = 1,
    replaces: str | None = None,
) -> dict[str, Any]:
    """Assemble the §13.4.2 manifest dict (all mandatory fields always present).

    ``replaces`` is supplied by the caller, never derived here — see the field's
    own comment below for why this module cannot honestly compute it.
    """
    s = bundle["signals"]
    # §13.7 default cadence — 3 months from the assessment date.
    try:
        due = (date.fromisoformat(assessment_date) + timedelta(days=90)).isoformat()
    except ValueError:
        due = None
    inapplicable = bundle.get("normative_inapplicability") or {}
    manifest: dict[str, Any] = {
        "renar-version": RENAR_VERSION,
        "senar-version": SENAR_VERSION,
        "manifest-version": manifest_version,
        # Date-granular id keeps the V1 non-reuse guarantee across same-year assessments.
        "manifest-id": f"CFM-{assessment_date}-tausik",
        "level": verdict["level"],
        "level-target": _next_level_target(verdict),
        "pre-adoption": verdict["pre_adoption"],
        "assessment-mode": "self",
        "assessment-date": assessment_date,
        "assessor": {"id": assessor_id, "role": "architect", "signature-ref": None},
        "next-assessment-due": due,
        "mandatory-clauses-confirmed": {name: c["confirmed"] for name, c in clauses.items()},
        # What each confirmation rests on — measured, declared, machinery or
        # vacuous — directly under the block it qualifies. Always present: a
        # bare `true` with no basis is the overstatement this block removes.
        "mandatory-clauses-basis": basis_section(clauses),
        # Which confirmations their measurer has not earned. Dropped entirely
        # when empty: a bare `measurer-caveats: {}` reads as
        # searched-and-found-none, a stronger claim than an absent registry
        # supports (header says what absence means).
        **({"measurer-caveats": caveats_section()} if caveats_section() else {}),
        # Obligations with no subject here, declared out loud. Neighbour of the
        # caveats above and NOT the same claim — renar_normative_inapplicability
        # says which is which. Dropped when empty, for the same reason.
        **({"normative-inapplicability": inapplicable} if inapplicable else {}),
        # The project's §10.4.4 declaration, judged by §13.3.6 above — one
        # source, published here and read there.
        "quality-gates": dict(QUALITY_GATES_DECLARED),
        "substrate-capabilities": {
            "v1-immutable-history": "declared",
            "v2-atomic-change-unit": "declared",
            "v3-diff-review": "declared",
            "v4-branching": "declared",
            "v5-version-pin": "declared",
            "v6-author-timestamp": "declared",
            "substrate-id": "git + sqlite (.tausik/tausik.db)",
        },
        "spec-types-supported": list(SPEC_TYPES_SUPPORTED),
        # Optional evidence/diagnostics — honest derivation trail.
        "assessment-evidence": {
            "blocked-at": verdict["blocked_at"],
            "reason": verdict["reason"],
            "unmet-clauses": verdict["unmet_clauses"],
            "raw-counts": bundle["raw"],
            "level-signals": {k: bool(v) for k, v in s.items()},
            # Per-sub-check detail: a red names WHICH half of a clause broke.
            "clause-13-3-3": bundle["clause_13_3_3"]["subchecks"],
            "clause-13-3-4": bundle["clause_13_3_4"]["subchecks"],
            "clause-13-3-6": clauses["quality-gates-closed-list"]["subchecks"],
            "clause-13-3-7": bundle["clause_13_3_7"]["subchecks"],
        },
        "replaced-by": None,
        # §13.4.2 back-link into the audit journal, in the clause's own form.
        # NOT derivable here, and the attempt is what broke the chain: composing
        # `CFM-{assessment_date}-tausik@v{n-1}` named a predecessor only if it
        # had been written the SAME DAY *and* every counter value had reached
        # the journal. Neither holds — the counter advances on every `--write`,
        # the journal records only what was committed — so 5 of the first 8
        # links pointed at manifests that never existed. The predecessor's id
        # lives in the journal; the caller that can read the journal passes it.
        # Absent one, the honest value is None: a chain has to start somewhere.
        "replaces": replaces,
    }
    excl = verdict.get("scope_exclusion")
    if excl:
        # §1.5.4: "манифест либо не существует, либо явно декларирует
        # «несоответствие»". The manifest exists (§13.9.2 forbids a claim
        # without one), so the declaration must be explicit and unmissable.
        manifest["level"] = None
        manifest["level-target"] = None
        manifest["conformance-declaration"] = "non-conformant"
        manifest["scope-exclusion"] = dict(excl)
        manifest["replaced-by"] = UNKNOWN_STATE_SENTINEL
    return manifest


def generate(
    conn: sqlite3.Connection,
    assessor_id: str,
    assessment_date: str,
    manifest_version: int = 1,
    replaces: str | None = None,
) -> tuple[dict[str, Any], str]:
    """End-to-end: gather → eval clauses → infer level → manifest + yaml text.

    ``replaces`` is passed through to :func:`build_manifest` untouched — this
    layer has no more access to the audit journal than that one does.
    """
    bundle = gather_signals(conn)
    clauses = eval_mandatory_clauses(bundle)
    verdict = infer_level(bundle, clauses)
    manifest = build_manifest(
        bundle, clauses, verdict, assessor_id, assessment_date, manifest_version, replaces
    )
    return manifest, render_yaml(manifest)


def current_level(conn: sqlite3.Connection) -> dict[str, Any]:
    """Read-only conformance verdict for display (no manifest / assessor / date).

    Returns :func:`infer_level`'s verdict plus a ``missing_signals`` list — the
    unmet signal keys blocking the next level — so a status line can name them.
    """
    bundle = gather_signals(conn)
    verdict = dict(infer_level(bundle, eval_mandatory_clauses(bundle)))
    blocked = verdict.get("blocked_at")
    signals = bundle["signals"]
    verdict["missing_signals"] = (
        [k for k in _LEVEL_REQUIRED[blocked] if not signals.get(k)]
        if blocked in _LEVEL_REQUIRED
        else []
    )
    return verdict


def format_status_line(verdict: dict[str, Any]) -> str:
    """One-line dashboard summary of a :func:`current_level` verdict."""
    level = verdict.get("level")
    blocked = verdict.get("blocked_at")
    missing = verdict.get("missing_signals") or []
    tail = f": {', '.join(missing)}" if missing else ""
    if level is None:
        excl = verdict.get("scope_exclusion")
        if excl:
            return (
                f"RENAR: non-conformant by declaration ({excl['clause']} — "
                "internal product without an independent client representative)"
            )
        if blocked and blocked != "mandatory-clauses":
            return f"RENAR: pre-adoption (blocked at {blocked}{tail})"
        n = len(verdict.get("unmet_clauses") or [])
        return f"RENAR: pre-adoption ({n} mandatory clause(s) unmet)"
    if blocked:
        return f"RENAR: {level} (blocked at {blocked}{tail})"
    return f"RENAR: {level}"
