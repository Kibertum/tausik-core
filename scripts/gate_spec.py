"""What a built-in gate IS: the record and the two phases it can belong to.

Split out of `gate_registry` when adding one gate pushed that module past the
line cap. The seam is not arbitrary: this file is the DECLARATION (what a gate
record consists of), and `gate_registry` is the DATA (which gates exist). They
change for different reasons — a new gate touches the data every time and the
shape almost never — and keeping the shape here is also what lets a module read
`GateSpec` without importing the whole registry.

Everything here is re-exported from `gate_registry`, so every existing
`from gate_registry import GateSpec, PHASE_SCOPED` keeps working.

TWO PHASES, because there are genuinely two kinds of gate:

* ``scoped`` — takes ``(gate_config, files)`` and returns ``(passed, output)``.
  Runs inside `gate_runner.run_gates` over the task's declared scope. Every gate
  a stack can declare is of this kind.
* ``post_scope`` — takes the whole close context and edits the QG-2 *report*
  (`gate_block._block`). It answers questions no file list can express: "is
  there a fresh signed verify green for this task?", "did the changelog gain a
  line?". These run after the scoped pipeline, on the task-done path only.

`get_gates_for_trigger` filters ``post_scope`` out, so `run_gates` never tries
to call one with the wrong signature — the phase is what keeps both kinds in one
registry without one corrupting the other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: A gate's COST decides which PHASE it runs in. Fast is the default: static analysis reads
#: files and answers in seconds. Slow means the gate compiles or runs the project.
#:
#: Measured on this project: ruff plus the duplicate-test audit plus the prose audit answer in
#: 3.5 seconds together, while the full pytest lane takes about four minutes. Fifteen times
#: that shift a static gate failed AFTER the lane had already run, each costing the lane again
#: plus two or three calls. Ordering them is worth more than any one of them.
#:
#: DECLARED BY NAME, and `tests/test_gate_runner_phases.py` requires the union to cover every
#: gate whose command runs tests or builds — a list that can silently miss the next one would
#: put a four-minute gate back in the cheap phase without anybody noticing.
COST_FAST = "fast"
COST_SLOW = "slow"

SLOW_GATES: frozenset[str] = frozenset(
    {
        "pytest",
        "go-test",
        "js-test",
        "cargo-test",
        "flutter-test",
        "swift-test",
        "swift-build",
        "phpunit",
        "javac",
    }
)


def gate_cost(name: str) -> str:
    """``COST_SLOW`` for a gate that runs the project, ``COST_FAST`` otherwise."""
    return COST_SLOW if name in SLOW_GATES else COST_FAST


PHASE_SCOPED = "scoped"
PHASE_POST_SCOPE = "post_scope"


@dataclass(frozen=True)
class GateSpec:
    """Everything the framework knows about one built-in gate."""

    name: str
    phase: str
    default_config: dict[str, Any]
    impl: str
    # SENAR 1.4 §8.6(a), SHALL on every configuration including Core: WHICH
    # CHANGE DOES NOT HAPPEN while the verdict is negative. `description` does
    # not answer that — "Lint with ruff before commit" describes the MECHANISM,
    # and a claim of conformance to section 8 is invalid under §13.4 without
    # the effect. The standard names the stock phrases it refuses ("ensures
    # quality"): no proposed action can be checked against them, so they say
    # nothing. Empty by default only so the dataclass stays constructible in a
    # test; the registry guard requires every real gate to fill it.
    prevents: str = ""
    # A fileless close (`task done --no-file-changes`) has no scope to gate.
    # Verify-First still runs — it is what *proves* the scope is empty — but
    # the changelog gate cannot apply: a task that touched no files carries no
    # changelog diff by construction. Declared here rather than as an `if` in
    # the runner so the exception is visible next to the gate it exempts.
    skip_on_fileless_close: bool = False
    # Post-scope gates that predate this registry own a config key of their
    # own (changelog: `task_done.changelog_gate.enabled`). The resolver lets
    # `gates status` report what will actually happen instead of the registry
    # default, which would be a lie for any project using the legacy key.
    enabled_resolver: str | None = field(default=None)
