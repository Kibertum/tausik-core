"""The outcome of one quality gate — a type, not a pair of booleans.

check-result-conflates-could-not-run-with-passed (release 1.9, wave 2).

WHY THIS EXISTS. A gate result used to be ``(passed: bool, output: str)``, with
a third state smuggled through the string channel as a private sentinel
(``_SCOPED_SKIP_SENTINEL``, ``_NO_IMPL_SENTINEL``). Two booleans cannot spell
four events, so the framework spelled them by convention, and the convention
leaked in both directions:

  * A gate that COULD NOT RUN was recorded as ``passed=True`` — a check that
    never executed reporting success (`gate_runner` line 159: no implementation
    and no command, answered SKIP, which the receipt signed).
  * A gate that could not run was ALSO recorded as a blocking FAIL — session
    #182 measured ``verify --task`` over a ``slow``-marked test file:
    ``[FAIL] pytest (block)`` on ``5 deselected``, where no test failed and no
    test ran. pytest had already said so in its exit code (5,
    ``EXIT_NOTESTSCOLLECTED``); the runner collapsed every nonzero code to
    ``False`` and threw that distinction away.

Both halves follow from one root: the result did not distinguish "executed, and
here is the verdict" from "did not execute". This module makes that difference
a type.

FOUR OUTCOMES, NOT THREE. The task states three (ran+passed, ran+failed, could
not run) and then carries a negative constraint: a legitimate skip — a change
that honestly matches no test — must stay expressible and must NOT block.
Collapsing the legitimate skip into the blocking third state would replace one
indistinguishability with another, which is precisely what this task exists to
stop. So the "did not execute" branch splits by whether non-execution is
legitimate: NOT_APPLICABLE (non-blocking) and COULD_NOT_RUN (blocking).
Confirmed by the owner in session #183.

WHY COULD_NOT_RUN BLOCKS BY DEFAULT. SENAR 1.4 §8.6(e): the absence of a
negative finding is not a positive verdict. A check that could not execute has
produced no evidence, and evidence is the thing a receipt is supposed to carry.

WHY A REASON IS MANDATORY AND NOT OPTIONAL. The #182 measurement showed the
cost of a verdict without one: the refusal named neither the cause nor the
remedy, and the distance between "blocking failure" and "all green" was a
single environment variable the refusal never mentioned. A COULD_NOT_RUN
without a reason is the same dead end wearing a better name, so the constructor
refuses to build one.

TUPLE COMPATIBILITY IS DELIBERATE AND TEMPORARY. ``GateOutcome`` unpacks as
``(passed, output)`` because ~48 call sites across seven test modules and the
gate pipeline already destructure that pair. Introducing the type additively
keeps the migration reviewable and keeps the rollback plan a plain revert;
callers that need the distinction read ``.outcome`` instead of the first slot.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- The four outcomes -------------------------------------------------------

PASSED = "PASSED"
FAILED = "FAILED"
NOT_APPLICABLE = "NOT_APPLICABLE"
COULD_NOT_RUN = "COULD_NOT_RUN"

OUTCOMES = frozenset({PASSED, FAILED, NOT_APPLICABLE, COULD_NOT_RUN})

#: Outcomes that mean the check actually executed and produced a verdict.
_EXECUTED = frozenset({PASSED, FAILED})

#: Outcomes that stop a `block`-severity gate from certifying a closure.
_BLOCKING = frozenset({FAILED, COULD_NOT_RUN})

#: Outcomes that owe the reader a reason. A verdict earned by execution
#: explains itself through the tool's own output; a non-execution does not.
_REASON_REQUIRED = frozenset({NOT_APPLICABLE, COULD_NOT_RUN})


# --- Reason codes ------------------------------------------------------------
# Machine-readable, stable, and stored. The human sentence travels in `detail`
# and may be reworded freely; the code is what a query or a guard matches on,
# so renaming one is a schema change, not an edit.

# ...could not run (blocking):
REASON_NO_TESTS_COLLECTED = "no_tests_collected"
REASON_NO_GATE_IMPLEMENTATION = "no_gate_implementation"
REASON_COMMAND_NOT_RUNNABLE = "command_not_runnable"
REASON_TIMED_OUT = "timed_out"
REASON_RUNNER_ERROR = "runner_error"
REASON_TEST_SOURCE_PARSE_ERROR = "test_source_parse_error"
# The configured command failed validation. The gate the user asked for did not
# run, and running the built-in default in its place would report one check's
# verdict under another check's name (GitLab #9).
REASON_OVERRIDE_REJECTED = "command_override_rejected"

# ...not applicable (non-blocking):
REASON_NO_TEST_MAPPING = "no_test_mapping"
REASON_NO_SCOPE_DECLARED = "no_scope_declared"
REASON_STACK_MISMATCH = "stack_mismatch"
REASON_NO_MATCHING_FILES = "no_matching_files"
# Every declared file is gone from disk — a task whose whole product was
# deletions. NOT_APPLICABLE and never PASSED: a file gate handed nothing to read
# has checked nothing, and reporting green there would turn "I deleted things"
# into a free verdict. Distinct from `no_matching_files`, where files existed and
# none matched the gate's extensions: those are different facts about the run
# and only a code, not the sentence beside it, lets a query tell them apart.
REASON_ALL_FILES_DELETED = "all_files_deleted"
# A state gate found no artifact to judge. FOUR codes and not one, because the
# four say different things to whoever reads the receipt: a checkout with no
# database is not a checkout whose CLAUDE.md has no DYNAMIC markers, and only a
# code — not the sentence next to it — lets a query tell them apart. They are
# NOT_APPLICABLE and not COULD_NOT_RUN on purpose: a fresh clone with nothing to
# render is not a fault, and reddening there would punish it for being fresh.
REASON_NO_DATABASE = "no_database"
REASON_NO_INSTRUCTION_FILE = "no_instruction_file"
REASON_NO_DYNAMIC_BLOCK = "no_dynamic_block"
REASON_EMPTY_KNOWLEDGE_BASE = "empty_knowledge_base"
# The two remaining "nothing to compare" states, from the drift gates. Same
# reasoning as the four above: a fresh clone has no deployed profile and no
# materialized projection, and is not at fault for either.
REASON_NO_SOURCE_DIR = "no_source_dir"
REASON_NO_PROJECTION = "no_projection"


@dataclass(frozen=True)
class GateOutcome:
    """One gate's result: what happened, why, and what to do about it.

    ``detail`` carries the gate's own output (or the framework's sentence when
    nothing ran). ``remedy`` carries the next action, and is kept separate so a
    caller can show it without re-parsing prose.
    """

    outcome: str
    detail: str = ""
    reason_code: str = ""
    remedy: str = ""

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError(
                f"unknown gate outcome {self.outcome!r}; "
                f"expected one of {', '.join(sorted(OUTCOMES))}"
            )
        if self.outcome in _REASON_REQUIRED and not self.reason_code:
            # Refused at construction, not later: a reasonless non-execution
            # that reaches a caller has already lost the information that
            # would have made it actionable.
            raise ValueError(
                f"{self.outcome} requires a reason_code — a check that did not "
                "execute must say why (see gate_outcome.REASON_*)"
            )

    # --- Readings -----------------------------------------------------------

    @property
    def ran(self) -> bool:
        """Did the check actually execute and produce a verdict?"""
        return self.outcome in _EXECUTED

    @property
    def blocks(self) -> bool:
        """Does this stop a `block`-severity gate from certifying?"""
        return self.outcome in _BLOCKING

    @property
    def verdict(self) -> str:
        """Short label for display and for the receipt summary line."""
        return _VERDICT_LABELS[self.outcome]

    @property
    def message(self) -> str:
        """Detail and remedy as one block — what a reader of the gate sees."""
        parts = [p for p in (self.detail.strip(), self.remedy.strip()) if p]
        return "\n".join(parts)

    # --- Legacy (passed, output) compatibility ------------------------------
    # `passed` here is the OLD boolean, whose meaning was "did not block".
    # NOT_APPLICABLE keeps its historical True; COULD_NOT_RUN is False, which
    # is the behaviour change this task is for.

    @property
    def legacy_passed(self) -> bool:
        return not self.blocks

    @property
    def legacy_skipped(self) -> bool:
        return self.outcome == NOT_APPLICABLE

    def __iter__(self):
        yield self.legacy_passed
        yield self.message

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int):
        return (self.legacy_passed, self.message)[index]


_VERDICT_LABELS = {
    PASSED: "PASS",
    FAILED: "FAIL",
    NOT_APPLICABLE: "SKIP",
    # Deliberately not "SKIP": the whole defect was that a check which could
    # not run read as one that had nothing to do.
    COULD_NOT_RUN: "CANNOT-RUN",
}


# --- Constructors ------------------------------------------------------------
# Named so the call site reads as the event, and so that the reason-bearing
# outcomes cannot be built without their reason.


def passed(detail: str = "") -> GateOutcome:
    """The check ran and found nothing wrong."""
    return GateOutcome(PASSED, detail=detail)


def failed(detail: str = "") -> GateOutcome:
    """The check ran and found something wrong."""
    return GateOutcome(FAILED, detail=detail)


def not_applicable(reason_code: str, detail: str = "", remedy: str = "") -> GateOutcome:
    """The check legitimately had nothing to do. Does not block.

    A remedy is allowed but not required: "you could have scoped this run" is
    worth saying even when nothing is wrong, whereas "no Dockerfile changed"
    has no action attached to it.
    """
    return GateOutcome(NOT_APPLICABLE, detail=detail, reason_code=reason_code, remedy=remedy)


def could_not_run(reason_code: str, detail: str = "", remedy: str = "") -> GateOutcome:
    """The check could not execute. Blocks, and says why."""
    return GateOutcome(COULD_NOT_RUN, detail=detail, reason_code=reason_code, remedy=remedy)


def coerce(value) -> GateOutcome:
    """Accept a GateOutcome or a legacy ``(passed, output)`` pair.

    The gate registry dispatches to implementations this task does not migrate
    in one step (filesize, tdd-order, drift...). They keep returning the pair;
    this is the single place that lifts it into the type, so `run_gates` has
    exactly one result shape to reason about.
    """
    if isinstance(value, GateOutcome):
        return value
    ok, output = value
    return passed(output) if ok else failed(output)
