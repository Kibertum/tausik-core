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
import re
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
    notes = task.get("notes") or ""
    ac_text = task["acceptance_criteria"].strip()
    # Parse numbered AC: lines starting with "1.", "2.", etc.
    ac_items = re.findall(r"^\s*\d+[\.\)]\s*(.+)", ac_text, re.MULTILINE)
    if not ac_items:
        # Fallback: split by newlines
        ac_items = [ln.strip() for ln in ac_text.splitlines() if ln.strip()]
    if not ac_items:
        return []
    # Check that evidence acknowledges verification. Accept any of:
    #  - literal "ac verified" / "verified ac" phrase
    #  - any line with checkmark (✓✔✅) — implies per-item evidence
    #  - "verified" keyword (broader, catches "verified all AC" etc)
    notes_l = notes.lower()
    has_marker = (
        "ac verified" in notes_l
        or "verified ac" in notes_l
        or "verified" in notes_l
        or any(c in notes for c in "✓✔✅")
    )
    if not has_marker:
        raise ServiceError(
            f"QG-2: '{slug}' has {len(ac_items)} acceptance criteria but no verification "
            f"evidence in task notes. Log verification: "
            f'.tausik/tausik task log {slug} "AC verified: 1. ✓ 2. ✓ ..."'
        )
    # Per-criterion check: warn if not all numbered criteria have evidence
    warnings: list[str] = []
    ac_verified_lines = re.findall(r"\d+[\.\)].*(?:[✓✔✅]|\[v\])", notes)
    if len(ac_verified_lines) < len(ac_items):
        warnings.append(
            f"WARNING: {len(ac_items)} AC criteria, but only {len(ac_verified_lines)} "
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
    notes_lower = notes_text.lower()
    try:
        rf_raw = task.get("relevant_files") or "[]"
        rf = json.loads(rf_raw) if isinstance(rf_raw, str) else (rf_raw or [])
    except (TypeError, ValueError, json.JSONDecodeError):
        rf = []
    tier = determine_checklist_tier(task, relevant_files=rf)
    lightweight_kw = ["scope", "phantom", "test tamper", "secret", "hardcoded secret"]
    standard_kw = lightweight_kw + [
        "delet",
        "test quality",
        "input valid",
        "deprecat",
        "cross-file",
        "code quality",
    ]
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
    kw_hits = sum(1 for kw in checks if kw in notes_lower)

    warnings: list[str] = []
    if kw_hits == 0:
        warnings.append(
            f"NOTE: Verification checklist ({tier}, {tier_count[tier]} items) — "
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

    return "\n".join(warnings)
