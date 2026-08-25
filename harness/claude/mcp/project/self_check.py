"""TAUSIK MCP self-check — detect stale in-memory modules.

Sibling-MCP enumeration used to live here too, and the docstring said so —
two entities in one line, which convention #348 names as the sign of a bad
cut. It now lives in `sibling_mcp`; this module only ASKS it a question and
carries the answer into the report. The old names are deliberately NOT
re-exported: a test still patching `self_check._enumerate_sibling_mcps`
must fail loudly on the missing attribute rather than patch nothing.

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

# Плоский импорт, как у остальных модулей сервера. Каталог кладётся на путь
# ЗДЕСЬ, а не в `_eager_import_watch_list`: импорт соседа выполняется раньше
# любой функции этого файла, и полагаться на то, что путь уже пополнил кто-то
# другой, значит зависеть от порядка загрузки.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import sibling_mcp  # noqa: E402 — путь пополняется строкой выше

# --- Eager-import critical modules ----------------------------------------
#
# NOTE: this list does NOT define the WATCH set (that used to be its job and
# was the bug behind mcp-self-check-watches-eleven-modules-of-a-hundred: the
# server imports dozens of modules, any of which can go stale, and a hand
# list can never keep up). Its ONLY remaining responsibility is to *force*
# these service-layer modules to load at startup, so their file is resolvable
# in the startup snapshot even for tools that lazy-import them on first call.
# The observed set is asked of the PRODUCER — `sys.modules` filtered to the
# deployed server tree (see `_loaded_our_module_paths`) — not enumerated here.
_EAGER_IMPORT_MODULES: tuple[str, ...] = (
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

# Small float tolerance so filesystem/precision noise never reads as drift.
_MTIME_TOLERANCE = 0.001


def _ensure_scripts_dir_on_path() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    scripts = os.path.normpath(os.path.join(here, "..", "..", "scripts"))
    if os.path.isdir(scripts) and scripts not in sys.path:
        sys.path.insert(0, scripts)


def _server_roots() -> tuple[str, ...]:
    """The deployed subtrees whose modules we watch: `<profile>/scripts` and
    `<profile>/mcp`, derived from THIS file's location so the check follows
    the active IDE profile (`.claude`, `.cursor`, `.opencode`, ...).

    Deriving from `__file__` (not a hard path) means stdlib and
    site-packages modules fall OUTSIDE these roots by construction — so a
    `pip install` can never masquerade as MCP drift (AC5).
    """
    here = os.path.dirname(os.path.abspath(__file__))  # <profile>/mcp/project
    mcp_root = os.path.dirname(here)  # <profile>/mcp
    profile = os.path.dirname(mcp_root)  # <profile>
    scripts_root = os.path.join(profile, "scripts")
    return (
        os.path.normcase(os.path.abspath(scripts_root)),
        os.path.normcase(os.path.abspath(mcp_root)),
    )


def _is_under_roots(path: str, roots: tuple[str, ...]) -> bool:
    """True if `path` lives inside one of the server roots (prefix match on a
    path-separator boundary, case-normalised for Windows)."""
    p = os.path.normcase(os.path.abspath(path))
    for root in roots:
        r = root if root.endswith(os.sep) else root + os.sep
        if p == root or p.startswith(r):
            return True
    return False


def _module_path(name: str) -> str | None:
    mod = sys.modules.get(name)
    if mod is None:
        return None
    f = getattr(mod, "__file__", None)  # getattr is untyped → coerce to str below
    if not f:  # builtins, namespace packages → no __file__, silently skipped (AC5)
        return None
    return os.path.abspath(str(f))


def _loaded_our_module_paths(roots: tuple[str, ...] | None = None) -> dict[str, str]:
    """Ask the PRODUCER for the watch set: every currently-loaded module whose
    `__file__` lives under the deployed server tree. Replaces the old
    hand-maintained 11-name list, which went blind to every module outside it.
    """
    if roots is None:
        roots = _server_roots()
    out: dict[str, str] = {}
    # Snapshot the items first — sys.modules can mutate during iteration.
    for name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        try:
            path = os.path.abspath(f)
        except Exception:  # noqa: BLE001 — a broken __file__ must not crash the diagnostic
            continue
        if _is_under_roots(path, roots):
            out[name] = path
    return out


def _snapshot_module_mtimes() -> dict[str, float]:
    out: dict[str, float] = {}
    for _name, path in _loaded_our_module_paths().items():
        try:
            out[path] = os.path.getmtime(path)
        except Exception:  # noqa: BLE001 — deleted/racing file must not abort the snapshot
            continue
    return out


def _eager_import_watch_list() -> None:
    """Import every eager module so its `__file__` becomes resolvable.

    Wrapped in a single try/except — the MCP server must NOT crash on a
    missing optional service module. We just record the failure as a
    skipped entry; the snapshot dict will simply not contain that path.
    """
    _ensure_scripts_dir_on_path()
    # The two MCP-project-local ones live in this directory, not in scripts/.
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    for name in _EAGER_IMPORT_MODULES:
        try:
            __import__(name)
        except Exception:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
            # Stale modules are best-effort; skip failures silently.
            continue


def _compute_drift(
    snapshot: dict[str, float],
    startup_epoch: float,
    loaded_paths: dict[str, str],
    getmtime: Any,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Pure drift core (injectable `getmtime` for tests). Two sources:

    1. Modules present at startup whose file advanced since the snapshot
       (`edited-after-startup`).
    2. Modules loaded LAZILY after startup — absent from the snapshot — whose
       file mtime is later than the server boot time (`lazy-loaded-after-edit`).
       These were the permanent blind spot: they never appeared in the startup
       snapshot, so an edit to them was invisible forever. A file mtime past
       the boot time is treated conservatively as drift (AC3).

    Any `getmtime` failure on a single module is swallowed so one deleted or
    unreadable file can never turn the whole diagnostic into an exception (AC5).
    """
    drift: list[dict[str, Any]] = []
    current: dict[str, float] = {}

    def _record(path: str, baseline: float, reason: str) -> None:
        try:
            cur = getmtime(path)
        except Exception:  # noqa: BLE001 — one bad file must not crash self_check
            return
        current[path] = cur
        if cur > baseline + _MTIME_TOLERANCE:
            drift.append(
                {
                    "module": os.path.basename(path),
                    "path": path,
                    "snapshot_mtime": baseline,
                    "current_mtime": cur,
                    "delta_seconds": round(cur - baseline, 2),
                    "reason": reason,
                }
            )

    for path, snap_mtime in snapshot.items():
        _record(path, snap_mtime, "edited-after-startup")
    for _name, path in loaded_paths.items():
        if path in snapshot:
            continue
        _record(path, startup_epoch, "lazy-loaded-after-edit")
    return drift, current


def collect() -> dict[str, Any]:
    """Return diagnostic snapshot for `tausik_self_check`.

    `drift_detected` is the headline signal — when True, the running MCP
    server is executing stale Python bytecode and the user should restart
    the IDE before running heavy tools (`tausik_verify`, `tausik_task_done`).
    """
    # Ask the producer for the live watch set, then run the pure drift core.
    # Wrapped defensively: any failure here must degrade to "no drift found",
    # never crash the MCP server on a tool call (AC5).
    try:
        loaded = _loaded_our_module_paths()
    except Exception:  # noqa: BLE001
        loaded = {}
    drift, current = _compute_drift(
        _MODULE_MTIMES_AT_STARTUP, _STARTUP_TIME_EPOCH, loaded, os.path.getmtime
    )
    project_dir = os.getcwd()  # MCP server.main() pins cwd to --project
    # Defensive, like _loaded_our_module_paths above: the diagnostic must never
    # crash the MCP server on a tool call, so any failure in the (cached)
    # enumeration degrades to "unknown" (count == -1), not an exception (AC5).
    try:
        siblings = sibling_mcp._enumerate_sibling_mcps_cached(os.getpid(), project_dir)
    except Exception:  # noqa: BLE001 — enumeration failure → "unknown", never crash
        siblings = {"count": -1, "pids": [], "error": "sibling enumeration raised"}
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
    # Report-only accumulation warning (decision #189): above a threshold, the
    # sibling count is an actionable "close old sessions" signal — the framework
    # never kills a process, since a live sibling can't be told from a stale one.
    sibling_warning_msg = ""
    try:
        from mcp_reaper import sibling_warning

        sibling_warning_msg = sibling_warning(sibling_count)
    except Exception:  # noqa: BLE001 — a missing helper must not break the diagnostic
        sibling_warning_msg = ""
    if sibling_warning_msg:
        remediation = f"{sibling_warning_msg} {remediation}"
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
        "sibling_warning": sibling_warning_msg,
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
