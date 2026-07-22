#!/usr/bin/env python3
"""PreToolUse hook: block Write/Edit if no active task in TAUSIK.

v1.4: direct SQLite SELECT replaces the previous subprocess + 5s timeout
shape. Two reasons:

  1. **Speed.** A subprocess CLI call costs 100-300 ms per Write/Edit on
     Windows; pure SQLite query is sub-millisecond. Editor-heavy sessions
     used to feel sluggish.
  2. **Reliability.** A subprocess that fails (PowerShell quirk, locked
     venv, transient OSError) used to silently let edits through —
     fail-open. The new path keeps that fail-open as DEFAULT (so `tausik
     doctor` issues never brick a project) but adds an explicit
     `TAUSIK_HOOK_FAIL_SECURE=1` opt-in: under that flag, any DB error
     blocks the write instead of allowing it. Recommended for shared/CI
     contexts where silent bypass is unacceptable.

Exit codes: 0 = allow, 2 = block.

Receives JSON on stdin with tool_name, tool_input. `tool_input.file_path` is
read to decide JURISDICTION: an edit landing outside this project is allowed
without a task here, because this gate has no authority over another
repository. Everything it cannot classify stays gated — see
`target_is_outside_project`. (Until v1.8 this docstring promised the stdin read
while the code never performed it, and the gate blocked cross-repository edits.)

Skipped via TAUSIK_SKIP_HOOKS=1 env var.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import is_tausik_project  # noqa: E402


def target_is_outside_project(raw_stdin: str, project_dir: str) -> bool:
    """Whether this call edits a file TAUSIK has no authority over.

    An agent often has more than one repository open. The gate's warrant is
    "no code without a task IN THIS PROJECT"; it has no standing over a file in
    someone else's repository, does not know their tasks, and cannot judge their
    discipline. Refusing there leaves an agent with a choice between abandoning
    legitimate work and opening a FICTITIOUS task here to unblock an edit
    elsewhere — and a gate that is profitable to fake is a gate that gets faked,
    after which it stops protecting this project too.

    FAIL-CLOSED BY CONSTRUCTION. Every uncertain case returns False, which means
    "keep gating": unparseable stdin, absent tool_input, a missing or non-string
    path, or any path arithmetic that raises. The loosening applies only to a
    target proven to sit outside, never to one merely not proven inside.

    Containment is decided on realpath via commonpath, NOT startswith: with a
    plain prefix test a sibling directory sharing a prefix (``…/core-old`` next
    to ``…/core``) reads as inside, and a symlink pointing from outside into the
    project reads as outside — each the wrong answer in the dangerous direction.
    """
    try:
        payload = json.loads(raw_stdin) if raw_stdin.strip() else {}
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            return False
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not isinstance(path, str) or not path.strip():
            return False
        # Relative paths belong to the project by definition of the cwd the hook
        # runs in, so they resolve against project_dir and stay gated.
        target = os.path.realpath(os.path.join(project_dir, path))
        root = os.path.realpath(project_dir)
        return os.path.commonpath([target, root]) != root
    except Exception:  # noqa: BLE001 — any failure means "not proven outside" => keep gating
        return False


def _has_active_task(db_path: str) -> bool:
    """Direct SQLite SELECT — no subprocess.

    Returns True iff at least one row in `tasks` has status='active'.
    Raises sqlite3.Error on failure so the caller can apply the
    fail-secure policy.
    """
    conn = sqlite3.connect(db_path, timeout=2.0)
    try:
        row = conn.execute("SELECT 1 FROM tasks WHERE status = 'active' LIMIT 1").fetchone()
        return row is not None
    finally:
        conn.close()


def main() -> int:
    # hook-stderr-encoding-locale-dependent: this hook's messages contain
    # non-ASCII, and their readability must not depend on how it was
    # launched. Local import: hooks/ is sys.path[0] only when run as a script.
    from _common import (
        emit_supervision_bypass,
        emit_supervision_degradation,
        force_utf8_io,
    )

    force_utf8_io()

    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        emit_supervision_bypass(
            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()), "skip_hooks", "task_gate"
        )
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    if not is_tausik_project(project_dir):
        return 0

    # Read stdin ONCE and unconditionally: it is a pipe, and leaving it unread
    # can block the caller. An empty read is fine — the helper treats it as
    # "not proven outside" and the gate stays on.
    try:
        raw_stdin = sys.stdin.read()
    except Exception:  # noqa: BLE001 — unreadable stdin must not weaken the gate
        raw_stdin = ""

    if target_is_outside_project(raw_stdin, project_dir):
        return 0

    db_path = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(db_path):
        # Bootstrap-but-not-init: nothing to enforce yet.
        return 0

    fail_secure = bool(os.environ.get("TAUSIK_HOOK_FAIL_SECURE"))

    try:
        active = _has_active_task(db_path)
    except sqlite3.Error as e:
        if fail_secure:
            print(
                f"BLOCKED: TAUSIK_HOOK_FAIL_SECURE=1 set, but task gate could "
                f"not query .tausik/tausik.db: {e}. Fix the DB or unset the "
                "flag to allow edits.",
                file=sys.stderr,
            )
            return 2
        # Default: fail-open so a transient DB issue never bricks editing — but
        # a silently-dropped gate must stay countable, not invisible.
        emit_supervision_degradation(project_dir, "db_error", "task_gate", str(e))
        return 0
    except Exception as e:  # defensive — never bring down the host.  # noqa: BLE001 — best-effort: a hook must never break the tool call it guards
        if fail_secure:
            print(
                f"BLOCKED: TAUSIK_HOOK_FAIL_SECURE=1 set, task gate crashed: {e}",
                file=sys.stderr,
            )
            return 2
        emit_supervision_degradation(project_dir, "db_error", "task_gate", str(e))
        return 0

    if active:
        return 0

    print(
        "BLOCKED: No active task. Start a task first:\n"
        "  Say 'начинай работу' then describe your task, or use /go.\n"
        "  TAUSIK requires a task before code changes (SENAR Rule 1).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
