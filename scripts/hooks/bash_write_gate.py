#!/usr/bin/env python3
"""PreToolUse hook: extend QG-0 + scope-ACL enforcement to Bash file writes.

l26-hook-contract-review (Decision #162). The load-bearing hole: task_gate
(QG-0 "no code without a task") and scope_write_gate (SENAR Rule 2 ACL) are
wired only on Write|Edit|MultiEdit. A Bash command that writes a file — a
`cat > f <<EOF` heredoc, `sed -i`, `tee`, `dd of=`, `python -c "open(f,'w')"` —
reached neither gate, so the exact content Write refuses lands unchecked. This
was demonstrated live twice (sessions #117, #118): the same file, blocked via
Write, created via a Bash heredoc without a single objection.

This gate parses a Bash command for its write TARGETS (see `bash_write_parse`),
resolves each to a project-relative path, and applies the SAME QG-0 + scope
decision the Write gates apply — by importing THEIR functions (scope_write_gate),
not by re-deriving the rule. A second copy of the rule would drift from the
first (conv #266: judge with the real producer, not a second copy).

Residual boundary — documented in docs/ru/agent-contract.md (AC2): obfuscated
writes are NOT caught — a path built in a shell variable, `base64 -d | sh`, a
writer hidden behind a wrapper (`sudo tee`), arbitrary interpreter code beyond
a literal `open(...)`. Shell is Turing-complete; a total gate is impossible.
AC2 permits "close it OR document the boundary explicitly"; only silence is
forbidden. This raises the bar from "trivially bypass with a heredoc" to "must
actively obfuscate", and names what remains.

Exit codes: 0 = allow, 2 = block. Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
sys.path.insert(1, os.path.dirname(_HOOKS_DIR))  # scripts/ — for scope_acl

from _common import is_tausik_project  # noqa: E402
from bash_write_parse import write_targets  # noqa: E402,F401 — re-exported for tests


def main() -> int:
    # hook-stderr-encoding-locale-dependent: local import (hooks/ is sys.path[0]
    # only when run as a script) + UTF-8 so non-ASCII messages survive any host.
    from _common import (
        emit_supervision_bypass,
        emit_supervision_degradation,
        force_utf8_io,
    )

    force_utf8_io()

    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        emit_supervision_bypass(
            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()), "skip_hooks", "bash_write_gate"
        )
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    if not is_tausik_project(project_dir):
        return 0
    db_path = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(db_path):
        return 0

    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError, OSError):
        return 0
    if not isinstance(event, dict) or event.get("tool_name") != "Bash":
        return 0
    tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    from scope_write_gate import (
        _active_acls,
        _delegated_slugs,
        _relative_to_project,
        declared_acls,
        delegated_missing_scope,
        has_declared_scope,
        scope_allows,
    )

    # Only in-tree writes are this gate's jurisdiction — identical rule to the
    # Write scope gate (out-of-tree paths, /dev/null, scratchpad, other repos
    # are governed elsewhere or not at all).
    in_tree: list[str] = []
    for raw in write_targets(command):
        # A Bash redirect/target is relative to the shell's cwd — the project
        # dir — not to wherever this hook process happened to launch. Resolve it
        # against project_dir before deciding jurisdiction (task_gate does the
        # same for its file/notebook paths). Absolute targets are used as-is.
        expanded = os.path.expanduser(raw)
        cand = expanded if os.path.isabs(expanded) else os.path.join(project_dir, expanded)
        rel = _relative_to_project(cand, project_dir)
        if rel is not None and rel not in in_tree:
            in_tree.append(rel)
    if not in_tree:
        return 0  # no in-project write detected — nothing to gate

    fail_secure = bool(os.environ.get("TAUSIK_HOOK_FAIL_SECURE"))
    try:
        acls = _active_acls(db_path)
    except sqlite3.Error as e:
        if fail_secure:
            print(
                f"BLOCKED: TAUSIK_HOOK_FAIL_SECURE=1 set, but bash-write gate "
                f"could not query .tausik/tausik.db: {e}.",
                file=sys.stderr,
            )
            return 2
        emit_supervision_degradation(project_dir, "db_error", "bash_write_gate", str(e))
        return 0

    # QG-0 (SENAR Rule 1): a Bash file write with no active task is exactly the
    # 'no code without a task' the Write gate blocks — same verdict here.
    if not acls:
        listed = "\n".join(f"  {p}" for p in in_tree)
        print(
            "BLOCKED: No active task, but this Bash command writes file(s) inside "
            "the project (SENAR Rule 1 — the same rule the Write tool enforces):\n"
            f"{listed}\n"
            "Start a task first: say 'начинай работу' and describe it, or use /go.",
            file=sys.stderr,
        )
        return 2

    # scope-ACL (SENAR Rule 2): reuse the Write gate's decision verbatim.
    offender = delegated_missing_scope(acls, _delegated_slugs(db_path))
    if offender is not None:
        print(
            f"BLOCKED: delegated task '{offender}' has no scope_paths — a worker "
            f"must declare its writable surface before writing files (Bash too). "
            f"Set it: `tausik task update {offender} --scope-paths <paths>`.",
            file=sys.stderr,
        )
        return 2

    if not has_declared_scope(acls):
        return 0  # nobody declared a scope — legacy freedom (QG-0 satisfied above)

    outside = [p for p in in_tree if not scope_allows(p, acls)]
    if not outside:
        return 0

    declared = declared_acls(acls)
    acl_lines = "\n".join(f"  {slug}: {patterns}" for slug, patterns in declared)
    first_slug = declared[0][0]
    outside_norm = [q.replace("\\", "/") for q in outside]
    paths = "\n".join(f"  {p}" for p in outside_norm)
    print(
        "BLOCKED: this Bash command writes outside the active task's declared "
        "scope (SENAR Rule 2 — the same rule the Write tool enforces):\n"
        f"{paths}\n"
        f"Active ACL(s):\n{acl_lines}\n"
        f"Extend it: `tausik task update {first_slug} --scope-paths <existing...> <path>`, "
        "or reconsider whether these files belong to the task.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
