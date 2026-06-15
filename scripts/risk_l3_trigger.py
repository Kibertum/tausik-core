"""High-risk closures require an L3 adversarial review (v15-l3-risk-trigger).

Walko HITL-for-1% pattern: instead of one review policy for everything,
escalate only the closures whose MEASURED risk is high — the ~1% where an
adversarial pass pays for itself. Two deliberate softeners:

  - Renormalized measured score: factors the collector could not measure
    are excluded (they already push the STORED score up conservatively).
    Escalating on absence-of-measurement would block every close on
    keyless / no-verify-gate projects — punishment for adoption, not risk.
  - Minimum measurement coverage: escalation needs MIN_MEASURED_WEIGHT
    of the model by weight actually measured (0.75 = at least four of
    the five factors). Thinner subsets — {ac_evidence, code_churn} at
    0.35, or {test_delta, ac_evidence, security} at 0.60 — read high on
    every casual close (source-only files, no evidence markers yet),
    which is routine work, not "the critical 1%". The 0.60 case was a
    live boundary flake at exactly 0.6667 in the full test suite.
  - Opt-out: config risk.l3_block_on_high=false downgrades to a warning.

A recorded L3 review for the task (tausik review record --run-type l3)
satisfies the gate; run_type matching is case-insensitive ('l3'/'L3').
"""

from __future__ import annotations

import sqlite3
from typing import Any

from risk_model import LEVEL_HIGH, WEIGHTS

# Escalate only when measured factors cover at least this share of the
# model's total weight — see module docstring.
MIN_MEASURED_WEIGHT = 0.75


def measured_score(risk: dict[str, Any]) -> float | None:
    """Risk over measured factors only, renormalized to weight-sum 1.

    None when nothing was measured — no evidence either way.
    """
    defaulted = set(risk.get("defaulted") or [])
    measured = {n: v for n, v in (risk.get("factors") or {}).items() if n not in defaulted}
    if not measured:
        return None
    wsum = sum(WEIGHTS[n] for n in measured)
    if wsum <= 0:
        return None
    return round(sum(WEIGHTS[n] * float(v) for n, v in measured.items()) / wsum, 4)


def measured_weight(risk: dict[str, Any]) -> float:
    """Share of the model's weight that was actually measured (0..1)."""
    defaulted = set(risk.get("defaulted") or [])
    return round(
        sum(
            w for n, w in WEIGHTS.items() if n in (risk.get("factors") or {}) and n not in defaulted
        ),
        4,
    )


def _author_model() -> str | None:
    """Best-effort author/active model from the live transcript. Never raises."""
    try:
        from model_routing import _auto_find_transcript, read_active_model_from_transcript

        return read_active_model_from_transcript(_auto_find_transcript())
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return None


def _delegation_hint() -> str:
    """SENAR Rule 4 delegation line for the L3 remediation. Never raises."""
    try:
        from external_reviewer import reviewer_hint

        return " " + reviewer_hint(_author_model())
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return ""


def has_l3_review(conn: sqlite3.Connection, slug: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM reviews WHERE task_slug = ? AND UPPER(run_type) = 'L3' LIMIT 1",
        (slug,),
    ).fetchone()
    return row is not None


def _block_enabled() -> bool:
    try:
        from project_config import load_config

        risk_cfg = load_config().get("risk", {})
        if isinstance(risk_cfg, dict):
            return bool(risk_cfg.get("l3_block_on_high", True))
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        pass
    return True


def check_l3_required(
    conn: sqlite3.Connection, slug: str, risk: dict[str, Any] | None
) -> tuple[bool, str]:
    """(blocking, note) for a computed closure risk. Never raises.

    blocking=True -> the caller must refuse the close with the note as
    remediation. blocking=False with a non-empty note -> append as info.
    """
    try:
        if not risk:
            return False, ""
        if measured_weight(risk) < MIN_MEASURED_WEIGHT:
            return False, ""
        ms = measured_score(risk)
        if ms is None or ms < LEVEL_HIGH:
            return False, ""
        if has_l3_review(conn, slug):
            return False, (
                f"L3 escalation satisfied: measured risk {ms} >= {LEVEL_HIGH}, "
                f"recorded L3 review found"
            )
        message = (
            f"High-risk closure: measured risk {ms} >= {LEVEL_HIGH} "
            f"(SENAR Rule 10.15 selective escalation, Rule 4 external validation)."
            f"{_delegation_hint()} Then record the verdict — "
            f"`tausik review record --task {slug} --type L3 "
            f"--critical <n> --warnings <n>` — and re-run task done. "
            f"Opt out: config risk.l3_block_on_high=false."
        )
        if not _block_enabled():
            return False, f"WARNING (l3_block_on_high=false): {message}"
        return True, message
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return False, ""
