#!/usr/bin/env python3
"""PreToolUse hook: block Write/Edit if no active task in TAUSIK.

v1.4: direct SQLite SELECT replaces the previous subprocess + 5s timeout
shape. Two reasons:

  1. **Speed.** A subprocess CLI call costs 100-300 ms per Write/Edit on
     Windows; pure SQLite query is sub-millisecond. Editor-heavy sessions
     used to feel sluggish.
  2. **Reliability.** A subprocess that fails (PowerShell quirk, locked
     venv, transient OSError) used to silently let edits through. A DB
     error now REFUSES by default — a guard that cannot evaluate should
     not wave the edit through, the same argument this project already
     makes for QG-0 and QG-2. Announced as a breaking change on PR #5 and
     shipped in 1.9. `TAUSIK_HOOK_FAIL_OPEN=1` restores the old behaviour
     for a broken database you cannot repair right now; the retired
     `TAUSIK_HOOK_FAIL_SECURE` asks for what is now the default and says
     so instead of being ignored.

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
from _common import (  # noqa: E402
    cli_invocation,
    is_tausik_project,
    shell_cwd,
)
from hook_policy import (  # noqa: E402
    classify_target,
    fail_open_on_db_error,
    legacy_fail_secure_notice,
)


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

    Containment itself is decided by `hook_policy.classify_target`, which BOTH this
    gate and `scope_write_gate` now call. They used to decide it separately and
    disagree: this one read any path-arithmetic failure as "not proven outside"
    and blocked, while the other read it as "outside" and allowed. On Windows a
    cross-drive target makes both raise, so the same file was refused via Write
    and written via a Bash heredoc — the Bash gate reuses `scope_write_gate`.
    Only "outside" loosens anything here; "unknown" keeps the gate on, exactly
    as before.
    """
    try:
        payload = json.loads(raw_stdin) if raw_stdin.strip() else {}
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            return False
        # Any field a write tool names its target by (PR #5): a serena edit
        # says `relative_path`, a FileSystem move says `path` AND
        # `destination`. EVERY named path must be outside for the exemption:
        # judging the destination alone let a move of a project file to a
        # foreign directory pass with no task at all (review, session #259).
        from write_tools import edited_paths  # noqa: PLC0415

        paths = [p for p in edited_paths(tool_input) if p.strip()]
        if not paths:
            return False
        # A relative path belongs to the SHELL's cwd, which the payload carries
        # — not to the project by definition, which is what stood here. The two
        # part company as soon as the agent works in a second checkout, and the
        # containment test still runs on the resolved absolute path, so a
        # relative path that climbs back into the project stays gated.
        cwd = shell_cwd(payload, project_dir)
        return all(classify_target(p, project_dir, cwd=cwd)[0] == "outside" for p in paths)
    except Exception:  # noqa: BLE001 — any failure means "not proven outside" => keep gating
        return False


def _db_error_block(what_failed: str, err: Exception) -> str:
    """The refusal for "the gate could not evaluate", kept distinct from QG-0's.

    These are different refusals and an agent must be able to tell them apart:
    QG-0 says "open a task", this one says "the gate is broken". Answering the
    first when the second happened sends the reader to create a task that will
    not help. It names the way forward for the case where the DB genuinely
    cannot be fixed right now.
    """
    return (
        f"BLOCKED: the task gate {what_failed}: {err}\n"
        "  This is NOT the 'no active task' refusal — the gate could not evaluate at all,\n"
        "  and a guard that cannot evaluate refuses rather than waving the edit through.\n"
        "  Fix:      repair or restore .tausik/tausik.db (try `.tausik/tausik doctor`)\n"
        "  Override: set TAUSIK_HOOK_FAIL_OPEN=1 to allow edits while the DB is broken"
    )


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

    fail_open = fail_open_on_db_error()
    notice = legacy_fail_secure_notice()
    if notice:
        print(notice, file=sys.stderr)

    try:
        active = _has_active_task(db_path)
    except sqlite3.Error as e:
        if not fail_open:
            print(_db_error_block("could not query .tausik/tausik.db", e), file=sys.stderr)
            return 2
        # Asked for explicitly. A dropped gate must stay countable, not invisible.
        emit_supervision_degradation(project_dir, "db_error", "task_gate", str(e))
        return 0
    except Exception as e:  # defensive — never bring down the host.  # noqa: BLE001 — best-effort: a hook must never break the tool call it guards
        if not fail_open:
            print(_db_error_block("crashed while checking for an active task", e), file=sys.stderr)
            return 2
        emit_supervision_degradation(project_dir, "db_error", "task_gate", str(e))
        return 0

    if active:
        return 0

    # The most-read message in the framework. It used to point at `/go`, a
    # skill that does not exist, and otherwise offered only a Russian phrase —
    # to an audience the README addresses in English. Both are now concrete,
    # existing commands, and the CLI is spelled for the reader's shell.
    cli = cli_invocation()
    print(
        "BLOCKED: No active task. TAUSIK requires a task before code changes "
        "(SENAR Rule 1).\n"
        "  Create one:   /plan   (or describe the task and ask to start it)\n"
        f"  Resume one:   {cli} task list --status planning\n"
        f"                {cli} task start <slug>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
