"""Bootstrap-drift gate runner — fails task-done when a source edit did not
reach the executable copy that actually runs.

The framework's runtime is the DEPLOYED profiles (.claude/, .cursor/, …), not
`scripts/` source: hooks and the MCP server load from a profile, while the test
suite imports from source (`pythonpath=["scripts"]`). So a hook or gate edit can
pass a fully green run and never take effect — green where it is checked, stale
where it runs. This is the release-1.8 thesis (memory #229): the guard exists
for the SINCERE agent who believes a fix landed, not for a liar.

Deliberately FAILS rather than auto-redeploying. A gate that rebuilt the copies
it evaluates would be mutating the state it judges — the exact defect class found
in `_handle_gate_toggle` this same cycle (an operation declared a check,
executed as a write). An edit that did not reach the running copy has NOT taken
effect, and blocking its closure is correct; the fix is one named command.

THE CHAIN HAS THREE LINKS, not two, and this gate now checks all three:
source → deployed profile (the two comparisons above), and deployed profile →
THE PROCESS THAT IS RUNNING IT. Session #191 measured the third: after a
redeploy, a fresh `gates status` listed the new gate while the MCP server
started before the redeploy closed two tasks without it. The server judges
with the registry it imported at start, and the files under it can change
without it noticing. `running_source_drift` takes a content snapshot at
process start; a change since then means this process would apply an older
gate set than the one on disk, and closing on that is refused with the one fix
there is — restart the process (a fresh CLI process is never stale).

Extracted to its own module (gate_renar_drift pattern) so gate_runner stays
under the filesize cap.
"""

from __future__ import annotations

import os
import sys
from typing import cast

import gate_outcome
import running_source_drift
from tausik_utils import library_source

# What a reader of a CANNOT-RUN row is supposed to DO. Both non-execution paths
# owe the same answer; a refusal without a next action is a dead end wearing a
# better name (#182).
_CANNOT_RUN_REMEDY = (
    "This gate produced no evidence, so it certifies nothing. Re-run once the "
    "fault above is gone; if it persists, the drift is unknown, not absent."
)


def _harness_drift_names(project_dir: str) -> list[str]:
    """Deployed harness-tree files (mcp, roles, subagents, aidd) that drift from
    source, via bootstrap's own copy functions (bootstrap_check).

    The harness tree fans out (`harness/claude/mcp/*` → `.claude/mcp/*`,
    `harness/claude/subagents/*` → `.claude/agents/*`), so a name-based
    comparator would be a second, silently-diverging layout formula (#249).
    Returns ``[]`` when bootstrap/ is not importable (a consumer without the
    source tree) — inert, never a crash: bootstrap-drift-harness-tree-ungated.
    """
    # lib_dir holds the source `harness/`: this repo (project_dir) or a submodule
    # consumer (.tausik-lib). Try both; bootstrap/ must be on sys.path to import.
    harness = library_source(project_dir, "harness")
    if harness is None:
        return []
    lib_dir = os.path.dirname(harness)
    boot = os.path.join(lib_dir, "bootstrap")
    if not os.path.isdir(boot):
        return []
    if boot not in sys.path:
        sys.path.insert(0, boot)
    from bootstrap_check import check_deployed_trees  # noqa: PLC0415

    return cast("list[str]", check_deployed_trees(lib_dir, project_dir))


def run_bootstrap_drift_gate_for(gate: dict, files: list[str]) -> gate_outcome.GateOutcome:
    """Registry-uniform ``(gate, files)`` entrypoint (gate-registry-single-source).

    Both arguments are ignored: the scan compares the deployed profiles against
    `scripts/` wholesale, and narrowing it to the task's declared files would
    let a drifted file outside that scope close a task silently.
    """
    return run_bootstrap_drift_gate()


def run_bootstrap_drift_gate() -> gate_outcome.GateOutcome:
    """Fail iff a present IDE profile's deployed source drifts from `scripts/` or
    the `harness/` fan-out.

    Read-only. Returns ``(passed, message)``. Passes (does not block) when there
    is nothing to compare — no source dir, or no profile installed (a fresh
    clone / CI has the profiles gitignored). Names the drifting files and the
    exact redeploy command on failure; a bare count is not actionable.
    """
    try:
        from project_config import find_tausik_dir  # noqa: PLC0415
        from service_doctor_drift import scripts_drift_names  # noqa: PLC0415

        # The project root is the parent of the resolved `.tausik/` dir, so the
        # gate checks the SAME project task-done is closing rather than the cwd.
        project_dir = os.path.dirname(os.path.abspath(find_tausik_dir()))
        scripts = scripts_drift_names(project_dir)
        harness = _harness_drift_names(project_dir)
    except Exception as e:  # noqa: BLE001 — caught, but recorded as non-execution, not as a pass
        return gate_outcome.could_not_run(
            gate_outcome.REASON_RUNNER_ERROR,
            f"Bootstrap drift check unavailable ({type(e).__name__}: {e}).",
            remedy=_CANNOT_RUN_REMEDY,
        )

    # The third link is checked FIRST and regardless of the other two: a
    # process that loaded an older copy than the one on disk is stale even
    # when disk and source agree — that is precisely the state a redeploy
    # leaves a running server in, and the state in which "no drift" would be
    # the most misleading answer this gate could give.
    stale = running_source_drift.changed_since_start()
    if stale:
        shown = "\n  ".join(stale[:20])
        more = f"\n  … (+{len(stale) - 20} more)" if len(stale) > 20 else ""
        return gate_outcome.failed(
            f"Stale process: {len(stale)} file(s) in the tree this process runs "
            "from changed AFTER it started, so it is executing an older copy — "
            "the gate set it applies and the handlers it runs are the ones it "
            f"imported before the change:\n  {shown}{more}\n"
            "Fix: restart the tausik-project MCP server (Claude Code: /mcp → "
            "reconnect), or close via the CLI `.tausik/tausik task done …`, "
            "which is a fresh process. The framework does not restart it for "
            "you (decision #189)."
        )

    if scripts is None and not harness:
        return gate_outcome.not_applicable(
            gate_outcome.REASON_NO_SOURCE_DIR,
            "No scripts/ source dir — bootstrap drift check skipped.",
        )
    names = sorted(set((scripts or []) + harness))
    if not names:
        return gate_outcome.passed(
            "No bootstrap drift — deployed profiles match source, and this "
            "process runs the copy that is on disk."
        )

    shown = "\n  ".join(names[:20])
    more = f"\n  … (+{len(names) - 20} more)" if len(names) > 20 else ""
    return gate_outcome.failed(
        f"Bootstrap drift: {len(names)} deployed file(s) do NOT match source — "
        "the edit did not reach the copy that runs (hooks/MCP load from the "
        "profile, not from scripts/ or harness/):\n  "
        f"{shown}{more}\n"
        "Fix: python bootstrap/bootstrap.py --ide all   (redeploys every "
        "installed profile; a bare `--update` only refreshes claude).\n"
        "Note: skills/, stacks/ and references/ drift is NOT covered here "
        "(config-dependent trees) — bootstrap-drift-harness-tree-ungated scope."
    )
