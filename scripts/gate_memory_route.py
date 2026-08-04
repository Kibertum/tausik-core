"""`memory_route` gate — refuse a close/commit that routes knowledge off-project.

Layer 1 of the memory-route enforcement (see `memory_sinks` for the list and
the other two layers). IDE-agnostic on purpose: it judges the WORKING TREE, so
it catches a hand edit, a shell script, a CI job, and a host TAUSIK has never
heard of — everything the per-harness PreToolUse hook cannot see.

Scope, and its two honest limits. `git status --porcelain` is the input, so:

* `~/.claude/**/memory/` lives outside any repository and is unreachable from
  here — the PreToolUse hook covers it.
* A GITIGNORED sink is invisible too. That is the right trade rather than a
  hole to plug: `--ignored` would sweep in `.tausik/`, `node_modules/` and every
  build artifact, and a gitignored file cannot reach a commit anyway. The gate's
  question is "does the change this project is about to record carry knowledge
  off-project?"; the hook's is "is this write leaking?", and only the second can
  see an ignored path.

Saying so out loud matters more than the coverage — a guard whose blind spot is
undocumented reads as total.

WHY THE INERT CASES ARE NOT FAILURES. A gate that blocked every non-git project
would be enforcing "use git", not "route knowledge to TAUSIK". So: no git on
PATH, or no repository → PASS with the reason stated. But a repository where git
IS available and the call still failed is a different animal — the answer was
computable and we did not get it, which is `unknown`, not `clean`, and unknown
fails closed (Decision #157). `uncommitted_changes` collapses both into `None`,
so the two are separated here before it is called.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Any

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from memory_sinks import find_foreign_sinks, redirect_message, sinks_from_config  # noqa: E402

_GATE_NAME = "memory_route"


def _project_root() -> str | None:
    """The project this gate judges — resolved from `.tausik/`, never from cwd.

    An MCP server launched in another directory would otherwise scan whatever
    repository the process happens to stand in (memory #265, defect
    `mcp-config-read-paths`).
    """
    try:
        from project_config import find_tausik_dir  # noqa: PLC0415

        return os.path.dirname(os.path.abspath(find_tausik_dir()))
    except Exception:  # noqa: BLE001 — no project handle is a jurisdiction question, not a crash
        return None


def _cli() -> str:
    try:
        from tausik_utils import cli_invocation  # noqa: PLC0415

        return cli_invocation()
    except Exception:  # noqa: BLE001 — the message must render even without the helper
        return ".tausik/tausik"


def scan_tree(root: str, cfg: Any) -> tuple[bool, str]:
    """`(passed, output)` for one repository. Pure of gate plumbing, so tests can
    drive it directly with a temp repo and a literal config."""
    sinks, allow, config_error = sinks_from_config(cfg)
    if config_error:
        return False, (
            f"memory_route: the policy in .tausik/config.json is unreadable: "
            f"{config_error}. A policy that cannot be read is unknown, not off — "
            f"fail-closed (Decision #157). Repair the `gates.memory_route` block, "
            f"or delete it to fall back to the shipped defaults."
        )

    from verify_git_diff import _is_repo_root, uncommitted_changes  # noqa: PLC0415

    if shutil.which("git") is None:
        return True, "memory_route: git not on PATH — working-tree scan skipped."
    if not _is_repo_root(root):
        return True, "memory_route: not a git repository — working-tree scan skipped."

    # `untracked="all"`: with git's default the whole of a newly created
    # `.cursor/rules/` collapses to one entry, `.cursor/`, which matches no sink
    # pattern — so the very first write into a fresh sink directory, the most
    # likely shape of this defect, would pass. Named files or nothing.
    changed = uncommitted_changes(root=root, untracked="all")
    if changed is None:
        return False, (
            "memory_route: `git status` failed inside a git repository, so whether "
            "a foreign memory sink was touched is UNKNOWN — fail-closed. Fix git "
            "(or run `git status` by hand to see the error) and retry."
        )

    hits = find_foreign_sinks(changed, root, sinks=sinks, allow=allow)
    if not hits:
        return True, (
            f"memory_route: {len(changed)} changed path(s), none in a foreign memory sink."
        )
    return False, redirect_message(hits, _cli(), root)


def run_memory_route_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Registry-uniform `(gate, files)` entrypoint.

    `files` is ignored, deliberately and for the same reason as
    `bootstrap_drift`: narrowing the scan to the task's declared scope would let
    a sink file the task never declared close the task in silence — and a write
    that leaks knowledge is exactly the kind nobody declares.
    """
    root = _project_root()
    if root is None:
        return True, "memory_route: no project root resolved — scan skipped."
    try:
        from project_config import load_config  # noqa: PLC0415

        cfg = load_config(os.path.join(root, ".tausik"))
    except Exception as e:  # noqa: BLE001 — unreadable config is unknown policy
        return False, (
            f"memory_route: .tausik/config.json could not be loaded "
            f"({type(e).__name__}: {e}) — unknown policy, fail-closed."
        )
    try:
        return scan_tree(root, cfg)
    except Exception as e:  # noqa: BLE001 — a gate must not crash the close it guards
        return False, (
            f"memory_route: the scan raised {type(e).__name__}: {e}. An unfinished "
            f"scan proves nothing — fail-closed."
        )


def _enabled(cfg: Any) -> bool:
    """Config `enabled` for this gate, falling back to the registry default.

    Read here rather than assumed so the git pre-commit hook honours the same
    switch as `gates status` — a project that turned the gate off must not still
    be blocked at commit time by a second, independent reader.
    """
    try:
        from gate_registry import GATE_REGISTRY  # noqa: PLC0415

        default = bool(GATE_REGISTRY[_GATE_NAME].default_config.get("enabled", True))
    except Exception:  # noqa: BLE001
        default = True
    if not isinstance(cfg, dict):
        return default
    gates = cfg.get("gates")
    if not isinstance(gates, dict):
        return default
    block = gates.get(_GATE_NAME)
    if not isinstance(block, dict) or "enabled" not in block:
        return default
    # Type-checked, not truthy-coerced: a hand-edited `"false"` must not read
    # as True and keep blocking every commit against the author's intent.
    return block["enabled"] is True


def main() -> int:
    """CLI entry for the git pre-commit hook. 0 = allow, 1 = block."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    root = _project_root() or os.getcwd()
    try:
        from project_config import load_config  # noqa: PLC0415

        cfg = load_config(os.path.join(root, ".tausik"))
    except Exception:  # noqa: BLE001 — no config: the shipped defaults still apply
        cfg = {}
    if not _enabled(cfg):
        return 0
    passed, output = scan_tree(root, cfg)
    if passed:
        return 0
    print(f"BLOCKED by the memory_route gate.\n{output}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
