"""QG-0 Context Gate (start-of-task validation).

Extracted from `service_gates.py` for filesize-gate compliance. Holds the
`check_qg0_start` free function plus the `SECURITY_KEYWORDS` / `SECURITY_AC_KEYWORDS`
keyword tuples it consults. Re-exported from `service_gates` so existing imports
(`from service_gates import SECURITY_KEYWORDS`, `GatesMixin._check_qg0_start(...)`)
keep working.

Hard QG-0 gates raised via `ServiceError`:
  - missing goal / acceptance_criteria
  - AC has no negative scenario (boundary-aware via gate_negative_scenario)
  - SENAR Rule 9.2 session-duration overrun (when session_check_duration_fn supplied)
  - SENAR Rule 2: explicit medium/complex without scope declaration
    (scope_paths or legacy free-text scope; opt-out qg0.scope_hard_gate=false)
  - SENAR Rule 6: explicit medium/complex without rollback_plan

Soft warnings returned in the list:
  - missing scope (simple/unset complexity) / scope_exclude (medium/complex)
  - audit overdue (when audit_check_fn supplied)
  - security surface mentioned in title/goal but no security AC
  - <5/9 intent dimensions filled (prompt-master diagnostic)
"""

from __future__ import annotations

from typing import Any, Callable

from gate_negative_scenario import has_negative_scenario
from gate_qg0_score import qg0_dimensions_score
from tausik_utils import ServiceError


SECURITY_KEYWORDS = (
    "auth",
    "login",
    "password",
    "token",
    "jwt",
    "session",
    "oauth",
    "payment",
    "billing",
    "charge",
    "stripe",
    "pii",
    "personal data",
    "encrypt",
    "decrypt",
    "secret",
    "credential",
    "api key",
    "авториз",
    "пароль",
    "токен",
    "оплат",
    "платёж",
    "персональн",
)

SECURITY_AC_KEYWORDS = (
    "security",
    "безопасн",
    "xss",
    "injection",
    "csrf",
    "sanitiz",
    "escap",
    "encrypt",
    "hash",
    "salt",
    "rate limit",
    "brute",
    "privilege",
    "escalat",
)


def _has_scope_paths(raw: Any) -> bool:
    """True only for a NON-empty scope_paths ACL. A parsed-empty '[]' is NOT a
    valid declaration — it would pass QG-0 yet make the write-gate block every
    edit (v15p review HIGH-1)."""
    if not raw:
        return False
    try:
        from scope_acl import _parse_list

        return bool(_parse_list(raw, "scope_paths"))
    except Exception:  # noqa: BLE001 — best-effort: fall back to a string check
        return str(raw).strip() not in ("", "[]", "null")


def _scope_hard_gate_enabled() -> bool:
    """config qg0.scope_hard_gate, default True; unreadable config = enabled
    (the opt-out must be explicit, mirroring the Rule 6 gate's posture)."""
    try:
        from project_config import load_config

        qg0 = load_config().get("qg0", {})
        if isinstance(qg0, dict):
            return bool(qg0.get("scope_hard_gate", True))
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        pass
    return True


def check_qg0_start(
    slug: str,
    task: dict[str, Any],
    *,
    audit_check_fn: Callable[[], str | None] | None = None,
    session_check_duration_fn: Callable[[], str | None] | None = None,
    renar_advisory_fn: Callable[[], str | None] | None = None,
) -> list[str]:
    """QG-0 Context Gate: validate goal, AC, scope, negative scenarios, security.

    Returns list of warning strings (empty if no warnings).
    Raises ServiceError for hard-gate failures.

    Optional callbacks:
      - `session_check_duration_fn`: returns warning string when SENAR Rule 9.2
        session limit exceeded; raises ServiceError (hard-block).
      - `audit_check_fn`: returns warning string when SENAR Rule 9.5 audit overdue;
        appended to soft warnings.
    """
    warnings: list[str] = []
    missing = []
    if not task.get("goal") or not task["goal"].strip():
        missing.append("goal")
    if not task.get("acceptance_criteria") or not task["acceptance_criteria"].strip():
        missing.append("acceptance_criteria")
    if missing:
        raise ServiceError(
            f"QG-0 Context Gate: '{slug}' cannot start — missing {', '.join(missing)}. "
            f"Fix: .tausik/tausik task update {slug} --goal '...' --acceptance-criteria '...'"
        )
    # QG-0: SENAR Core Rule 2 scope. v15-scope-rule2-hardgate: explicit
    # medium/complex tasks must DECLARE scope — either structured
    # scope_paths (v30 ACL, enforced by scope_write_gate) or legacy
    # free-text scope (backward compat). Hard gate is keyword-free (no FP
    # heuristics); opt out via config qg0.scope_hard_gate=false. Unset
    # complexity / simple keeps the historical warning-only behavior.
    has_scope_decl = bool((task.get("scope") or "").strip()) or _has_scope_paths(
        task.get("scope_paths")
    )
    if not has_scope_decl:
        if task.get("complexity") in ("medium", "complex") and _scope_hard_gate_enabled():
            raise ServiceError(
                f"QG-0 Start Gate (SENAR Rule 2): '{slug}' ({task['complexity']}) "
                f"declares no scope. Define what this task may touch before "
                f"starting: .tausik/tausik task update {slug} "
                f"--scope-paths 'src/feature/*' 'tests/*' (structured ACL, "
                f"write-enforced) or --scope 'what to change' (free text). "
                f"Opt out: config qg0.scope_hard_gate=false."
            )
        warnings.append(
            f"WARNING: Task '{slug}' has no scope defined. "
            f"SENAR recommends defining what to change and what NOT to touch."
        )
    # QG-0: scope_exclude warning for medium/complex tasks (SENAR Core Rule 2)
    complexity = task.get("complexity") or "medium"
    if complexity in ("medium", "complex"):
        if not task.get("scope_exclude") or not task["scope_exclude"].strip():
            warnings.append(
                f"WARNING: Task '{slug}' ({complexity}) has no scope_exclude. "
                f"SENAR recommends defining what NOT to touch for medium/complex tasks."
            )
    # QG-0: rollback plan required for medium/complex (SENAR Rule 6,
    # v15s-rule6-rollback-plan). Hard gate ONLY for explicitly-set
    # medium/complex — unset complexity gets a warning, otherwise the
    # default-to-medium fallback would hard-block every legacy/lightweight
    # flow that never declared complexity.
    no_rollback = not (task.get("rollback_plan") or "").strip()
    if task.get("complexity") in ("medium", "complex") and no_rollback:
        raise ServiceError(
            f"QG-0 Start Gate (SENAR Rule 6): '{slug}' ({task['complexity']}) "
            f"has no rollback_plan. Define how to undo the change before "
            f"starting. Templates: 'git revert <commit>' (code), "
            f"'migration down / restore backup' (schema/data), "
            f"'feature flag off' (behavior). "
            f"Fix: .tausik/tausik task update {slug} --rollback-plan 'git revert'"
        )
    if not task.get("complexity") and no_rollback:
        warnings.append(
            f"WARNING: Task '{slug}' has no rollback_plan (SENAR Rule 6). "
            f"Recommended: task update {slug} --rollback-plan 'git revert'"
        )
    # QG-0: negative scenario required in AC (SENAR Core Start Gate #3).
    # v1.3.4 (med-batch-2-qg #1): use boundary-aware detection instead of
    # substring match. "Works without errors" no longer satisfies the gate.
    ac_text = task.get("acceptance_criteria") or ""
    if ac_text and not has_negative_scenario(ac_text):
        raise ServiceError(
            f"QG-0 Start Gate: '{slug}' AC has no negative scenario. "
            f"SENAR requires at least one error/boundary case in acceptance criteria. "
            f"Fix: add a criterion like 'Returns 400 on invalid input' or 'Ошибка при пустом поле'."
        )
    # SENAR Rule 9.2: session duration — block task_start after limit
    if session_check_duration_fn is not None:
        try:
            session_warning = session_check_duration_fn()
            if session_warning:
                raise ServiceError(
                    f"QG-0 Start Gate: {session_warning} "
                    f"Use '/end' to finish session, or 'session extend' to continue."
                )
        except ServiceError:
            raise
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            pass  # callback unavailable — skip
    # SENAR Rule 9.5: audit overdue warning at task start
    if audit_check_fn is not None:
        try:
            audit_warning = audit_check_fn()
            if audit_warning:
                warnings.append(f"AUDIT: {audit_warning}")
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            pass
    # QG-0: security surface warning (SENAR Core Start Gate #5).
    # ac_text is case-preserving for has_negative_scenario (case-insensitive
    # internally); lowercase here for SECURITY_AC substring check (keywords
    # are already lowercased).
    ac_lower = ac_text.lower()
    title_and_goal = f"{task.get('title', '')} {task.get('goal', '')}".lower()
    if any(kw in title_and_goal for kw in SECURITY_KEYWORDS):
        if not any(kw in ac_lower for kw in SECURITY_AC_KEYWORDS):
            warnings.append(
                f"WARNING: Task '{slug}' appears security-relevant but AC has no security criteria. "
                f"SENAR recommends identifying threat surface and adding security AC."
            )
    # RENAR-lite advisory (Decision #115, rung 2): non-blocking nudge for a
    # high-stakes task without a linked SPEC/ADAPT. Never raises.
    if renar_advisory_fn is not None:
        try:
            renar_msg = renar_advisory_fn()
            if renar_msg:
                warnings.append(renar_msg)
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            pass
    # QG-0: 9-dimension intent completeness (prompt-master pattern)
    dims = qg0_dimensions_score(task)
    filled = sum(1 for v in dims.values() if v)
    if filled < 5:
        missing_dims = [k for k, v in dims.items() if not v]
        warnings.append(
            f"CONTEXT: Task '{slug}' has only {filled}/9 intent dimensions defined. "
            f"Consider adding: {', '.join(missing_dims)}. "
            f"(prompt-master: thin context = drift risk)"
        )
    return warnings
