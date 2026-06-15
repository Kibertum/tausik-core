"""Composite risk model for task closure (v15-risk-model, SENAR Rule 5).

Pure, deterministic, stdlib-only. Produces a 0.0-1.0 risk score from five
normalized factors; v15-risk-compute-on-done wires it into task_done and
v15-l3-risk-trigger escalates `high` to a mandatory L3 adversarial review.

Factors (each 0.0 = safe, 1.0 = maximally risky):
  gate_coverage  — share of configured verify gates that did NOT actually
                   run (skipped/missing). Skipped gates prove nothing.
  test_delta     — source changed without proportionate test change.
  ac_evidence    — share of acceptance criteria lacking explicit evidence.
  code_churn     — change size on a log scale (big diffs hide defects).
  security_hits  — security-sensitive files touched (auth/payment/hooks).

Design choices (rationale in docs/ru/research/risk-model.md):
  - Weighted sum, not max(): closure risk accumulates across independent
    weaknesses; a single mediocre factor should not dominate, but several
    together must. max() would ignore compounding, min() is meaningless.
  - Missing factor -> conservative 1.0 + listed in `defaulted`: an
    integration that cannot measure a factor must not look safer than one
    that measured it as bad (fail-visible, not fail-open).
  - Hard ValueError on NaN / out-of-range / unknown factors: a silent
    clamp would hide caller bugs and quietly skew history rows.
"""

from __future__ import annotations

import math
from typing import Any

# Weights sum to exactly 1.0 — checked at import time below.
WEIGHTS: dict[str, float] = {
    # Unverified gates are the strongest closure-risk signal we have:
    # the whole QG-2 chain (receipts included) attests only gates that RAN.
    "gate_coverage": 0.25,
    # Untouched tests under source churn is the classic silent-regression
    # precursor; slightly below gates because scoped runs legitimately
    # skip unrelated suites.
    "test_delta": 0.20,
    # AC without evidence = "done" on the agent's word; same tier as tests.
    "ac_evidence": 0.20,
    # Security surface multiplies the cost of any defect; tier with tests.
    "security_hits": 0.20,
    # Churn is a coarse amplifier, weakest standalone predictor.
    "code_churn": 0.15,
}

# Level thresholds: high starts at 0.66 (triggers L3 review downstream),
# medium at 0.33. Boundaries land on level names, not in gaps.
LEVEL_MEDIUM = 0.33
LEVEL_HIGH = 0.66

_EPS = 1e-9
assert abs(sum(WEIGHTS.values()) - 1.0) < _EPS, "risk weights must sum to 1.0"


def _check_unit(value: float, name: str) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"risk factor {name!r}: not a number ({value!r})") from None
    if math.isnan(v) or math.isinf(v):
        raise ValueError(f"risk factor {name!r}: NaN/Inf is not a valid risk value")
    if v < 0.0 or v > 1.0:
        raise ValueError(f"risk factor {name!r}: {v} outside [0.0, 1.0]")
    return v


def compute_risk(factors: dict[str, Any]) -> dict[str, Any]:
    """Composite score from (a subset of) the five canonical factors.

    Returns {"score", "level", "factors", "weights", "defaulted"}.
    Unknown factor names raise ValueError; missing canonical factors
    default to 1.0 (conservative) and are listed in `defaulted`.
    """
    if not isinstance(factors, dict):
        raise ValueError("factors must be a dict of name -> value in [0, 1]")
    unknown = set(factors) - set(WEIGHTS)
    if unknown:
        raise ValueError(f"unknown risk factor(s) {sorted(unknown)}; expected {sorted(WEIGHTS)}")
    resolved: dict[str, float] = {}
    defaulted: list[str] = []
    for name in WEIGHTS:
        if name in factors:
            resolved[name] = _check_unit(factors[name], name)
        else:
            resolved[name] = 1.0
            defaulted.append(name)
    score = sum(WEIGHTS[n] * v for n, v in resolved.items())
    score = min(1.0, max(0.0, round(score, 4)))
    if score >= LEVEL_HIGH:
        level = "high"
    elif score >= LEVEL_MEDIUM:
        level = "medium"
    else:
        level = "low"
    return {
        "score": score,
        "level": level,
        "factors": resolved,
        "weights": dict(WEIGHTS),
        "defaulted": defaulted,
    }


# --- Normalizers: raw observations -> [0, 1] risk values --------------------


def norm_gate_coverage(gate_results: list[dict[str, Any]]) -> float:
    """Share of gates that did not produce a real PASS/FAIL run.

    Empty list = nothing ran = 1.0 (nothing proven).
    """
    if not gate_results:
        return 1.0
    ran = sum(1 for g in gate_results if not g.get("skipped"))
    return round(1.0 - ran / len(gate_results), 4)


def norm_test_delta(source_changed: int, tests_changed: int) -> float:
    """Source files changed vs test files changed.

    No source change -> 0.0 (docs/config task). Source changed with zero
    test change -> 1.0. Otherwise risk falls with the tests/source ratio;
    one test file per two source files (ratio 0.5) already counts as low
    (0.2) — demanding 1:1 would punish legitimate multi-file refactors.
    """
    if source_changed < 0 or tests_changed < 0:
        raise ValueError("file counts must be non-negative")
    if source_changed == 0:
        return 0.0
    ratio = tests_changed / source_changed
    return round(max(0.0, 1.0 - min(ratio / 0.5, 1.0) * 0.8 - min(ratio, 1.0) * 0.2), 4)


def norm_ac_evidence(criteria_total: int, criteria_with_evidence: int) -> float:
    """Share of AC items without explicit evidence. No AC at all = 1.0."""
    if criteria_total < 0 or criteria_with_evidence < 0:
        raise ValueError("criteria counts must be non-negative")
    if criteria_total == 0:
        return 1.0
    covered = min(criteria_with_evidence, criteria_total)
    return round(1.0 - covered / criteria_total, 4)


def norm_code_churn(lines_changed: int) -> float:
    """log10 scale: 0 lines = 0.0, ~10 -> 0.33, ~100 -> 0.67, >=1000 -> 1.0."""
    if lines_changed < 0:
        raise ValueError("lines_changed must be non-negative")
    return round(min(1.0, math.log10(lines_changed + 1) / 3.0), 4)


def norm_security_hits(relevant_files: list[str]) -> float:
    """0.0 when no security-sensitive file touched; otherwise floor 0.5
    plus the sensitive share — any security touch is at least medium risk."""
    if not relevant_files:
        return 0.0
    from security_pattern import is_security_sensitive

    hits = sum(1 for f in relevant_files if is_security_sensitive([f]))
    if hits == 0:
        return 0.0
    return round(min(1.0, 0.5 + 0.5 * hits / len(relevant_files)), 4)
