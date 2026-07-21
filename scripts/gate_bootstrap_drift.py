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

Extracted to its own module (gate_renar_drift pattern) so gate_runner stays
under the filesize cap.
"""

from __future__ import annotations

import os
import sys


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
    lib_dir = project_dir
    if not os.path.isdir(os.path.join(lib_dir, "harness")):
        alt = os.path.join(project_dir, ".tausik-lib")
        if os.path.isdir(os.path.join(alt, "harness")):
            lib_dir = alt
        else:
            return []
    boot = os.path.join(lib_dir, "bootstrap")
    if not os.path.isdir(boot):
        return []
    if boot not in sys.path:
        sys.path.insert(0, boot)
    from bootstrap_check import check_deployed_trees  # noqa: PLC0415

    return check_deployed_trees(lib_dir, project_dir)


def run_bootstrap_drift_gate() -> tuple[bool, str]:
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
    except Exception as e:  # noqa: BLE001 — a gate must never crash task-done
        return True, f"Bootstrap drift check unavailable ({type(e).__name__}: {e})."

    if scripts is None and not harness:
        return True, "No scripts/ source dir — bootstrap drift check skipped."
    names = sorted(set((scripts or []) + harness))
    if not names:
        return True, "No bootstrap drift — deployed profiles match source."

    shown = "\n  ".join(names[:20])
    more = f"\n  … (+{len(names) - 20} more)" if len(names) > 20 else ""
    return False, (
        f"Bootstrap drift: {len(names)} deployed file(s) do NOT match source — "
        "the edit did not reach the copy that runs (hooks/MCP load from the "
        "profile, not from scripts/ or harness/):\n  "
        f"{shown}{more}\n"
        "Fix: python bootstrap/bootstrap.py --ide all   (redeploys every "
        "installed profile; a bare `--update` only refreshes claude).\n"
        "Note: skills/, stacks/ and references/ drift is NOT covered here "
        "(config-dependent trees) — bootstrap-drift-harness-tree-ungated scope."
    )
