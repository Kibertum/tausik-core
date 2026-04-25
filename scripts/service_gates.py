"""TAUSIK GatesMixin — QG-0/QG-2 verification logic for task lifecycle."""

from __future__ import annotations

import json

import re
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

# Shared keyword tuples for QG-0 checks
NEGATIVE_SCENARIO_KEYWORDS = (
    "error",
    "fail",
    "invalid",
    "reject",
    "401",
    "403",
    "404",
    "422",
    "500",
    "ошибк",
    "невалидн",
    "отказ",
    "некорректн",
    "пуст",
    "отсутств",
    "not found",
    "denied",
    "unauthorized",
    "timeout",
    "empty",
    "missing",
    "negative",
    "не должн",
    "не может",
    "запрещ",
    "блокир",
    "exceed",
    "overflow",
    "refuse",
    "forbid",
    "block",
    "deny",
    "break",
    "crash",
    "exception",
)

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


def qg0_dimensions_score(task: dict[str, Any]) -> dict[str, bool]:
    """Score a task against 9 intent dimensions (prompt-master).

    Returns {dimension: bool}. A task filling ≥5 is considered well-contextualized.
    This is a soft signal — hard gates (goal, AC, negative scenario) are enforced elsewhere.
    """
    import re

    def _has(field: str) -> bool:
        val = task.get(field)
        return bool(val and str(val).strip())

    ac = (task.get("acceptance_criteria") or "") + " " + (task.get("notes") or "")
    file_re = re.compile(
        r"\b[\w/.-]+\.(py|js|ts|tsx|jsx|go|rs|java|kt|php|md|json|yaml|yml|sql|sh)\b"
    )
    memory_re = re.compile(r"\bmemory\s*#?\d+\b|\bmem_\d+\b|\b#\d+\s+\[", re.IGNORECASE)
    evidence_plan = bool(file_re.search(ac) or memory_re.search(ac))

    return {
        "goal": _has("goal"),
        "acceptance_criteria": _has("acceptance_criteria"),
        "scope": _has("scope"),
        "scope_exclude": _has("scope_exclude"),
        "role": _has("role"),
        "stack": _has("stack"),
        "complexity": _has("complexity"),
        "story_link": _has("story_slug") or _has("epic_slug"),
        "evidence_plan": evidence_plan,
    }


class GatesMixin:
    """QG-0 and QG-2 verification methods for task lifecycle."""

    be: SQLiteBackend

    def _check_qg0_start(self, slug: str, task: dict[str, Any]) -> list[str]:
        """QG-0 Context Gate: validate goal, AC, scope, negative scenarios, security.

        Returns list of warning strings (empty if no warnings).
        Raises ServiceError for hard-gate failures.
        """
        warnings: list[str] = []
        missing = []
        if not task.get("goal") or not task["goal"].strip():
            missing.append("goal")
        if (
            not task.get("acceptance_criteria")
            or not task["acceptance_criteria"].strip()
        ):
            missing.append("acceptance_criteria")
        if missing:
            raise ServiceError(
                f"QG-0 Context Gate: '{slug}' cannot start — missing {', '.join(missing)}. "
                f"Fix: .tausik/tausik task update {slug} --goal '...' --acceptance-criteria '...'"
            )
        # QG-0: warn if scope not defined (SENAR Core Rule 2)
        if not task.get("scope") or not task["scope"].strip():
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
        # QG-0: negative scenario required in AC (SENAR Core Start Gate #3)
        ac_text = (task.get("acceptance_criteria") or "").lower()
        if ac_text and not any(kw in ac_text for kw in NEGATIVE_SCENARIO_KEYWORDS):
            raise ServiceError(
                f"QG-0 Start Gate: '{slug}' AC has no negative scenario. "
                f"SENAR requires at least one error/boundary case in acceptance criteria. "
                f"Fix: add a criterion like 'Returns 400 on invalid input' or 'Ошибка при пустом поле'."
            )
        # SENAR Rule 9.2: session duration — block task_start after limit
        try:
            session_warning = self.session_check_duration()  # type: ignore[attr-defined]
            if session_warning:
                raise ServiceError(
                    f"QG-0 Start Gate: {session_warning} "
                    f"Use '/end' to finish session, or 'session extend' to continue."
                )
        except (AttributeError, Exception) as e:
            if isinstance(e, ServiceError):
                raise
            pass  # GatesMixin used outside ProjectService — skip
        # SENAR Rule 9.5: audit overdue warning at task start
        try:
            audit_warning = self.audit_check()  # type: ignore[attr-defined]
            if audit_warning:
                warnings.append(f"AUDIT: {audit_warning}")
        except (AttributeError, Exception):
            pass
        # QG-0: security surface warning (SENAR Core Start Gate #5)
        title_and_goal = f"{task.get('title', '')} {task.get('goal', '')}".lower()
        if any(kw in title_and_goal for kw in SECURITY_KEYWORDS):
            if not any(kw in ac_text for kw in SECURITY_AC_KEYWORDS):
                warnings.append(
                    f"WARNING: Task '{slug}' appears security-relevant but AC has no security criteria. "
                    f"SENAR recommends identifying threat surface and adding security AC."
                )
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

    def _verify_ac(
        self, slug: str, task: dict[str, Any], ac_verified: bool
    ) -> list[str]:
        """QG-2: Verify acceptance criteria evidence exists (per-criterion).

        Returns list of warning strings (empty if no warnings).
        Raises ServiceError for hard-gate failures.
        """
        if not task.get("acceptance_criteria"):
            return []
        if not ac_verified:
            raise ServiceError(
                f"QG-2: '{slug}' cannot complete — acceptance criteria not verified. "
                f"Verify each criterion, then: .tausik/tausik task done {slug} --ac-verified"
            )
        notes = task.get("notes") or ""
        ac_text = task["acceptance_criteria"].strip()
        # Parse numbered AC: lines starting with "1.", "2.", etc.
        ac_items = re.findall(r"^\s*\d+[\.\)]\s*(.+)", ac_text, re.MULTILINE)
        if not ac_items:
            # Fallback: split by newlines
            ac_items = [ln.strip() for ln in ac_text.splitlines() if ln.strip()]
        if not ac_items:
            return []
        # Check that evidence mentions "AC verified" at all
        if "ac verified" not in notes.lower():
            raise ServiceError(
                f"QG-2: '{slug}' has {len(ac_items)} acceptance criteria but no verification "
                f"evidence in task notes. Log verification first: "
                f'.tausik/tausik task log {slug} "AC verified: 1. ... ✓ 2. ... ✓"'
            )
        # Per-criterion check: warn if not all numbered criteria have evidence
        warnings: list[str] = []
        ac_verified_lines = re.findall(
            r"\d+[\.\)].*(?:[\u2713\u2714\u2705]|\[v\])", notes
        )
        if len(ac_verified_lines) < len(ac_items):
            warnings.append(
                f"WARNING: {len(ac_items)} AC criteria, but only {len(ac_verified_lines)} "
                f"have explicit evidence markers (✓). Consider verifying each criterion."
            )
        return warnings

    def _verify_plan_complete(self, slug: str, task: dict[str, Any]) -> None:
        """Check all plan steps are done."""
        if not task.get("plan"):
            return
        try:
            steps = json.loads(task["plan"])
            total = len(steps)
            done_count = sum(1 for s in steps if s.get("done"))
            if done_count < total:
                raise ServiceError(
                    f"Plan incomplete ({done_count}/{total} steps). "
                    f"Complete remaining steps with: .tausik/tausik task step {slug} N"
                )
        except (json.JSONDecodeError, TypeError) as e:
            raise ServiceError(f"Corrupted plan data for task '{slug}': {e}")

    def _determine_checklist_tier(self, task: dict[str, Any]) -> str:
        """Auto-detect verification checklist tier based on task risk.

        Tiers: lightweight (4 items), standard (10), high (18), critical (28).
        """
        complexity = task.get("complexity") or "medium"
        title_goal = f"{task.get('title', '')} {task.get('goal', '')}".lower()
        # Security keywords -> auto High tier
        is_security = any(kw in title_goal for kw in SECURITY_KEYWORDS)
        if complexity == "simple" and not is_security:
            return "lightweight"
        if is_security:
            return "high"
        if complexity == "complex":
            return "critical"
        return "standard"

    def _check_verification_checklist(self, slug: str, task: dict[str, Any]) -> str:
        """SENAR Core Rule 5: Verification checklist (28 items, 4 tiers).

        Returns warning string (empty if OK). Advisory — not a hard gate.
        Tier auto-detected from complexity + security keywords.
        """
        notes_lower = (task.get("notes") or "").lower()
        tier = self._determine_checklist_tier(task)
        # Lightweight: items 1, 3, 5, 7
        lightweight_kw = [
            "scope",
            "phantom",
            "test tamper",
            "secret",
            "hardcoded secret",
        ]
        # Standard: items 1-10
        standard_kw = lightweight_kw + [
            "delet",
            "test quality",
            "input valid",
            "deprecat",
            "cross-file",
            "code quality",
        ]
        # High: items 1-18 (Standard + security)
        high_kw = standard_kw + [
            "null guard",
            "empty config",
            "header trust",
            "idor",
            "return true",
            "auth coverage",
            "deserializ",
            "ssrf",
        ]
        # Critical: items 1-28 (all)
        critical_kw = high_kw + [
            "dependency version",
            "magic number",
            "over-engineer",
            "duplicat",
            "edge case",
            "naming",
            "commit scope",
            "string format",
            "unreachable",
            "swallow",
        ]
        tier_kw = {
            "lightweight": lightweight_kw,
            "standard": standard_kw,
            "high": high_kw,
            "critical": critical_kw,
        }
        tier_count = {"lightweight": 4, "standard": 10, "high": 18, "critical": 28}
        checks = tier_kw.get(tier, standard_kw)
        verified = sum(1 for kw in checks if kw in notes_lower)
        if verified == 0:
            return (
                f"NOTE: Verification checklist ({tier}, {tier_count[tier]} items) — "
                f"no checklist items found in notes. Run /review before closing."
            )
        return ""

    def _run_quality_gates(self, slug: str, relevant_files: list[str] | None) -> None:
        """QG-2 Implementation Gate: scoped gates with verify cache.

        Delegates to `service_verification.run_gates_with_cache` — see that
        module for cache rules (10 min TTL, files_hash invalidation,
        security-sensitive bypass). The scope passed in (and recorded with
        the verify run) is derived from the task's complexity tier per
        SENAR Rule 5: simple→lightweight, medium→standard, complex→high.
        Security-sensitive `relevant_files` (per `is_security_sensitive`)
        promote to `critical`.
        """
        try:
            from service_verification import is_security_sensitive, run_gates_with_cache
        except ImportError:
            import logging

            logging.getLogger("tausik.gates").warning(
                "service_verification not available"
            )
            return
        task = self.be.task_get(slug) or {}
        scope = self._determine_checklist_tier(task)
        if is_security_sensitive(relevant_files or []):
            scope = "critical"
        passed, results, _status = run_gates_with_cache(
            self.be._conn,
            slug,
            relevant_files,
            scope=scope,
            append_notes_fn=self.be.task_append_notes,
        )
        if not passed:
            failed = [
                r for r in results if not r["passed"] and r["severity"] == "block"
            ]
            details = "; ".join(f"{r['name']}: {r['output'][:100]}" for r in failed)
            raise ServiceError(
                f"QG-2 Implementation Gate: blocking gates failed for '{slug}'. "
                f"Fix issues first: {details}"
            )
