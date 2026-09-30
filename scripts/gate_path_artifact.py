"""A change under a guarded path must move its artifact in the same commit.

changed-path-does-not-require-its-artifact-to-move (1.10, github#90). The rule
is a MAP in config, not code — `gates.path_artifact.map` is a list of
`{"paths": [globs], "artifacts": [files]}`; a staged change under any `paths`
glob requires a substantive staged change to every listed artifact. Idea from
check-feature-memory.mjs of github.com/kiaquila/unicorn-hub (MIT), where a
product path requires spec.md/plan.md/tasks.md in the same PR.

Not the changelog gate: that one is bound to a TASK at `task done`; this one is
bound to PATHS at commit, whoever commits. Guards nothing by default — the map
is empty, because another repository's paths are not ours.

* an empty map is skipped OUT LOUD (NOT_APPLICABLE with a reason), never a pass;
* staged files that cannot be read (git missing, no repository) BLOCK;
* an artifact touched only by whitespace or blank lines does not count.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

import gate_outcome
import git_exec
from path_glob import glob_match

REASON_NO_PATH_MAP = "no_path_map"


def _repo_root() -> str:
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(12):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.getcwd()


def _git(root: str, *args: str) -> subprocess.CompletedProcess | None:
    try:
        return git_exec.run_git(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def staged_files(root: str) -> list[str] | None:
    got = _git(root, "diff", "--cached", "--name-only")
    if got is None or got.returncode != 0:
        return None
    return [ln.strip() for ln in (got.stdout or "").splitlines() if ln.strip()]


def moved_substantively(root: str, artifact: str) -> bool:
    """True when the staged diff of `artifact` has a non-whitespace change."""
    got = _git(root, "diff", "--cached", "-w", "--ignore-blank-lines", "--numstat", "--", artifact)
    if got is None or got.returncode != 0:
        return False
    for line in (got.stdout or "").splitlines():
        added, removed = (line.split("\t") + ["0", "0"])[:2]
        if (added.isdigit() and int(added) > 0) or (removed.isdigit() and int(removed) > 0):
            return True
    return False


def run_path_artifact_gate(gate: dict[str, Any], files: list[str], root: str | None = None):
    rules = gate.get("map") or []
    if not isinstance(rules, list) or not rules:
        return gate_outcome.not_applicable(
            REASON_NO_PATH_MAP,
            "path_artifact: no path map configured — nothing is guarded, which is not a pass.",
            remedy="Declare gates.path_artifact.map in .tausik/config.json to guard paths.",
        )
    base = root or _repo_root()
    staged = staged_files(base)
    if staged is None:
        return gate_outcome.could_not_run(
            gate_outcome.REASON_RUNNER_ERROR,
            "path_artifact: the staged file list could not be read (no git or no repository).",
            remedy="Run the commit from inside the git repository with git on PATH.",
        )
    missing: list[str] = []
    for rule in rules:
        globs = rule.get("paths") or [] if isinstance(rule, dict) else []
        artifacts = rule.get("artifacts") or [] if isinstance(rule, dict) else []
        touched = [f for f in staged if any(glob_match(g, f) for g in globs)]
        if not touched:
            continue
        for art in artifacts:
            if not moved_substantively(base, art):
                missing.append(f"{art} (for {touched[0]}{' …' if len(touched) > 1 else ''})")
    if missing:
        return gate_outcome.failed(
            "path_artifact: a guarded path changed but its artifact did not move in the same "
            "commit: " + ", ".join(missing)
        )
    return gate_outcome.passed("path_artifact: every guarded change carries its artifact")
