"""RENAR-CONFORMANCE.yaml self-assessment generator (v16r-conformance-yaml).

Generates a RENAR conformance manifest (standard §14.4.2) whose level is
computed **honestly from live DB state**, never declared. The audit (§0.2.3)
found kai's hand-written manifest stuck at pre-adoption; this closes the gap by
deriving every signal from the project DB so the claim cannot drift from reality.

Honesty contract (§14.4.3): a manifest claims a ``level`` only when ALL seven
mandatory clauses (§14.3) hold AND every required comparative-table signal
(§12.9) for that level is met on real data. The moment one mandatory clause is
unmet, the generator emits ``pre_adoption: true`` + ``level: null`` instead of
overstating — the canonical resolution kai adopted (a level below RENAR-1 is not
in the closed list, so "not yet conformant" is expressed as pre-adoption).

Machinery vs data: some clauses are *capabilities* the substrate guarantees
structurally (closed SPEC-type list, closed gate list, V1–V6 over git+sqlite);
those are confirmed from machinery. Others are *data* facts (does an ADAPT exist
per ТЗ, are there TC) — confirmed only when the rows actually exist. The evidence
section reports both so a fresh agent sees exactly what is missing to reach
RENAR-1.

Read-only: queries the DB, never writes (the CLI's optional --write touches only
RENAR-CONFORMANCE.yaml at the project root).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any


from service_specs import SPEC_TYPES

RENAR_VERSION = "1.0"
SENAR_VERSION = "1.3"

# Derived from the canonical closed list (single source) → "SPEC-<TYPE>" labels.
SPEC_TYPES_SUPPORTED = [f"SPEC-{t}" for t in SPEC_TYPES]

# Comparative-table (§12.9) signal keys required at each level, cumulative. A
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
    """Collect raw counts + derived §12.9 signal booleans from the live DB.

    Capability signals (schema_validation_hook, qg*_enforced, closed lists,
    knowledge_graph, adversarial_gate) reflect TAUSIK machinery that exists
    regardless of artifact data; data signals are derived from actual rows.
    """
    specs = _scalar(conn, "SELECT COUNT(*) FROM specs")
    # Actively transitioned specs — at least one out of the initial 'draft'
    # state. The bare "status IN (closed-set)" is a tautology (DB CHECK already
    # guarantees it); §12.6.1 wants statuses *used*, i.e. real transitions.
    specs_transitioned = _scalar(conn, "SELECT COUNT(*) FROM specs WHERE status != 'draft'")
    adapts = _scalar(conn, "SELECT COUNT(*) FROM adapts")
    adapts_signed = _scalar(conn, "SELECT COUNT(*) FROM adapts WHERE status='signed'")
    # Non-superseded delta-ADAPT — a superseded delta is not a current change-set (§7.6).
    deltas = _scalar(
        conn, "SELECT COUNT(*) FROM adapts WHERE delta_n > 0 AND status != 'superseded'"
    )
    task_specs = _scalar(conn, "SELECT COUNT(*) FROM task_specs")
    reasoning = _scalar(conn, "SELECT COUNT(DISTINCT task_slug) FROM reasoning_steps")
    mem_edges = _scalar(conn, "SELECT COUNT(*) FROM memory_edges")
    verifs = _scalar(conn, "SELECT COUNT(*) FROM verification_runs")

    raw = {
        "specs_count": specs,
        "adapts_count": adapts,
        "adapts_signed_count": adapts_signed,
        "delta_adapts_count": deltas,
        "task_specs_count": task_specs,
        "reasoning_tasks_count": reasoning,
        "memory_edges_count": mem_edges,
        "verification_runs_count": verifs,
    }

    # §12.9 signal booleans. Machinery-backed signals are unconditionally True
    # because the running framework provides the hook/closed-list/gate.
    signals = {
        # mandatory / RENAR-1
        "substrate_v1_v6": True,  # git + sqlite WAL: V1–V6 (machinery)
        "adapt_per_tz": adapts > 0,  # data: needs ≥1 ADAPT in the substrate
        # RENAR-2
        "frontmatter_structured": specs > 0,  # specs carry typed structured fields
        "tz_immutable": adapts_signed > 0,  # §12.5.1: a draft ADAPT is not a fixed TZ
        "delta_tz_artifact": deltas > 0,  # non-superseded delta-ADAPT change-set (§7.6)
        # RENAR-3
        "schema_validation_hook": True,  # drift-1 detector (renar_drift.py) — machinery
        "lifecycle_statuses_used": specs_transitioned > 0,  # §12.6.1: statuses really used
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
        "continuous_reconciliation": False,  # no scheduled reconciliation hook (§12.7.1)
        # RENAR-5
        "adversarial_gate": False,  # tausik-reviewer exists but not an artifact promote-gate
        "multi_model_must": False,
        # row existence ≠ graph-first enforcement (§12.8.1); honest False
        "knowledge_graph_primary": False,
        "hallucination_rate_tracked": False,
    }
    return {"raw": raw, "signals": signals}


# Mandatory clause → (confirmed bool, evidence). §14.3.1–§14.3.7.
def eval_mandatory_clauses(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    s = bundle["signals"]
    r = bundle["raw"]
    return {
        # §14.3.1 — policy clause (requirements > code, enforced via QG-0
        # task-before-code + QG-2 verify-first). Machinery-confirmed.
        "sot-inversion": {
            "confirmed": True,
            "evidence": "QG-0 task-before-code + QG-2 verify-first policy enforced",
        },
        "substrate-v1-v6": {"confirmed": s["substrate_v1_v6"], "evidence": "git + sqlite WAL"},
        # §14.3.3 — DATA clause: a ТЗ without its ADAPT is the canonical gap
        # (audit §0.2.3). This is the honest gate that keeps a substrate without
        # tracked requirements at pre-adoption.
        "adapt-per-tz": {
            "confirmed": s["adapt_per_tz"],
            "evidence": f"{r['adapts_count']} ADAPT artifact(s)"
            if r["adapts_count"]
            else "no ADAPT artifacts — no ТЗ tracked in the requirements substrate",
        },
        "spec-types-closed-list": {
            "confirmed": True,
            "evidence": "9 closed SPEC types enforced (service + DB CHECK)",
        },
        # §14.3.5 — conditional clause: pos/neg pairing is required for each
        # normative assertion *covered by at least one TC*. TAUSIK has no
        # first-class TC artifacts, so the pairing obligation is vacuous (no
        # TC-covered assertion exists to violate it). Honest vacuous-true — NOT
        # a claim that gate_negative_scenario (a QG-0 check on task AC text)
        # enforces artifact-level TC pairing.
        "tc-pos-neg-pairing": {
            "confirmed": True,
            "evidence": "no first-class TC artifacts → pairing obligation vacuous (§14.3.5)",
        },
        "quality-gates-closed-list": {
            "confirmed": True,
            "evidence": "QG-0/QG-2 task-lifecycle gates (closed list)",
        },
        "closed-lists-backward-findings": {
            "confirmed": True,
            "evidence": "ADAPT backward-finding categories closed to 7 (FINDING_CATEGORIES)",
        },
    }


def infer_level(bundle: dict[str, Any], clauses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return {level, pre_adoption, unmet_clauses, blocked_at, reason}.

    pre_adoption when any mandatory clause is unmet (§14.4.3). Otherwise the
    level is the highest RENAR-N whose cumulative §12.9 required signals all hold.
    """
    signals = bundle["signals"]
    unmet = [name for name, c in clauses.items() if not c["confirmed"]]
    if unmet:
        return {
            "level": None,
            "pre_adoption": True,
            "unmet_clauses": unmet,
            "blocked_at": "mandatory-clauses",
            "reason": f"{len(unmet)} mandatory clause(s) unmet → conformance absent (§14.4.3)",
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
    if verdict["pre_adoption"]:
        return "RENAR-1"
    level = verdict["level"]
    idx = _LEVEL_ORDER.index(level)
    return _LEVEL_ORDER[idx + 1] if idx + 1 < len(_LEVEL_ORDER) else None


def build_manifest(
    bundle: dict[str, Any],
    clauses: dict[str, dict[str, Any]],
    verdict: dict[str, Any],
    assessor_id: str,
    assessment_date: str,
    manifest_version: int = 1,
) -> dict[str, Any]:
    """Assemble the §14.4.2 manifest dict (all mandatory fields always present)."""
    s = bundle["signals"]
    # §14.7 default cadence — 3 months from the assessment date.
    try:
        due = (date.fromisoformat(assessment_date) + timedelta(days=90)).isoformat()
    except ValueError:
        due = None
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
        "quality-gates": {
            "qg-0": "required",
            "qg-1": "required",
            "qg-2": "required",
            "qg-3": "declared",
            "qg-4": "absent",
        },
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
        },
        "replaced-by": None,
        "replaces": None,
    }
    return manifest


# Mandatory §14.4.2 keys a valid manifest must always carry.
MANDATORY_FIELDS = (
    "renar-version",
    "manifest-version",
    "manifest-id",
    "level",
    "assessment-mode",
    "assessment-date",
    "assessor",
    "mandatory-clauses-confirmed",
    "quality-gates",
    "substrate-capabilities",
    "spec-types-supported",
)


def _require_yaml():  # type: ignore[no-untyped-def]
    """Lazy PyYAML import — optional RENAR dependency, not a core CLI dep."""
    try:
        import yaml
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "RENAR conformance/export needs PyYAML — install it: pip install pyyaml "
            "(it is an OPTIONAL dependency; the core TAUSIK CLI is stdlib-only)."
        ) from e
    return yaml


def render_yaml(manifest: dict[str, Any]) -> str:
    """Serialize to YAML 1.2 (§14.4.1). Stable key order, block style."""
    yaml = _require_yaml()
    header = (
        "# RENAR Conformance Manifest — auto-generated by `tausik renar conformance`.\n"
        "# Level is computed from live DB state (§14.4.3), not declared. Do not\n"
        "# hand-edit `level` / `mandatory-clauses-confirmed` — regenerate instead.\n"
    )
    body: str = yaml.safe_dump(
        manifest, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    return header + body


def generate(
    conn: sqlite3.Connection,
    assessor_id: str,
    assessment_date: str,
    manifest_version: int = 1,
) -> tuple[dict[str, Any], str]:
    """End-to-end: gather → eval clauses → infer level → manifest + yaml text."""
    bundle = gather_signals(conn)
    clauses = eval_mandatory_clauses(bundle)
    verdict = infer_level(bundle, clauses)
    manifest = build_manifest(
        bundle, clauses, verdict, assessor_id, assessment_date, manifest_version
    )
    return manifest, render_yaml(manifest)


def current_level(conn: sqlite3.Connection) -> dict[str, Any]:
    """Read-only conformance verdict for display (no manifest / assessor / date).

    Returns :func:`infer_level`'s verdict plus a ``missing_signals`` list — the
    unmet §12.9 keys blocking the next level — so a status line can name them.
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
        if blocked and blocked != "mandatory-clauses":
            return f"RENAR: pre-adoption (blocked at {blocked}{tail})"
        n = len(verdict.get("unmet_clauses") or [])
        return f"RENAR: pre-adoption ({n} mandatory clause(s) unmet)"
    if blocked:
        return f"RENAR: {level} (blocked at {blocked}{tail})"
    return f"RENAR: {level}"
