"""TAUSIK MCP self-check — detect stale in-memory modules + sibling MCP servers.

Background: gotchas #77, #79, #80 describe `tausik_verify` and
`tausik_task_done` hanging silently when the running MCP project server
holds stale Python modules — usually because the user (or bootstrap)
edited `scripts/service_verification.py`, `scripts/gate_runner.py`, or
similar service code AFTER the MCP server booted, and the IDE never
respawned the server. The CLI (`.tausik/tausik`) reloads from disk every
invocation, so it doesn't share the issue.

This module captures a snapshot of watched-module mtimes at MCP server
startup, then exposes a `collect()` helper the `tausik_self_check` tool
calls to compare against the current on-disk mtimes. Drift = the MCP is
running stale code; the agent should warn the user to restart the IDE.

Eager import: the constants block at the bottom of this file imports the
service modules we watch. That forces them to load under the MCP server
process at startup so we can snapshot whatever MCP will actually call into
later — even tools that lazy-import on first invocation. Without that, a
module loaded later (e.g. on first `tausik_verify`) would already match
the on-disk file by definition, masking real drift.
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
from typing import Any

# --- Watched modules ------------------------------------------------------
#
# Files whose mtime advancing after MCP startup indicates the running
# server has stale in-memory code. The list is intentionally narrow —
# every entry should be a service-layer module that participates in the
# `tausik_verify` / `task_done` paths where stale code has caused silent
# hangs in the past. Adding modules here pays a small startup cost; do not
# add UI/skill/test files.
_WATCHED_MODULES: tuple[str, ...] = (
    "service_verification",
    "verify_cache",
    "security_pattern",
    "gate_runner",
    "gate_command_runner",
    "service_gates",
    "service_task",
    "project_service",
    "project_backend",
    "handlers",
    "handlers_skill",
)

_STARTUP_TIME_ISO: str = ""
_STARTUP_TIME_EPOCH: float = 0.0
_MODULE_MTIMES_AT_STARTUP: dict[str, float] = {}


def _ensure_scripts_dir_on_path() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    scripts = os.path.normpath(os.path.join(here, "..", "..", "scripts"))
    if os.path.isdir(scripts) and scripts not in sys.path:
        sys.path.insert(0, scripts)


def _module_path(name: str) -> str | None:
    mod = sys.modules.get(name)
    if mod is None:
        return None
    f = getattr(mod, "__file__", None)
    if not f:
        return None
    return os.path.abspath(f)


def _snapshot_module_mtimes() -> dict[str, float]:
    out: dict[str, float] = {}
    for name in _WATCHED_MODULES:
        path = _module_path(name)
        if not path:
            continue
        try:
            out[path] = os.path.getmtime(path)
        except OSError:
            continue
    return out


def _eager_import_watch_list() -> None:
    """Import every watched module so its `__file__` becomes resolvable.

    Wrapped in a single try/except — the MCP server must NOT crash on a
    missing optional service module. We just record the failure as a
    skipped entry; the snapshot dict will simply not contain that path.
    """
    _ensure_scripts_dir_on_path()
    # The two MCP-project-local ones live in this directory, not in scripts/.
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    for name in _WATCHED_MODULES:
        try:
            __import__(name)
        except Exception:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
            # Stale modules are best-effort; skip failures silently.
            continue


def _enumerate_sibling_mcps(self_pid: int, project_dir: str) -> dict[str, Any]:
    """Best-effort sibling enumeration. Returns `{count, pids, error}`.

    `count == -1` means we could not introspect — the agent should treat
    this as "unknown, check manually" rather than "no siblings".

    v14b-defect-mcp-self-check-venv-launcher: also exclude the direct
    parent PID. On Windows, `venv\\Scripts\\python.exe` is a launcher
    shim that re-execs the real interpreter as a child while keeping the
    same command line; the parent process matches the same needle/project
    filter as the child and would otherwise count as a "sibling MCP",
    producing a chronic +1 false-positive that masquerades as a real
    leak. POSIX rarely shows the same shape (venv usually returns the
    interpreter's PID directly), but `os.getppid()` works on all
    platforms so the guard is uniform.
    """
    needle = "mcp/project/server.py"
    project_norm = os.path.normpath(project_dir)
    pids: list[int] = []
    err: str | None = None
    try:
        parent_pid = os.getppid()
    except Exception:  # noqa: BLE001
        parent_pid = -1  # never matches a real PID — guard becomes a no-op
    if sys.platform == "win32":
        # Two introspection paths in priority order:
        #   1. wmic.exe — present on legacy Windows / older Win11 builds
        #   2. PowerShell `Get-CimInstance Win32_Process` — modern Windows
        #      (Win11 24H2+ removed wmic from the base image)
        # Each fallback ONLY fires when the prior one raised FileNotFoundError
        # (binary missing). Real failures (permission, hang) propagate as the
        # `err` string and stop the chain — we do not paper over genuine
        # errors with the next backend.
        import subprocess

        wmic_used = False
        try:
            r = subprocess.run(
                [
                    "wmic",
                    "process",
                    "where",
                    "name='python.exe'",
                    "get",
                    "ProcessId,CommandLine",
                    "/FORMAT:CSV",
                ],
                capture_output=True,
                text=True,
                timeout=4,
            )
            wmic_used = True
            for line in r.stdout.splitlines():
                if needle not in line:
                    continue
                parts = line.rsplit(",", 1)
                if len(parts) != 2:
                    continue
                cmd, raw_pid = parts
                try:
                    pid = int(raw_pid.strip())
                except ValueError:
                    continue
                if pid == self_pid or pid == parent_pid:
                    continue
                if project_norm.replace("\\", "/").lower() in cmd.replace("\\", "/").lower():
                    pids.append(pid)
        except FileNotFoundError:
            # wmic absent → try PowerShell.
            try:
                ps_query = (
                    "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | "
                    'ForEach-Object { "$($_.ProcessId)|$($_.CommandLine)" }'
                )
                r = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        ps_query,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                for line in r.stdout.splitlines():
                    if needle not in line:
                        continue
                    raw_pid, _, cmd = line.partition("|")
                    try:
                        pid = int(raw_pid.strip())
                    except ValueError:
                        continue
                    if pid == self_pid or pid == parent_pid:
                        continue
                    if project_norm.replace("\\", "/").lower() in cmd.replace("\\", "/").lower():
                        pids.append(pid)
            except FileNotFoundError as e:
                err = f"wmic and powershell both missing: {e}"
            except Exception as e:  # noqa: BLE001
                err = f"powershell Get-CimInstance failed: {e}"
        except Exception as e:  # noqa: BLE001
            if wmic_used:
                err = f"wmic introspection failed: {e}"
            else:
                err = f"wmic startup failed: {e}"
    else:
        # POSIX: prefer /proc, fall back to ps.
        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                if pid == self_pid or pid == parent_pid:
                    continue
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmdline = f.read().decode("utf-8", errors="replace")
                except OSError:
                    continue
                if needle in cmdline and project_norm in cmdline:
                    pids.append(pid)
        except FileNotFoundError:
            try:
                import subprocess

                r = subprocess.run(
                    ["ps", "-A", "-o", "pid=,command="],
                    capture_output=True,
                    text=True,
                    timeout=4,
                )
                for line in r.stdout.splitlines():
                    if needle not in line or project_norm not in line:
                        continue
                    parts = line.strip().split(None, 1)
                    if len(parts) < 2:
                        continue
                    try:
                        pid = int(parts[0])
                    except ValueError:
                        continue
                    if pid != self_pid and pid != parent_pid:
                        pids.append(pid)
            except Exception as e:  # noqa: BLE001
                err = f"ps fallback failed: {e}"
        except Exception as e:  # noqa: BLE001
            err = f"/proc walk failed: {e}"
    return {
        "count": len(pids) if err is None else -1,
        "pids": pids,
        "error": err,
    }


def collect() -> dict[str, Any]:
    """Return diagnostic snapshot for `tausik_self_check`.

    `drift_detected` is the headline signal — when True, the running MCP
    server is executing stale Python bytecode and the user should restart
    the IDE before running heavy tools (`tausik_verify`, `tausik_task_done`).
    """
    drift: list[dict[str, Any]] = []
    current: dict[str, float] = {}
    for path, snap_mtime in _MODULE_MTIMES_AT_STARTUP.items():
        try:
            cur = os.path.getmtime(path)
        except OSError:
            continue
        current[path] = cur
        if cur > snap_mtime + 0.001:  # tolerate float-precision noise
            drift.append(
                {
                    "module": os.path.basename(path),
                    "path": path,
                    "snapshot_mtime": snap_mtime,
                    "current_mtime": cur,
                    "delta_seconds": round(cur - snap_mtime, 2),
                }
            )
    project_dir = os.getcwd()  # MCP server.main() pins cwd to --project
    siblings = _enumerate_sibling_mcps(os.getpid(), project_dir)
    sibling_count = siblings["count"]
    # Three remediation states:
    #   - drift OR confirmed sibling leak (count > 0) → "Restart IDE"
    #   - introspection failed (count == -1) → tell user the drift check is
    #     still valid; sibling check is unavailable on this host
    #   - clean (drift=False, count == 0) → "no action needed"
    if drift or (isinstance(sibling_count, int) and sibling_count > 0):
        remediation = (
            "Restart your IDE so the MCP project server respawns with fresh "
            "modules. Then re-run /start. Until then, prefer the CLI: "
            "`.tausik/tausik verify --task <slug>` and "
            "`.tausik/tausik task done <slug> --ac-verified`."
        )
    elif sibling_count == -1:
        remediation = (
            "MCP modules in sync (drift check passed). Sibling-MCP check "
            "unavailable on this host — drift check still active and is "
            "the primary signal."
        )
    else:
        remediation = "MCP modules in sync; no action needed."
    return {
        "server": "tausik-project",
        "pid": os.getpid(),
        "startup_time_iso": _STARTUP_TIME_ISO,
        "watched_modules_count": len(_MODULE_MTIMES_AT_STARTUP),
        "watched_modules": dict(_MODULE_MTIMES_AT_STARTUP),
        "current_mtimes": current,
        "drift_detected": bool(drift),
        "stale_modules": drift,
        "sibling_mcp_count": sibling_count,
        "sibling_mcp_pids": siblings["pids"],
        "sibling_introspection_error": siblings["error"],
        "remediation": remediation,
    }


# --- Eager startup snapshot ------------------------------------------------
# Run at import time so server.py only needs to `import self_check` once
# (before entering the JSON-RPC loop) to capture the baseline. The order
# is: eager-import watch list, then snapshot — both must complete before
# any tool can be invoked.
_eager_import_watch_list()
_MODULE_MTIMES_AT_STARTUP = _snapshot_module_mtimes()
_STARTUP_TIME_EPOCH = _dt.datetime.now(_dt.timezone.utc).timestamp()
_STARTUP_TIME_ISO = _dt.datetime.fromtimestamp(_STARTUP_TIME_EPOCH, _dt.timezone.utc).isoformat()
