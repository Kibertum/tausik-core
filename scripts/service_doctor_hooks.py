"""Is the commit hook alive, switched off on purpose, or DEAD and silent?

commit-hooks-are-dead-hookspath-points-at-a-missing-repo. This repository's
`.git/config` carried `core.hooksPath = C:\\Projects\\Personal\\claude\\.git\\hooks`
— a path to a repository that does not exist on the machine. Git treats a hook
it cannot find exactly like a hook that is not there: it runs nothing and says
nothing. So on every commit, three controls silently did not run — the
`memory_route` gate (a BLOCKING control against project knowledge leaking into
another agent's memory), mypy, and the incremental RAG reindex.

The setting was repaired by the owner on 2026-08-31. This check exists because
the repair fixed the SETTING, not the DEFECT: nothing in the project would have
noticed, and nothing would notice a recurrence.

THREE STATES, NOT TWO — and that is the whole point. A boolean "are hooks
working" would have to call the third state either fine or broken, and both
answers are wrong:

  * ALIVE      — `core.hooksPath` names a directory holding a `pre-commit`.
  * BY CHOICE  — `core.hooksPath` is unset. LEGITIMATE and documented:
                 docs/ru/hooks.md:107 prescribes exactly this for CI runners
                 without mypy. Reddening here would train the reader to ignore
                 the check on every CI box, which is how a real red gets missed.
  * DEAD       — `core.hooksPath` IS set and no `pre-commit` resolves under it.
                 Nobody decided this; it is the state the defect produced, and
                 it is the only red.

WHY THE FILE IS PROBED AND THE HOOK IS NOT RUN. The measurement in the task used
`git hook run pre-commit`, which EXECUTES the hook — mypy, a RAG reindex, the
gates. A diagnostic that runs the thing it is diagnosing is not a diagnostic; it
is a side effect. `git` resolves a hook by looking for that filename under the
configured directory, so looking for the same file answers the same question.
"""

from __future__ import annotations

import os
import subprocess

#: What git looks for. Not configurable — this is git's own name for the hook.
HOOK_NAME = "pre-commit"

_LABEL = "Commit hooks"


def read_hooks_path(project_dir: str) -> str | None:
    """`core.hooksPath` as git itself resolves it, or None when unset.

    Asked of git rather than parsed out of `.git/config`, because the value can
    come from the local, global or system tier and only git knows which wins —
    re-implementing that precedence here would be a second source of truth about
    a setting whose whole defect was that nobody was watching it.
    """
    try:
        proc = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:  # noqa: BLE001 — git missing / timeout: answered below
        return None
    if proc.returncode != 0:
        return None  # exit 1 = the key is not set anywhere
    value = (proc.stdout or "").strip()
    return value or None


def resolve_hook(project_dir: str, hooks_path: str) -> str | None:
    """Absolute path of the `pre-commit` git would run, or None if none resolves.

    A relative `core.hooksPath` (the documented `scripts/hooks`) is resolved
    against the repository root, which is what git does.
    """
    base = hooks_path if os.path.isabs(hooks_path) else os.path.join(project_dir, hooks_path)
    candidate = os.path.join(base, HOOK_NAME)
    return candidate if os.path.isfile(candidate) else None


def check_commit_hooks(project_dir: str) -> list[tuple[str, str, str]]:
    """One row: ``(severity, label, detail)``. `warn` only for the dead state."""
    hooks_path = read_hooks_path(project_dir)

    if hooks_path is None:
        return [
            (
                "ok",
                _LABEL,
                "core.hooksPath is not set — git uses .git/hooks. Legitimate and "
                "documented for CI runners (docs/ru/hooks.md:107); heavy "
                "verification runs through `tausik verify` regardless.",
            )
        ]

    resolved = resolve_hook(project_dir, hooks_path)
    if resolved is not None:
        return [("ok", _LABEL, f"core.hooksPath={hooks_path} — {HOOK_NAME} resolves and will run.")]

    # The dead state. Name the path: the defect was invisible precisely because
    # nothing ever printed the value that was wrong.
    return [
        (
            "warn",
            _LABEL,
            f"core.hooksPath={hooks_path} is SET but no {HOOK_NAME} resolves under it — "
            "git treats a hook it cannot find as a hook that is not there and says "
            "nothing, so memory_route (blocking), mypy and the RAG reindex do not run "
            "on any commit.\n"
            "        Fix: git config core.hooksPath scripts/hooks   (this repository)\n"
            "        or:  git config core.hooksPath .tausik-lib/scripts/hooks   (consumer)\n"
            "        or:  git config --unset core.hooksPath   (switch them off on purpose)",
        )
    ]
