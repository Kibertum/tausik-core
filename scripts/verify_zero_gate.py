"""A run in which no gate executed is not a positive verdict.

SENAR 1.4 §8.6(e) — SHALL on every configuration, and the standard says
expressly that the property is not weakened on any of them: THE ABSENCE OF A
NEGATIVE FINDING IS NOT A POSITIVE VERDICT.

WHAT WE DID INSTEAD. `verify --task <slug> --no-tests-expected` printed "no
gate actually executed", recorded the run with `no_tests_declared=1`, exited 0
and minted a handle that closed the task (measured live, session #177). The
label was honest and the verdict was not: §8.6(e) is a property of the VERDICT,
not of the sentence printed beside it.

Worse, the row was written with a clean command. `verify_cached_run` states
that a run which passed but is not replayable — "empty scope, all gates
skipped, or a security-sensitive file set" — is stamped `noncacheable|`, and
`verify_handle_check` refuses such a row. But the all-skipped branch returns
BEFORE that stamp is applied (`verify_cached_run` line 302 returns into
`handle_no_test_mapped`, which records `command=cache_command` unprefixed), so
the one class the prefix names first was the one class it never covered.

WHY THIS IS NOT SOLVED BY REFUSING. A documentation task, a config task, an
investigation — these honestly map to no test, and an earlier version of this
branch blocked them with no way out (`verify-no-test-mapped-dead-end`). The way
out must stay, but it must be a SECOND, EXPLICIT ACT rather than a verdict
granted on the first. So: verify records the exemption and mints the handle;
closing on it requires the closer to say so, and that acknowledgement is
recorded too. One declaration is a claim; a claim plus a knowing acceptance is
a decision, and a decision is auditable.

TWO KINDS OF NON-EXECUTION, NOT ONE. A gate skipped because it does not apply
(hadolint with no Dockerfile) is legitimate. A gate that WAS applicable and
still did not run is not, and `GateOutcome` already spells the difference
(`NOT_APPLICABLE` vs `COULD_NOT_RUN`). Collapsing them would replace one
indistinguishability with another — the exact mistake `gate_outcome` was
extracted to end.

This module holds only the NOTION. It lives apart because both of its readers,
`verify_handle_check` (477 lines) and `verify_run_record` (469), are within
thirty lines of the filesize gate.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

#: Flag on `task done` by which a closer knowingly accepts a run that executed
#: no gate. Named for what it admits, not for what it permits.
ACK_FLAG = "--gates-not-applicable"

#: Outcomes that mean the gate RAN and produced a finding.
_EXECUTED = frozenset({"PASSED", "FAILED"})

#: Non-execution that is legitimate: the gate had nothing in scope to look at.
_LEGITIMATE_NON_EXECUTION = "NOT_APPLICABLE"

#: Non-execution that is not: the gate applied and still produced no evidence.
_FAILED_TO_RUN = "COULD_NOT_RUN"

# The three states a run can be in with respect to §8.6(e).
EXECUTED = "executed"
NONE_APPLICABLE = "none-applicable"
APPLICABLE_DID_NOT_RUN = "applicable-did-not-run"


def _outcome_of(result: dict[str, Any]) -> str:
    """Read a result's outcome, falling back to the legacy skipped flag.

    Results written before `gate_outcome` existed carry only ``skipped``. Such
    a result is read as NOT_APPLICABLE rather than as an execution: reading it
    the other way would let an old row certify what it never checked.
    """
    outcome = result.get("outcome")
    if isinstance(outcome, str) and outcome:
        return outcome
    return _LEGITIMATE_NON_EXECUTION if result.get("skipped") else "PASSED"


def executed_gates(results: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """The gates that actually ran and produced a finding."""
    return [r for r in results if _outcome_of(r) in _EXECUTED]


def run_state(results: Sequence[dict[str, Any]]) -> str:
    """Classify a run for §8.6(e).

    ``EXECUTED`` — at least one gate ran; the verdict rests on evidence.
    ``APPLICABLE_DID_NOT_RUN`` — a gate applied and produced nothing anyway.
      This is the state §8.6(e) forbids outright, and it is reported ahead of
      the legitimate one: a run holding both a legitimate skip and a gate that
      could not run is not made legitimate by the skip.
    ``NONE_APPLICABLE`` — nothing was in scope for any gate. Legitimate, and
      closable through an acknowledged exemption.
    """
    if not results:
        # No results at all is not "nothing applied" — it is a run that never
        # reached the gates. Treated as the forbidden state, because we cannot
        # say a gate did not apply when no gate was ever consulted.
        return APPLICABLE_DID_NOT_RUN
    if executed_gates(results):
        return EXECUTED
    if any(_outcome_of(r) == _FAILED_TO_RUN for r in results):
        return APPLICABLE_DID_NOT_RUN
    return NONE_APPLICABLE


def rests_on_a_declaration(run: dict[str, Any]) -> bool:
    """True for a recorded run that closed with no gate behind it."""
    raw = run.get("no_tests_declared")
    if raw is None or isinstance(raw, bool):
        return bool(raw)
    try:
        return bool(int(raw))
    except (TypeError, ValueError):
        return False


def refusal(run_id: Any, task_slug: str) -> str:
    """Why such a handle is refused, and the one way past it.

    A refusal that names no remedy is the dead end this branch already created
    once, so the flag is spelled out rather than alluded to.
    """
    return (
        f"verify-handle: run #{run_id} executed NO gate — it was recorded "
        "because you declared that none was expected, not because anything "
        "was checked. SENAR 1.4 §8.6(e): the absence of a negative finding is "
        "not a positive verdict, so this handle does not certify the closure "
        "on its own.\n"
        f"If that is genuinely right for '{task_slug}' — a documentation, "
        "config or investigation task that maps to no test — close it with "
        f"`{ACK_FLAG}`. The acknowledgement is recorded next to the run, so "
        "'closed with no gate behind it' stays one query away."
    )


def verdict_note(state: str) -> str:
    """What the verify command prints instead of an ordinary green."""
    if state == APPLICABLE_DID_NOT_RUN:
        return (
            "NOT A VERDICT: no gate executed, and at least one gate APPLIED — "
            "it produced no evidence rather than finding nothing wrong. This "
            "run certifies nothing and cannot be acknowledged away; fix the "
            "gate that could not run."
        )
    return (
        "NOT A VERDICT: no gate executed — you declared --no-tests-expected, "
        "so nothing was checked. Recorded with no_tests_declared=1 for the "
        f"audit trail. To close on it, say so explicitly: `{ACK_FLAG}`."
    )


#: Prefix stamped on rows that passed but may never be replayed (empty scope,
#: a security-sensitive file set). `verify_cached_run` writes it; a handle must
#: honour it or the prefix would guard one door and not the other. It lives
#: beside the zero-gate notion because both answer the same question — whether
#: a recorded row is a certificate or only an audit trail — and because its
#: reader is thirty lines from the filesize gate.
NONCACHEABLE_PREFIX = "noncacheable|"


def is_non_replayable(run: dict[str, Any]) -> bool:
    """True for a row recorded for the audit trail rather than as a certificate."""
    return str(run.get("command") or "").startswith(NONCACHEABLE_PREFIX)


def non_replayable_refusal(run_id: Any, task_slug: str) -> str:
    """Why a non-replayable row cannot certify a closure."""
    return (
        f"verify-handle: run #{run_id} is marked non-replayable "
        "(empty scope, all gates skipped, or a security-sensitive file set). "
        "It was recorded for the audit trail, not as a certificate. "
        f"Declare the scope and re-run `tausik verify --task {task_slug}`."
    )
