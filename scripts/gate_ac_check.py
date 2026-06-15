"""QG-2 acceptance-criteria + plan-completion + checklist-tier checks.

Extracted from `service_gates.py` for filesize-gate compliance. All four
helpers are pure functions: they take the task dict (and optionally the
list of relevant files) and either return a warning string / list, or
raise `ServiceError` for hard-gate failures. The mixin methods on
`GatesMixin` are now thin delegators to these.

  - `verify_ac` — QG-2: AC evidence presence + per-criterion checkmarks
  - `verify_plan_complete` — QG-2: every plan step marked done
  - `determine_checklist_tier` — auto-pick lightweight/standard/high/critical
  - `check_verification_checklist` — SENAR Core Rule 5 advisory warnings
"""

from __future__ import annotations

import json
from typing import Any

from gate_qg0_check import SECURITY_KEYWORDS
from tausik_utils import ServiceError


def verify_ac(slug: str, task: dict[str, Any], ac_verified: bool) -> list[str]:
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
    from service_ac_evidence import build_report

    notes = task.get("notes") or ""
    ac_text = task["acceptance_criteria"].strip()
    # Structured parse (inline-aware: single-line "1. … 2. … N." AC is counted
    # correctly, and 'AC-N: ✓' evidence markers are recognised — unlike the old
    # line-anchored regexes that under-counted both, producing a bogus
    # "N criteria, only 0 markers" warning on every single-line AC closure).
    report = build_report(ac_text, notes)
    total_ac = report.total_ac
    if not total_ac:
        return []
    # Check that evidence acknowledges verification. Accept any of:
    #  - literal "ac verified" / "verified ac" phrase
    #  - any checkmark (✓✔✅) — implies per-item evidence
    #  - at least one AC criterion with parsed evidence (test ref / marker)
    # A bare "verified" anywhere in notes is NOT accepted: an incidental
    # mention ("git identity verified", "CI verified") must not bypass QG-2.
    notes_l = notes.lower()
    has_marker = (
        "ac verified" in notes_l
        or "verified ac" in notes_l
        or any(c in notes for c in "✓✔✅")
        or report.covered > 0
    )
    if not has_marker:
        raise ServiceError(
            f"QG-2: '{slug}' has {total_ac} acceptance criteria but no verification "
            f"evidence in task notes. Log verification: "
            f'.tausik/tausik task log {slug} "AC verified: 1. ✓ 2. ✓ ..."'
        )
    # Per-criterion check: warn if not all numbered criteria have an explicit
    # evidence marker (✓ or a test ref) mapped to them.
    warnings: list[str] = []
    verified = sum(
        1 for item in report.items if any(e.has_checkmark or e.test_refs for e in item.evidence)
    )
    if verified < total_ac:
        warnings.append(
            f"WARNING: {total_ac} AC criteria, but only {verified} "
            f"have explicit evidence markers (✓). Consider verifying each criterion."
        )
    return warnings


def verify_plan_complete(slug: str, task: dict[str, Any]) -> None:
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


def determine_checklist_tier(
    task: dict[str, Any],
    relevant_files: list[str] | None = None,
) -> str:
    """Auto-detect verification checklist tier based on task risk.

    Tiers: lightweight (4 items), standard (10), high (18), critical (28).

    v1.3.4 (med-batch-2-qg #2): also consult `is_security_sensitive`
    on `relevant_files` — a "fix typo" task (title=trivial) that touches
    scripts/auth.py is security-sensitive in practice. Without this
    check, such a task picked tier='lightweight' (4 items) even though
    the file change ought to demand critical-tier review.
    """
    from service_verification import is_security_sensitive

    complexity = task.get("complexity") or "medium"
    title_goal = f"{task.get('title', '')} {task.get('goal', '')}".lower()
    # Security keywords in title/goal -> high tier
    is_security_title = any(kw in title_goal for kw in SECURITY_KEYWORDS)
    # Security-sensitive files (auth/payment/hooks/...) -> critical tier
    is_security_files = is_security_sensitive(relevant_files or [])

    if is_security_files:
        return "critical"
    if complexity == "simple" and not is_security_title:
        return "lightweight"
    if is_security_title:
        return "high"
    if complexity == "complex":
        return "critical"
    return "standard"


# Checklist keyword tables, shared by the advisory warning and the hard gate.
# Each tier is a superset of the previous one (more items = stricter review).
_LIGHTWEIGHT_KW = ["scope", "phantom", "test tamper", "secret", "hardcoded secret"]
_STANDARD_KW = _LIGHTWEIGHT_KW + [
    "delet",
    "test quality",
    "input valid",
    "deprecat",
    "cross-file",
    "code quality",
]
_HIGH_KW = _STANDARD_KW + [
    "null guard",
    "empty config",
    "header trust",
    "idor",
    "return true",
    "auth coverage",
    "deserializ",
    "ssrf",
]
_CRITICAL_KW = _HIGH_KW + [
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
_TIER_KEYWORDS = {
    "lightweight": _LIGHTWEIGHT_KW,
    "standard": _STANDARD_KW,
    "high": _HIGH_KW,
    "critical": _CRITICAL_KW,
}
_TIER_COUNT = {"lightweight": 4, "standard": 10, "high": 18, "critical": 28}

# Planning tiers (call-budget derived) for which a missing checklist is a HARD
# block, not a warning — SENAR Rule 5 escalation (v15s-rule5-checklist-hardgate).
_HARD_CHECKLIST_TIERS = frozenset({"substantial", "deep"})


def _checklist_keyword_scan(task: dict[str, Any]) -> tuple[str, int]:
    """Return (checklist_tier, kw_hits) for a task's notes. Shared helper."""
    notes_lower = (task.get("notes") or "").lower()
    try:
        rf_raw = task.get("relevant_files") or "[]"
        rf = json.loads(rf_raw) if isinstance(rf_raw, str) else (rf_raw or [])
    except (TypeError, ValueError, json.JSONDecodeError):
        rf = []
    tier = determine_checklist_tier(task, relevant_files=rf)
    checks = _TIER_KEYWORDS.get(tier, _STANDARD_KW)
    return tier, sum(1 for kw in checks if kw in notes_lower)


def checklist_missing(task: dict[str, Any]) -> bool:
    """True when no verification-checklist keyword is present in task notes."""
    _, kw_hits = _checklist_keyword_scan(task)
    return kw_hits == 0


def checklist_hard_block(task: dict[str, Any]) -> tuple[bool, str]:
    """(blocking, message) for the Rule 5 hard gate.

    Blocks only when the task's PLANNING tier is substantial/deep AND no
    checklist keyword is found in notes. Lower tiers return (False, "") — the
    caller downgrades those to an escalating nudge.
    """
    tier = (task.get("tier") or "").strip().lower()
    if tier not in _HARD_CHECKLIST_TIERS or not checklist_missing(task):
        return False, ""
    return True, (
        f"QG-2 SENAR Rule 5: planning tier '{tier}' requires a verification "
        f"checklist in notes before closing — none found. Run /review, then log "
        f"checklist evidence (scope / tests / security / edge-cases) via "
        f"`task log`, and re-run task done. Opt out: config "
        f"task_done.checklist_hard=false."
    )


def check_verification_checklist(task: dict[str, Any]) -> str:
    """SENAR Core Rule 5: Verification checklist (28 items, 4 tiers).

    Returns warning string (empty if OK). Advisory — not a hard gate.
    Tier auto-detected from complexity + security keywords.

    v1.4 (r14-senar-checklist-deeper): the v1.3 implementation counted
    keyword hits in `notes` ("scope", "phantom", "secret"…). That made
    QG-2 trivial to fool ("scope clean, no secrets" produced 2 hits)
    and gave nothing for AC traceability. We now run a structured AC
    evidence parser (`service_ac_evidence`) on top of the keyword
    check and surface the gaps:
      - per-AC coverage (which AC have explicit evidence)
      - test-ref coverage (which AC cite tests/test_*.py::test_*)
      - negative-scenario evidence presence
    """
    from service_ac_evidence import build_report

    notes_text = task.get("notes") or ""
    tier, kw_hits = _checklist_keyword_scan(task)

    warnings: list[str] = []
    if kw_hits == 0:
        warnings.append(
            f"NOTE: Verification checklist ({tier}, {_TIER_COUNT[tier]} items) — "
            "no checklist items found in notes. Run /review before closing."
        )

    ac_text = task.get("acceptance_criteria") or ""
    if ac_text.strip():
        report = build_report(ac_text, notes_text)
        if report.total_ac:
            if report.covered < report.total_ac:
                gap_str = ", ".join(str(i) for i in report.gaps())
                warnings.append(
                    f"NOTE: AC evidence parser found {report.covered}/"
                    f"{report.total_ac} criteria with explicit evidence "
                    f"(gaps: AC {gap_str}). Add 'AC-N: ✓ tested via tests/...' "
                    "lines via `task log`."
                )
            if tier in ("high", "critical") and report.covered_with_tests == 0:
                warnings.append(
                    f"NOTE: tier={tier} requires test-ref evidence (e.g. "
                    "'tests/test_foo.py::test_bar') — none found in notes."
                )
            if tier in ("high", "critical") and not report.has_negative_evidence:
                warnings.append(
                    "NOTE: high/critical task should exercise the AC's "
                    "negative scenario — no `Negative:` evidence found in notes."
                )
            # SENAR Rule 4 domain challenge (v15s-rule4-domain-challenge): all
            # tiers except planning-tier 'trivial' must answer "does the result
            # make sense OUTSIDE the tests?" — guards against test-passing but
            # domain-meaningless outputs (arXiv 2605.30353).
            planning_tier = (task.get("tier") or "").strip().lower()
            if planning_tier != "trivial" and not report.has_domain_evidence:
                warnings.append(
                    "NOTE: domain challenge — does the result make sense OUTSIDE "
                    "the tests? Add a `Domain:` evidence line (e.g. 'Domain: output "
                    "is physically/semantically valid for real inputs')."
                )

    return "\n".join(warnings)
