#!/usr/bin/env python3
"""SessionStart hook: auto-inject TAUSIK project state into new Claude Code sessions.

Eliminates the need for manual /start — agent sees active tasks, blockers,
and session warnings as part of the initial conversation context.

Exit code 0 always (graceful degradation). Output: Claude Code hookSpecificOutput JSON.
Skipped via TAUSIK_SKIP_HOOKS=1 env var.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import tausik_path as _tausik_path  # noqa: E402


def _run_tausik(cmd: str, args: list[str], project_dir: str, timeout: int = 4) -> str:
    """Run tausik CLI; return stdout on success, empty string on any failure."""
    try:
        result = subprocess.run(
            [cmd, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=project_dir,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def _rag_server_path(project_dir: str) -> str | None:
    """Path to the codebase-rag MCP server.py if installed, else None."""
    for ide in ("claude", "cursor"):
        p = os.path.join(project_dir, ".claude", "mcp", "codebase-rag", "server.py")
        if os.path.exists(p):
            return p
        p2 = os.path.join(
            project_dir, "agents", ide, "mcp", "codebase-rag", "server.py"
        )
        if os.path.exists(p2):
            return p2
    return None


def _spawn_background_reindex(project_dir: str, mode: str = "incremental") -> None:
    """Spawn rag indexer in background; return immediately.

    On first run (`full`) we still spawn detached so SessionStart never blocks.
    A small Python wrapper is enough — rag_indexer's `index_incremental` /
    `index_full` are called via the same server.py runtime.
    """
    server = _rag_server_path(project_dir)
    if not server:
        return
    venv_py = os.path.join(project_dir, ".tausik", "venv", "Scripts", "python.exe")
    if not os.path.exists(venv_py):
        venv_py = os.path.join(project_dir, ".tausik", "venv", "bin", "python")
    if not os.path.exists(venv_py):
        venv_py = sys.executable
    code = (
        f"import sys; sys.path.insert(0, {os.path.dirname(server)!r}); "
        "from rag_store import RAGStore; "
        "from rag_indexer import index_incremental, index_full; "
        f"store = RAGStore({os.path.join(project_dir, '.tausik', 'rag', 'rag.db')!r}); "
        f"({'index_full' if mode == 'full' else 'index_incremental'})({project_dir!r}, store)"
    )
    try:
        kwargs: dict = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "cwd": project_dir,
        }
        if sys.platform == "win32":
            DETACHED_PROCESS = 0x00000008
            kwargs["creationflags"] = DETACHED_PROCESS  # type: ignore[assignment]
        else:
            kwargs["start_new_session"] = True  # type: ignore[assignment]
        subprocess.Popen([venv_py, "-c", code], **kwargs)
    except (OSError, ValueError):
        pass  # never break the session start


def _rag_summary(project_dir: str) -> str:
    """Best-effort summary of RAG index health + auto-spawn incremental reindex."""
    rag_db = os.path.join(project_dir, ".tausik", "rag", "rag.db")
    if not os.path.exists(rag_db):
        # First run for this project — spawn FULL reindex in background.
        _spawn_background_reindex(project_dir, mode="full")
        return "RAG: not initialised — full reindex spawned in background. Try `search_code` after a minute."
    try:
        import sqlite3

        with sqlite3.connect(rag_db) as conn:
            row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
            chunks = int(row[0]) if row else 0
    except Exception:
        return "RAG: status unknown (db unreadable)."
    # Always kick off an incremental reindex in the background so the index
    # picks up any commits made between sessions. Cheap when nothing changed
    # (early-return inside index_incremental on same `last_commit`).
    _spawn_background_reindex(project_dir, mode="incremental")
    if chunks == 0:
        return "RAG: empty — full reindex spawned in background."
    return f"RAG: {chunks} chunks indexed — incremental reindex running in background. Prefer `search_code` over `Grep`."


def build_context(project_dir: str) -> str:
    """Gather project state and format it for injection into the session."""
    tausik_cmd = _tausik_path(project_dir)
    if not tausik_cmd:
        return ""

    status = _run_tausik(tausik_cmd, ["status"], project_dir)
    active = _run_tausik(
        tausik_cmd, ["task", "list", "--status", "active"], project_dir
    )
    blocked = _run_tausik(
        tausik_cmd, ["task", "list", "--status", "blocked"], project_dir
    )
    memory_block = _run_tausik(tausik_cmd, ["memory", "block"], project_dir)
    rag = _rag_summary(project_dir)

    parts = ["# TAUSIK Session Context (auto-injected)\n"]
    if status:
        parts.append(f"\n{status}\n")
    parts.append(f"\n{rag}\n")

    def _has_tasks(out: str) -> bool:
        return bool(out) and "(none)" not in out and "No tasks" not in out

    if _has_tasks(active):
        parts.append(f"\n## Active tasks\n```\n{active}\n```\n")
    if _has_tasks(blocked):
        parts.append(f"\n## Blocked tasks\n```\n{blocked}\n```\n")
    if memory_block:
        parts.append(f"\n{memory_block}\n")

    parts.append(
        "\n**Reminders:**\n"
        "- `task start <slug>` is required before any Write/Edit (SENAR Rule 9.1).\n"
        "- Run `/start` for the full dashboard (handoff, metrics, explorations, audit).\n"
        "- Log progress with `task log`; document dead ends with `dead-end`.\n"
        "- Project knowledge → `tausik memory add`, NOT `~/.claude/*/memory/` "
        "(blocked by PreToolUse hook; bypass only with `confirm: cross-project`).\n"
    )
    return "".join(parts)


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tausik_db = os.path.join(project_dir, ".tausik", "tausik.db")

    if not os.path.exists(tausik_db):
        return 0

    context = build_context(project_dir)
    if not context.strip():
        return 0

    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        pass

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
