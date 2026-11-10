#!/usr/bin/env python3
"""SessionStart hook: auto-inject TAUSIK project state into new Claude Code sessions.

Eliminates the need for manual /start — agent sees active tasks, blockers,
and session warnings as part of the initial conversation context.

Exit code 0 always (graceful degradation). Output: Claude Code hookSpecificOutput JSON.
Skipped via TAUSIK_SKIP_HOOKS=1 env var.
"""

import hashlib
import json
import os
import subprocess
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HOOKS_DIR, os.path.dirname(_HOOKS_DIR)]

from _common import profile_dir as _common_profile_dir  # noqa: E402
from _common import tausik_path as _tausik_path  # noqa: E402
from codex_capability import exact_hook_command, manifest_error  # noqa: E402
from cursor_capability import cursor_preflight_hooks_ready  # noqa: E402

MAX_CONTEXT_BYTES = 2_048


def _run_tausik(cmd: str, args: list[str], project_dir: str, timeout: int = 4) -> str:
    """Run tausik CLI; return stdout on success, empty string on any failure."""
    try:
        result = subprocess.run(
            [cmd, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=project_dir,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def _profile_dir() -> str | None:
    """The IDE profile directory this hook is deployed inside, or None.

    Delegates to `_common.profile_dir` — the self-location and its marker logic
    (hardened by s130-review-fixes) live in one place so they cannot drift
    between the hooks that need them. `_common` sits in the same `hooks/` dir,
    so it locates the same profile this hook was deployed into.
    """
    return _common_profile_dir()


def _rag_server_path(project_dir: str) -> str | None:
    """Path to the codebase-rag MCP rag_server.py if installed, else None."""
    profile = _profile_dir()
    if profile:
        p = os.path.join(profile, "mcp", "codebase-rag", "rag_server.py")
        if os.path.exists(p):
            return p
    for ide in ("claude", "cursor"):
        # `ide` was previously unused in this branch — the literal below read
        # `.claude` on both iterations, so the cursor pass tested the same path
        # twice and only the harness fallback below ever varied.
        p = os.path.join(project_dir, f".{ide}", "mcp", "codebase-rag", "rag_server.py")
        if os.path.exists(p):
            return p
        p2 = os.path.join(project_dir, "harness", ide, "mcp", "codebase-rag", "rag_server.py")
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


def _auto_rebuild_skills(project_dir: str) -> None:
    """Best-effort skill profile pre-merge on session start.

    Resolves (ide, model) via env > config.json > auto-detect, then writes
    merged SKILL.md files when the sha256 differs from what's already on
    disk. Cache hit = no-op (microseconds). Never raises, never blocks.
    """
    try:
        profile = _profile_dir()
        scripts_dir = (
            os.path.join(profile, "scripts")
            if profile
            else os.path.join(project_dir, ".claude", "scripts")
        )
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import json as _json

        from skill_profile_rebuild import rebuild_skills  # type: ignore[import-not-found]
        from skill_profile_session import (  # type: ignore[import-not-found]
            load_session_state,
            now_iso,
            resolve_profile,
            save_session_state,
        )

        from tausik_utils import tausik_config_path  # type: ignore[import-not-found]

        cfg_path = tausik_config_path(project_dir)
        cfg: dict = {}
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, encoding="utf-8") as f:
                    cfg = _json.load(f) or {}
            except Exception:  # noqa: BLE001 — best-effort: a hook must never break the tool call it guards
                cfg = {}

        ide, model, source = resolve_profile(cfg)

        tausik_dir = os.path.join(project_dir, ".tausik")
        state = load_session_state(tausik_dir)
        if state.get("ide") == ide and state.get("model") == model:
            return  # cache hit — disk already merged for this combination

        profile = _profile_dir()
        skills_dst = os.path.join(
            profile if profile else os.path.join(project_dir, ".claude"), "skills"
        )
        if not os.path.isdir(skills_dst):
            return
        rebuild_skills(skills_dst, ide=ide, model=model, force=False)
        state.update({"ide": ide, "model": model, "source": source, "last_rebuild_at": now_iso()})
        save_session_state(tausik_dir, state)
    except Exception:  # noqa: BLE001 — best-effort: a hook must never break the tool call it guards
        return  # SessionStart must never block


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
            row = conn.execute("SELECT COUNT(*) FROM rag_chunks").fetchone()
            chunks = int(row[0]) if row else 0
    except sqlite3.OperationalError as exc:
        # A missing table is a real schema bug (issue #2) — surface it. Other
        # OperationalErrors (e.g. "unable to open database file") are
        # infrastructure problems, not schema drift — keep the generic message.
        if "no such table" in str(exc).lower():
            return f"RAG: schema error ({exc})."
        return "RAG: status unknown (db unreadable)."
    except Exception:  # noqa: BLE001 — best-effort: a hook must never break the tool call it guards
        return "RAG: status unknown (db unreadable)."
    # Always kick off an incremental reindex in the background so the index
    # picks up any commits made between sessions. Cheap when nothing changed
    # (early-return inside index_incremental on same `last_commit`).
    _spawn_background_reindex(project_dir, mode="incremental")
    if chunks == 0:
        return "RAG: empty — full reindex spawned in background."
    return f"RAG: {chunks} chunks indexed (incremental reindex running in background)."


def build_context(project_dir: str) -> str:
    """Gather project state and format it for injection into the session."""
    tausik_cmd = _tausik_path(project_dir)
    if not tausik_cmd:
        return ""

    status = _run_tausik(tausik_cmd, ["status", "--compact"], project_dir)
    rag = _rag_summary(project_dir)

    parts = ["# TAUSIK Session Contract\n"]
    if status:
        parts.append(f"{status}\n")

    contract = (
        "**Reminders:** SENAR Rule 9.1: define goal+AC and run `task start` before edits; "
        "log material progress; "
        "run `verify` and record AC evidence before `task done --ac-verified`.\n"
        "Load work context with `task show <slug> --package` (MCP: "
        "`tausik_task_show` mode=package); use `/start` for the dashboard.\n"
        "- Project knowledge → `tausik memory add`, NOT `~/.claude/*/memory/` "
        "(blocked by PreToolUse hook; bypass only with `confirm: cross-project`).\n"
    )
    prefix = "".join(parts)
    required = prefix + contract
    if len(required.encode()) > MAX_CONTEXT_BYTES:
        return required + "OVERFLOW: required session contract exceeds budget; nothing truncated.\n"
    candidate = prefix + f"{rag}\n" + contract
    if len(candidate.encode()) <= MAX_CONTEXT_BYTES:
        return candidate
    return required + "OMITTED: optional RAG status exceeded the context budget.\n"


def _open_host_session(
    project_dir: str, payload: object, *, trusted_host: str | None = None
) -> str | None:
    """The TAUSIK session IS the host session (decision #376): open it here.

    Idempotent per host session id — SessionStart fires again on resume and
    after compaction with the same id, and those must not open a second row.
    A payload without an id (another host, a manual run) opens nothing: the
    CLI path `tausik session start` remains for hosts without the event.
    A release refusal becomes additional context so the host does not treat a
    missing TAUSIK session as permission to work outside governance.
    """
    if trusted_host not in {"codex", "cursor"}:
        return _open_legacy_host_session(project_dir, payload)
    return _issue_execution_lease(project_dir, payload, trusted_host=trusted_host)


def _open_legacy_host_session(project_dir: str, payload: object) -> str | None:
    """Preserve the shared Claude/Qwen lifecycle; it does not mint Codex authority."""

    host_id = payload.get("session_id") if isinstance(payload, dict) else None
    if not isinstance(host_id, str) or not host_id.strip():
        return None
    tausik_cmd = _tausik_path(project_dir)
    if not tausik_cmd:
        return None
    try:
        result = subprocess.run(
            [tausik_cmd, "session", "start", "--host-id", host_id.strip()],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
            cwd=project_dir,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return f"TAUSIK SESSION NOT OPENED: version check could not finish ({type(exc).__name__})."
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "session start refused"
        return f"TAUSIK SESSION START REFUSED. {detail} Do not begin project work."
    warning = result.stderr.strip()
    return f"TAUSIK SESSION OPENED WITH WARNING. {warning}" if warning else None


def _codex_preflight_hooks_ready(project_dir: str) -> bool:
    """Attest that the profile which requests authority has both security adapters."""
    path = os.path.join(project_dir, ".codex", "hooks.json")
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError, TypeError):
        return False
    manifest_path = os.path.join(project_dir, ".codex", "tausik-capability.json")
    try:
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError, TypeError):
        return False
    if not isinstance(manifest, dict) or manifest_error(manifest) is not None:
        return False
    hooks_root = os.path.realpath(os.path.join(project_dir, ".codex", "scripts", "hooks"))

    def ready(event: str, script: str) -> bool:
        expected = os.path.join(hooks_root, script)
        if not os.path.isfile(expected):
            return False
        try:
            with open(expected, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
        except OSError:
            return False
        if manifest["adapters"].get(script) != digest:
            return False
        commands = [
            str(hook.get("command", ""))
            for entry in payload.get("hooks", {}).get(event, [])
            if isinstance(entry, dict) and entry.get("matcher") == ""
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict) and hook.get("type") == "command"
        ]
        for command in commands:
            if exact_hook_command(command, expected, project_dir, manifest["python_executable"]):
                return True
        return False

    parser = os.path.join(hooks_root, "codex_composite_mcp.py")
    try:
        with open(parser, "rb") as fh:
            parser_digest = hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return False
    return (
        manifest["adapters"].get("codex_composite_mcp.py") == parser_digest
        and ready("PreToolUse", "codex_write_gate.py")
        and ready("PostToolUse", "memory_preflight_posttool.py")
        and ready("UserPromptSubmit", "user_prompt_submit.py")
        and ready("Stop", "can_stop_gate.py")
    )


def _issue_execution_lease(project_dir: str, payload: object, *, trusted_host: str) -> str | None:
    """Issue only from this trusted SessionStart boundary; never from MCP/CLI."""

    if not isinstance(payload, dict):
        return "TAUSIK EXECUTION LEASE REFUSED. IDENTITY_MISSING: invalid hook payload."
    db_path = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.isfile(db_path):
        return None
    if os.path.isfile(os.path.join(project_dir, ".tausik", "execution-lease-maintenance")):
        return (
            "TAUSIK EXECUTION LEASE REFUSED. LEASE_MAINTENANCE: a prior PostToolUse "
            "audit could not persist; owner recovery is required. Do not begin project work."
        )
    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        from project_backend import SQLiteBackend
        from project_service import ProjectService
        from service_execution_lease import (
            assertion_from_session_start,
            enter_execution_lease_maintenance,
            issue_execution_lease,
            reconcile_execution_lease_state,
        )
        from service_host_context import enforce_hard_ceiling

        assertion_payload = dict(payload)
        backend = SQLiteBackend(db_path)
        try:
            assertion = assertion_from_session_start(
                assertion_payload, project_dir, trusted_host=trusted_host
            )
            svc = ProjectService(backend)
            ready = (
                _codex_preflight_hooks_ready(project_dir)
                if trusted_host == "codex"
                else cursor_preflight_hooks_ready(project_dir)
            )
            if not ready:
                enter_execution_lease_maintenance(
                    svc, f"{trusted_host} protected-action hook capability is missing or stale"
                )
                return (
                    "TAUSIK EXECUTION LEASE REFUSED. CAPABILITY_MISMATCH: "
                    f"{trusted_host} protected-action hooks are missing or stale. "
                    "Do not begin project work."
                )
            ceiling = enforce_hard_ceiling(svc, host=trusted_host, thread_id=assertion.thread_id)
            if ceiling is not None:
                return (
                    "TAUSIK EXECUTION LEASE REFUSED. HOST_CONTEXT_HARD: "
                    "checkpoint saved; continue in a fresh host thread."
                )
            reconcile_execution_lease_state(svc, assertion)
            lease = issue_execution_lease(
                svc,
                assertion,
            )
        finally:
            backend.close()
    except Exception as exc:  # noqa: BLE001 - trusted boundary fails closed with a typed notice
        if hasattr(exc, "code"):
            return f"TAUSIK EXECUTION LEASE REFUSED. {exc} Do not begin project work."
        return (
            "TAUSIK EXECUTION LEASE REFUSED. LEASE_INTERNAL: "
            f"{type(exc).__name__}. Do not begin project work."
        )
    return (
        "TAUSIK EXECUTION LEASE ISSUED. "
        f"thread_id={lease['thread_id']} expires_at={lease['expires_at']}. "
        "The trusted PreToolUse adapter binds mutations; no bearer token is exposed."
    )


def main() -> int:
    # hook-stderr-encoding-locale-dependent: this hook's messages contain
    # non-ASCII, and their readability must not depend on how it was
    # launched. Local import: hooks/ is sys.path[0] only when run as a script.
    from _common import force_utf8_io

    force_utf8_io()

    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    import argparse

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--trusted-host")
    args, _ = parser.parse_known_args()
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tausik_db = os.path.join(project_dir, ".tausik", "tausik.db")

    if not os.path.exists(tausik_db):
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        payload = {}
    session_notice = _open_host_session(project_dir, payload, trusted_host=args.trusted_host)
    if session_notice and "REFUSED" in session_notice:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": session_notice,
                    }
                }
            )
        )
        return 0

    _auto_rebuild_skills(project_dir)
    context = build_context(project_dir)
    if session_notice:
        context = f"{session_notice}\n{context}"
    if not context.strip():
        return 0

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
