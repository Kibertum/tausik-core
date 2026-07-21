"""task_done config-flag readers — extracted from service_task_done.py.

Two tiny fail-closed readers for `config.task_done.*` hard-gate toggles.
Pulled out to keep service_task_done.py under the 400-line filesize gate when
qg2-cannot-close-fileless-task added the fileless-close plumbing; no behaviour
change, same defaults (both True — fail-closed).
"""

from __future__ import annotations


def _root_cause_hard_enabled() -> bool:
    """config task_done.root_cause_hard, default True (fail-closed policy —
    see docs/ru/research/failclosed-gates-audit.md)."""
    try:
        from project_config import load_config

        td = load_config().get("task_done", {})
        if isinstance(td, dict):
            return bool(td.get("root_cause_hard", True))
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        pass
    return True


def _checklist_hard_enabled() -> bool:
    """config task_done.checklist_hard, default True (SENAR Rule 5 hard gate
    for substantial/deep planning tiers — v15s-rule5-checklist-hardgate)."""
    try:
        from project_config import load_config

        td = load_config().get("task_done", {})
        if isinstance(td, dict):
            return bool(td.get("checklist_hard", True))
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        pass
    return True
