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
