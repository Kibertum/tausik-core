#!/usr/bin/env python3
"""PostToolUse hook: auto-format edited files by detected stack.

Runs after Write/Edit. Determines formatter from file extension.
Also logs the changed file to the active TAUSIK task.
Exit codes: 0 = success, 1 = warning (non-blocking).
"""

import json
import os
import subprocess
import sys

# Extension → formatter command
FORMATTERS = {
    ".py": ["ruff", "format", "--quiet"],
    ".ts": ["npx", "prettier", "--write"],
    ".tsx": ["npx", "prettier", "--write"],
    ".js": ["npx", "prettier", "--write"],
    ".jsx": ["npx", "prettier", "--write"],
    ".json": ["npx", "prettier", "--write"],
    ".css": ["npx", "prettier", "--write"],
    ".scss": ["npx", "prettier", "--write"],
    ".html": ["npx", "prettier", "--write"],
    ".go": ["gofmt", "-w"],
    ".rs": ["rustfmt"],
}


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    # MultiEdit carries `file_path` too and was off this hook's matcher (PR #5);
    # the field is read through the one helper so every editor's spelling counts.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from write_tools import edited_path  # noqa: PLC0415

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    file_path = edited_path(data.get("tool_input")) or ""
    if file_path and not os.path.isabs(file_path):
        # serena speaks project-relative paths; the hook's own cwd is not
        # necessarily the project, so resolve before asking the filesystem.
        file_path = os.path.normpath(os.path.join(project_dir, file_path))
    if not file_path or not os.path.isfile(file_path):
        return 0

    # Auto-format by extension
    _, ext = os.path.splitext(file_path)
    formatter = FORMATTERS.get(ext.lower())
    if formatter:
        try:
            # check=False on purpose: a formatter's non-zero exit (syntax it
            # can't parse, config quibble) must not fail the write hook. The
            # explicit flag marks this as a conscious ignore, not a default swallow.
            subprocess.run(
                formatter + [file_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=project_dir,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Formatter not installed — graceful degradation
            pass

    # Re-index the file in the graph, in THIS process. Measured: the work is
    # 0.47 ms, while a hook process of its own costs 54 ms — thirty times the
    # work in overhead, plus a second thing to deploy and keep in cross-host
    # parity. Fail-open: a refresh that raises must not affect the write, and
    # the query layer recomputes fingerprints anyway, so a miss shows up as
    # staleness rather than as a lie.
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from graph_refresh import refresh_one

        refresh_one(project_dir, file_path)
    except Exception:  # noqa: BLE001 - the graph is secondary to the work
        pass

    # THE PER-FILE JOURNAL ENTRY WAS REMOVED HERE, session #235, with numbers.
    #
    # This block used to append "Modified: <path>" to the active task after
    # every write. Three measurements decided it:
    #
    #   * it never ran on Windows. It invoked `.tausik/tausik` — the POSIX shell
    #     wrapper — which raises OSError [WinError 2] there, and the surrounding
    #     `except OSError` swallowed it. 4 tasks out of 1,565 carry such a line,
    #     all from before the wrapper split.
    #   * reviving it costs 190 ms per write, measured through the wrapper. The
    #     whole hook was 68 ms. Nearly tripling every file write to restore a
    #     line nobody had missed is not a repair, it is a new tax.
    #   * git records which file changed, exactly and permanently. A second
    #     record of the same fact, machine-written into a journal meant for
    #     meaning, dilutes the entries an agent writes on purpose.
    #
    # What the block WAS right about is that a hook must not hand-roll what
    # `_common` already does: it resolved the wrapper itself and got the
    # platform wrong. `_common.tausik_path` and `current_active_task_slug` are
    # the ones to use if per-write journaling is ever wanted again — the latter
    # reads the slug straight from the database with no subprocess at all.

    return 0


if __name__ == "__main__":
    sys.exit(main())
