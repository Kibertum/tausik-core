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
import os
from typing import Any

from gate_qg0_check import SECURITY_KEYWORDS

# "Is this citation a real test?" — its own question, and the one every defect in
# the first Rule 5 rewrite turned out to live in. See that module's docstring.
from gate_test_citation import _test_ref_exists
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


# How many review items each tier's checklist has — the number quoted back to
# the agent so the nudge names the depth expected of it. The keyword TABLES that
# used to sit here (`scope`, `secret`, `phantom`, …) are gone: they decided the
# verdict by vocabulary, and they were wrong about it on 44.7% of the closed
# tasks carrying AC.
#
# An earlier version of this comment claimed "nothing reads a keyword list any
# more". That was not true, and saying it in the file that exists to stop
# untrue supervision messages was the worse half of the mistake: the ADVISORY
# level still accepts `manual`/`manually`/`/review`/`adversarial`, which are
# `MANUAL_RE` and `REVIEW_RE` in `service_ac_evidence` — a four-word vocabulary
# in place of a twenty-eight-word one. It is kept on purpose (an honest manual
# run is real evidence and often the only kind available), and it is why the
# hard gate does NOT accept it: the level that can be cleared by a word is the
# level that only warns.
_TIER_COUNT = {"lightweight": 4, "standard": 10, "high": 18, "critical": 28}

# Planning tiers (call-budget derived) for which a missing checklist is a HARD
# block, not a warning — SENAR Rule 5 escalation (v15s-rule5-checklist-hardgate).
_HARD_CHECKLIST_TIERS = frozenset({"substantial", "deep"})


_PROSE_SUFFIXES = (".md", ".txt", ".rst")


def _prose_only(task: dict[str, Any]) -> bool:
    """True iff the task declares relevant files and every one of them is prose.

    Prose is a Markdown/text/reST file or anything under `docs/`. An empty or
    undeclared scope is NOT prose-only — nothing is known about it, and the
    notes must keep asking. A generated file (`ROADMAP.md`, the `tausik/`
    projection) is prose by suffix and counts as such: nothing a test could
    exercise lives in it either.
    """
    try:
        rf_raw = task.get("relevant_files") or "[]"
        rf = json.loads(rf_raw) if isinstance(rf_raw, str) else (rf_raw or [])
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    paths = [str(p).replace("\\", "/").strip().lower() for p in rf if p]
    if not paths:
        return False
    return all(p.endswith(_PROSE_SUFFIXES) or p.startswith("docs/") or "/docs/" in p for p in paths)


def _task_tier(task: dict[str, Any]) -> str:
    """The task's checklist tier, from complexity + security-sensitive files."""
    try:
        rf_raw = task.get("relevant_files") or "[]"
        rf = json.loads(rf_raw) if isinstance(rf_raw, str) else (rf_raw or [])
    except (TypeError, ValueError, json.JSONDecodeError):
        rf = []
    return determine_checklist_tier(task, relevant_files=rf)


def _measurement_verified(item: Any, verified_run_ids: set[int] | None) -> bool:
    """True if the AC item cites a verification_run that FACT-checks out: its id
    is in `verified_run_ids` (the green runs for THIS task, gathered from the DB
    by the caller). A bare pytest summary carries no run id and so is never
    'verified' here — it reads as evidence by form (counted in report.covered)
    but cannot clear the fact-based activity gate. This is what stops
    `verification_run #1` (a wrong/red/foreign run) from being a free pass:
    the detector reads the form, this reads the fact."""
    if not verified_run_ids:
        return False
    return any(e.is_measurement and e.measurement_run_id in verified_run_ids for e in item.evidence)


def _evidence_strength(
    task: dict[str, Any], verified_run_ids: set[int] | None = None
) -> tuple[int, int, int]:
    """`(with_real_test, with_any_activity, total_ac)` for a task's AC evidence.

    * `with_real_test` — AC items citing a test file that EXISTS on disk OR a
      verification_run that fact-checks out (a signed green run of the real
      gates is at least as strong as a resolvable test citation).
    * `with_any_activity` — AC items whose evidence names a test, a manual run,
      a review, or a verified measurement. A bare check mark is not activity; it
      is a claim that some happened, which is the thing being verified.
    """
    from service_ac_evidence import build_report

    ac_text = task.get("acceptance_criteria") or ""
    report = build_report(ac_text, task.get("notes") or "")
    with_real_test = 0
    with_activity = 0
    for item in report.items:
        real_test = any(ref for e in item.evidence for ref in e.test_refs if _test_ref_exists(ref))
        verified_run = _measurement_verified(item, verified_run_ids)
        if real_test or verified_run:
            with_real_test += 1
        if real_test or verified_run or any(e.is_manual or e.is_review for e in item.evidence):
            with_activity += 1
    return with_real_test, with_activity, report.total_ac


def checklist_missing(task: dict[str, Any], verified_run_ids: set[int] | None = None) -> bool:
    """True when NO acceptance criterion cites an actual verification activity.

    This used to count vocabulary. `_TIER_KEYWORDS` held words like `scope`,
    `secret` and `phantom`, and a single occurrence anywhere in the notes
    silenced the gate — so it was cleared by typing a word, not by verifying
    anything. The docstring of `check_verification_checklist` already said as
    much about the v1.3 design it claimed to have replaced ("trivial to fool
    ('scope clean, no secrets' produced 2 hits)"); the structured parser was
    added ON TOP of the keyword scan rather than in place of it, and the keyword
    scan stayed as the sole source of this verdict — including for the HARD
    block on substantial/deep tasks.

    Measured over the 851 closed tasks that carry AC, the two disagree on 380 of
    them (44.7%): 320 tasks satisfied the keyword scan with no real evidence
    behind any criterion, and 60 were warned at while their evidence was real.
    A gate that is wrong in both directions on nearly half its population does
    not select for verification; it selects for knowing the password. That is
    also why the warning was ignored at every close of session #132 — there was
    no honest action that cleared it.
    """
    _real_test, with_activity, total = _evidence_strength(task, verified_run_ids)
    if not total:
        # No parsable AC — nothing to have evidence FOR. QG-0 requires AC before
        # a task can start, so this is legacy rows, not a live path.
        return True
    return with_activity == 0


def checklist_hard_block(
    task: dict[str, Any], verified_run_ids: set[int] | None = None
) -> tuple[bool, str]:
    """(blocking, message) for the Rule 5 hard gate.

    Blocks only when the task's PLANNING tier is substantial/deep AND no
    acceptance criterion cites a test file that exists OR a verification_run
    that fact-checks out. Lower tiers return (False, "") — the caller downgrades
    those to an escalating nudge.

    The hard tier is deliberately stricter than `checklist_missing`, which also
    accepts a manual run or a review — those are cleared by a word, and a level
    cleared by a word can only warn.

    An earlier version of this docstring called a resolving citation "the only
    claim it cannot make cheaply". Review disproved it: the citation was cheap
    (see `_test_ref_exists` for the three ways, now closed). What is true after
    the fix is narrower and worth stating exactly — the citation must name a
    function that is defined in a file inside `tests/`. That is a price, not a
    proof, and `_test_ref_exists` lists what it still does not establish.
    """
    tier = (task.get("tier") or "").strip().lower()
    if tier not in _HARD_CHECKLIST_TIERS:
        return False, ""
    real_test, _activity, total = _evidence_strength(task, verified_run_ids)
    if total and real_test:
        return False, ""
    return True, _no_real_test_message(tier) + _citation_diagnosis(task) + _no_test_roots_hint()


def _citation_diagnosis(task: dict[str, Any]) -> str:
    """Say WHICH of two different things went wrong with the citations.

    GitLab #16: a Rust project cited `src-tauri/.../project_extras_tests.rs::name`
    — a real, green test — and the refusal said "a path that does not resolve",
    which was false: the path resolved; the FORM was not recognised. The two
    causes have two different fixes (create/spell the path vs. cite a form the
    detector reads), so the message names the one that applies.
    """
    from ac_evidence_detectors import find_test_refs, find_unrecognised_refs

    notes = task.get("notes") or ""
    recognised = find_test_refs(notes)
    if recognised:
        unresolved = [r for r in recognised if not _test_ref_exists(r)]
        if unresolved:
            shown = ", ".join(sorted(set(unresolved))[:3])
            return (
                f"\nCITED BUT NOT RESOLVED: {shown} — the path does not exist under the "
                "project root, or the ::name is not defined in that file."
            )
        return ""
    looks_like = find_unrecognised_refs(notes)
    if looks_like:
        shown = ", ".join(sorted(set(looks_like))[:3])
        return (
            f"\nCITED BUT FORM NOT RECOGNISED: {shown} — the path resolves or not, the "
            "detector never got that far: a test file is read under tests/, test/, "
            "__tests__/ or spec/, or by name (test_x.py, x_test.go, x_tests.rs, "
            "x.test.ts, x.spec.js, x_spec.rb, XTest.java), optionally ::name."
        )
    return ""


def _no_test_roots_hint() -> str:
    """Приписка о НАСТОЯЩЕЙ причине, когда корней с тестами не нашлось вовсе.

    Без неё отказ выглядел одинаково в двух разных случаях: цитата не совпала с
    реальным тестом — и сверять было не с чем. Второй случай наступает у
    проекта с раскладкой глубже той, до которой достаёт обнаружение, и
    совершенно честная ссылка `services/api/tests/test_billing.py::test_charge`
    читалась как выдуманная. Совет в общем тексте («поправьте цитату») в этом
    случае неисполним, а настоящее лекарство — `testing.roots` — не назван.
    """
    try:
        from gate_test_citation import _project_root
        from gate_test_resolver import test_roots

        if test_roots(os.path.abspath(_project_root(None))):
            return ""
    except Exception:  # noqa: BLE001 — подсказка не обязана ронять сам гейт
        return ""
    return (
        "\nПРИЧИНА, СКОРЕЕ ВСЕГО, НЕ В ЦИТАТЕ: в этом проекте не найдено ни "
        "одного каталога с тестами, поэтому сверять ссылку не с чем и ЛЮБАЯ "
        "цитата читается как неразрешимая. Обнаружение достаёт до трёх "
        "сегментов пути (`tests`, `backend/tests`, `services/api/tests`); если "
        "тесты лежат иначе, назовите корни явно: `testing.roots` в "
        "`.tausik/config.json`."
    )


def _no_real_test_message(tier: str) -> str:
    return (
        f"QG-2 SENAR Rule 5: planning tier '{tier}' requires at least one "
        f"acceptance criterion backed by a test that EXISTS (or a green "
        f"verification_run #NNNN for this task) — none found. Log it as "
        f'`task log <slug> "AC-3: ✓ tests/test_foo.py::test_bar"`, or as a '
        f"heading 'AC-3 (what is checked): …' with '✓ tests/…::test_…' lines "
        f"directly beneath it, and re-run "
        f"task done. A bare check mark does not count, and a path that does not "
        f"resolve is treated as no evidence at all. If this task legitimately "
        f"has no test to cite, close it with the state that says so rather than "
        f"with prose. Opt out: config task_done.checklist_hard=false."
    )


def check_verification_checklist(
    task: dict[str, Any], verified_run_ids: set[int] | None = None
) -> str:
    """SENAR Core Rule 5: Verification checklist (28 items, 4 tiers).

    Returns warning string (empty if OK). Advisory — not a hard gate.
    Tier auto-detected from complexity + security keywords.

    v1.4 (r14-senar-checklist-deeper) added the structured AC evidence parser
    (`service_ac_evidence`) and described it as replacing the v1.3 keyword
    count, which it correctly called "trivial to fool". The parser was added on
    top; the keyword count stayed, and it — not the parser — remained the source
    of the "no checklist items found" verdict. `checklist_missing` now carries
    the measurement that ended it. What the parser reports is unchanged:
      - per-AC coverage (which AC have explicit evidence)
      - test-ref coverage (which AC cite tests/test_*.py::test_*)
      - negative-scenario evidence presence
    """
    from service_ac_evidence import build_report

    notes_text = task.get("notes") or ""
    tier = _task_tier(task)

    warnings: list[str] = []
    # Verification is proportionate to the change (owner, session #263): a task
    # whose every relevant file is prose — docs, notes, changelogs, plans — has
    # no behaviour a test could exercise, so the four test-shaped notes below
    # (checklist-missing, test-ref, negative, domain) are not printed for it.
    # They were: the close of a measurement task printed all of them, and each
    # is an invitation to write a test that asserts a sentence. The AC-coverage
    # note stays — evidence lines are meaningful for prose too.
    prose_only = _prose_only(task)
    if not prose_only and checklist_missing(task, verified_run_ids):
        warnings.append(
            f"NOTE: Verification checklist ({tier}, {_TIER_COUNT[tier]} items) — "
            "no acceptance criterion names a test, a manual run, a review or a "
            "green verification_run. A check mark on its own is a claim, not "
            "evidence. TWO forms are read, and naming both matters — showing one "
            "example without saying it was the only one recognised is what made "
            "this warning fire over checklists that were there. Either "
            "'AC-2: ✓ tests/test_foo.py::test_bar' on one line, or a heading "
            "'AC-2 (what is checked): …' with '✓ tests/…::test_…' lines directly "
            "beneath it (no blank line between). Log it via `task log`."
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
            # GitLab #16: a close accepted on a green verification_run printed
            # this note anyway, at every successful close — noise that trains
            # ignoring. A measured run IS the evidence the tier asks for.
            if (
                not prose_only
                and tier in ("high", "critical")
                and report.covered_with_tests == 0
                and not any(_measurement_verified(i, verified_run_ids) for i in report.items)
            ):
                warnings.append(
                    f"NOTE: tier={tier} requires test-ref evidence (e.g. "
                    "'tests/test_foo.py::test_bar') — none found in notes."
                )
            if not prose_only and tier in ("high", "critical") and not report.has_negative_evidence:
                warnings.append(
                    "NOTE: high/critical task should exercise the AC's "
                    "negative scenario — no `Negative:` evidence found in notes."
                )
            # SENAR Rule 4 domain challenge (v15s-rule4-domain-challenge): all
            # tiers except planning-tier 'trivial' must answer "does the result
            # make sense OUTSIDE the tests?" — guards against test-passing but
            # domain-meaningless outputs (arXiv 2605.30353).
            planning_tier = (task.get("tier") or "").strip().lower()
            if not prose_only and planning_tier != "trivial" and not report.has_domain_evidence:
                warnings.append(
                    "NOTE: domain challenge — does the result make sense OUTSIDE "
                    "the tests? Add a `Domain:` evidence line (e.g. 'Domain: output "
                    "is physically/semantically valid for real inputs')."
                )

    return "\n".join(warnings)
