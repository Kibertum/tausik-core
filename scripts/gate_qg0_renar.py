"""RENAR-lite QG-0 advisory — Decision #115, ladder rung 2.

Non-blocking nudge: a high-stakes task — tier substantial/deep OR complexity
complex (either condition is sufficient) — that starts WITHOUT a linked SPEC and
WITHOUT an ADAPT is reminded to author the RENAR interpretation+gap artifact
before coding.

Advisory-first by design: this NEVER raises and NEVER blocks task_start — it
only appends a warning. Toggle via config `renar.qg0_advisory` (default on).
Hard-gate promotion (rung 3) and RENAR-2 signing (rung 4) are 2.0 work.
"""

from __future__ import annotations

from typing import Any

_HIGH_TIERS = ("substantial", "deep")


def _advisory_enabled() -> bool:
    """config renar.qg0_advisory, default True; unreadable config = enabled."""
    try:
        from project_config import load_config

        renar = load_config().get("renar", {})
        if isinstance(renar, dict):
            return bool(renar.get("qg0_advisory", True))
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        pass
    return True


def _is_high_stakes(task: dict[str, Any]) -> bool:
    return task.get("tier") in _HIGH_TIERS or task.get("complexity") == "complex"


def renar_qg0_advisory(be: Any, task: dict[str, Any], slug: str) -> str | None:
    """Return a non-blocking RENAR advisory string, or None.

    Fully defensive: any config/backend error degrades to None so QG-0 (and
    therefore task_start) is never broken by the advisory.
    """
    try:
        if not _advisory_enabled() or not _is_high_stakes(task):
            return None
        specs = be.specs_for_task(slug) or [] if hasattr(be, "specs_for_task") else []
        adapts = (
            be.adapts_for_target("task", slug) or [] if hasattr(be, "adapts_for_target") else []
        )
        if specs or adapts:
            return None
        tier = task.get("tier") or task.get("complexity") or "high-stakes"
        return (
            f"RENAR (advisory): '{slug}' is {tier} but has no linked SPEC or ADAPT. "
            f"Consider authoring the interpretation+gap artifact before coding — "
            f"link a requirement (`tausik spec link {slug} <spec>`) and interpret it "
            f"(`tausik adapt create ...`). Advisory only (Decision #115); "
            f"disable via config renar.qg0_advisory=false."
        )
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return None
