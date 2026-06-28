"""Kilo Code MCP-config validation for `tausik doctor` (v156 P3).

Runs only when a project looks like a Kilo install (a `.kilo/` or `.kilocode/`
dir exists). Validates the MCP stanza TAUSIK writes via bootstrap_kilo: a
top-level ``mcp`` key mapping server names to
``{type, command:[python, server.py, "--project", "${workspaceFolder}"], enabled}``.

Structural validation only — it confirms the config Kilo will read is well-formed
and points at a real server.py; it does NOT need a live Kilo build. `${workspaceFolder}`
is resolved to the project dir (Kilo expands it at launch).
"""

from __future__ import annotations

import json
import os
import re

# Same two paths bootstrap_kilo writes (Decision #120).
_KILO_CONFIGS = (
    os.path.join(".kilo", "kilo.jsonc"),
    os.path.join(".kilocode", "mcp.json"),
)

_PROJECT_SERVER = "tausik-project"
_RESTART_HINT = "then restart Kilo so it reloads MCP servers"

# Best-effort JSONC comment stripping: Kilo tolerates // and /* */ comments;
# json.loads does not. We only fall back to this when strict parsing fails.
_LINE_COMMENT = re.compile(r"(?m)^[ \t]*//.*?$")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def is_kilo_project(project_dir: str) -> bool:
    """True when the project carries Kilo config dirs (so the check should run)."""
    return os.path.isdir(os.path.join(project_dir, ".kilo")) or os.path.isdir(
        os.path.join(project_dir, ".kilocode")
    )


def _load_jsonc(path: str) -> dict:
    """Parse a (possibly JSONC) config file. Raises ValueError if unparseable."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        stripped = _BLOCK_COMMENT.sub("", _LINE_COMMENT.sub("", raw))
        stripped = _TRAILING_COMMA.sub(r"\1", stripped)
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as e:
            raise ValueError(str(e)) from e
    if not isinstance(data, dict):
        raise ValueError("top-level value is not a JSON object")
    return data


def _resolve_ws(value: str, project_dir: str) -> str:
    """Expand Kilo's ${workspaceFolder} placeholder to the project dir."""
    return value.replace("${workspaceFolder}", project_dir)


def _validate_one(path: str, rel: str, project_dir: str) -> tuple[str, str, str]:
    """Validate a single Kilo config file. Returns (severity, label, detail).

    severity ∈ {"ok", "warn", "fail"}. Never raises — a broken config is a
    diagnostic finding, not a doctor crash.
    """
    label = f"Kilo config ({rel})"
    try:
        data = _load_jsonc(path)
    except (ValueError, OSError) as e:
        return (
            "fail",
            label,
            f"invalid JSON/JSONC: {e} — re-run `bootstrap --ide kilo`, {_RESTART_HINT}",
        )

    mcp = data.get("mcp")
    if not isinstance(mcp, dict) or not mcp:
        return ("warn", label, f"no `mcp` stanza — re-run `bootstrap --ide kilo`, {_RESTART_HINT}")

    server = mcp.get(_PROJECT_SERVER)
    if not isinstance(server, dict):
        return (
            "warn",
            label,
            f"`{_PROJECT_SERVER}` server missing from `mcp` — re-run `bootstrap --ide kilo`, {_RESTART_HINT}",
        )

    command = server.get("command")
    if not isinstance(command, list) or len(command) < 2:
        return (
            "fail",
            label,
            f"`{_PROJECT_SERVER}.command` must be an array [python, server.py, ...] — "
            f"re-run `bootstrap --ide kilo`, {_RESTART_HINT}",
        )

    server_py = _resolve_ws(str(command[1]), project_dir)
    if not os.path.isfile(server_py):
        return (
            "warn",
            label,
            f"server.py not found at {server_py} — re-run `bootstrap --ide kilo`, {_RESTART_HINT}",
        )

    # python (command[0]): only flag an in-project/absolute interpreter that is
    # missing. A bare "python" relies on PATH — out of scope to resolve here.
    python_exe = _resolve_ws(str(command[0]), project_dir)
    if (os.path.isabs(python_exe) or os.sep in python_exe) and not os.path.isfile(python_exe):
        return (
            "warn",
            label,
            f"python not found at {python_exe} — re-run `bootstrap`, {_RESTART_HINT}",
        )

    if server.get("enabled") is False:
        return (
            "warn",
            label,
            f"`{_PROJECT_SERVER}` is disabled (`enabled:false`) — set true, {_RESTART_HINT}",
        )

    return ("ok", label, f"valid — `{_PROJECT_SERVER}` MCP stanza resolves")


def check_kilo_config(project_dir: str) -> list[tuple[str, str, str]]:
    """Return doctor findings for the Kilo MCP config, or [] for non-Kilo projects.

    Each finding is (severity, label, detail) with severity ∈ {ok, warn, fail}.
    """
    if not is_kilo_project(project_dir):
        return []

    existing = [(rel, os.path.join(project_dir, rel)) for rel in _KILO_CONFIGS]
    present = [(rel, p) for rel, p in existing if os.path.isfile(p)]
    if not present:
        return [
            (
                "warn",
                "Kilo MCP config",
                f"`.kilo/`/`.kilocode/` present but no {', '.join(_KILO_CONFIGS)} — "
                f"run `bootstrap --ide kilo`, {_RESTART_HINT}",
            )
        ]
    return [_validate_one(p, rel, project_dir) for rel, p in present]
