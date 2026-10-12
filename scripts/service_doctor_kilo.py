"""Kilo Code MCP-config validation for `tausik doctor` (v156 P3, probed since 1.11.2).

Runs only when a project looks like a Kilo install (a `.kilo/` or `.kilocode/`
dir exists). Validates the MCP stanza TAUSIK writes via bootstrap_kilo: a
top-level ``mcp`` key mapping server names to
``{type, command:[python, server.py, "--project", <abs-project>], enabled}``.

Two layers. Structural: the config parses, names the server, points at real
files, and carries no ``${workspaceFolder}`` — Kilo 7.8.3 does not expand that
variable in MCP commands (measured: zero literals in its ``kilo.exe``), so a
relative stanza is dead at spawn even though it parses. Live: an initialize
handshake against the configured command, because "the file parses" and "the
host can load the server" are different claims; only the second one is worth a
checkmark. No live Kilo build is needed — the probe runs the same command the
host would run.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import threading

from jsonc_utils import load_jsonc as _load_jsonc

# Same two paths bootstrap_kilo writes (Decision #120).
_KILO_CONFIGS = (
    os.path.join(".kilo", "kilo.jsonc"),
    os.path.join(".kilocode", "mcp.json"),
)

_PROJECT_SERVER = "tausik-project"
_RESTART_HINT = "then restart Kilo so it reloads MCP servers"
_WS_VAR = "${workspaceFolder}"
_PROBE_LABEL = "Kilo MCP live probe"
_PROBE_TIMEOUT_S = 25.0


def is_kilo_project(project_dir: str) -> bool:
    """True when the project carries Kilo config dirs (so the check should run)."""
    return os.path.isdir(os.path.join(project_dir, ".kilo")) or os.path.isdir(
        os.path.join(project_dir, ".kilocode")
    )


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

    legacy = [str(c) for c in command if _WS_VAR in str(c)]
    if legacy:
        return (
            "warn",
            label,
            f"command uses {_WS_VAR} which Kilo does not expand in MCP commands "
            f"(measured: zero occurrences of the literal in Kilo 7.8.3 kilo.exe) — "
            f"the server cannot start; re-run `bootstrap --ide kilo` for absolute paths, "
            f"{_RESTART_HINT}",
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

    return ("ok", label, f"valid — `{_PROJECT_SERVER}` MCP stanza parses, paths exist")


def probe_mcp_server(
    command: list[str],
    project_dir: str,
    timeout: float = _PROBE_TIMEOUT_S,
    expected_name: str = _PROJECT_SERVER,
) -> tuple[bool, str]:
    """Run the configured MCP command and perform an initialize handshake.

    Returns (ok, detail). This is the check that separates "the config parses"
    from "the host can load the server": a dead spawn (wrong interpreter, a
    variable the host never expands, a crashing server) answers here, where the
    structural check cannot. The child is terminated before returning.
    """
    cmd = [str(c).replace(_WS_VAR, project_dir) for c in command]
    request = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "tausik-doctor", "version": "1"},
            },
        }
    )
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=project_dir,
        )
    except OSError as e:
        return False, f"spawn failed: {e}"

    try:
        if proc.stdin is None or proc.stdout is None:
            raise OSError("pipes unavailable")
        proc.stdin.write(request + "\n")
        proc.stdin.flush()
    except Exception as e:  # noqa: BLE001 — a broken pipe is a probe finding
        with contextlib.suppress(Exception):
            proc.terminate()
            proc.wait(timeout=5)
        return False, f"failed to send initialize: {e}"

    box: dict[str, str] = {}

    def _read() -> None:
        try:
            box["line"] = proc.stdout.readline()  # type: ignore[union-attr]
        except Exception as e:  # noqa: BLE001 — a dead pipe is a probe finding
            box["error"] = str(e)

    reader = threading.Thread(target=_read, daemon=True)
    reader.start()
    reader.join(timeout)
    with contextlib.suppress(Exception):
        proc.terminate()
        proc.wait(timeout=5)

    line = box.get("line", "")
    if not line.strip():
        if "error" in box:
            return False, f"no initialize response (read error: {box['error']})"
        return False, f"no initialize response within {timeout:.0f}s"
    try:
        resp = json.loads(line)
        info = resp["result"]["serverInfo"]
        name = str(info.get("name", ""))
        version = str(info.get("version", "?"))
    except Exception as e:  # noqa: BLE001 — malformed reply is a finding
        return False, f"unreadable initialize response: {e}: {line[:120]!r}"
    if name != expected_name:
        return False, f"unexpected server name {name!r} (expected {expected_name!r})"
    return True, f"initialize handshake OK ({name} {version})"


def _probe_finding(path: str, project_dir: str) -> tuple[str, str, str]:
    """Probe the tausik-project command from one config file. Never raises."""
    try:
        data = _load_jsonc(path)
        command = data["mcp"][_PROJECT_SERVER]["command"]
        if not isinstance(command, list) or len(command) < 2:
            raise ValueError("command is not an array")
    except Exception as e:  # noqa: BLE001 — structural layer already reported it
        return ("warn", _PROBE_LABEL, f"skipped — config unreadable for probing: {e}")
    ok, detail = probe_mcp_server([str(c) for c in command], project_dir)
    if ok:
        return ("ok", _PROBE_LABEL, detail)
    return (
        "warn",
        _PROBE_LABEL,
        f"{detail} — the declared command cannot serve MCP; fix per the Kilo config "
        f"findings above, {_RESTART_HINT}",
    )


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
    findings = [_validate_one(p, rel, project_dir) for rel, p in present]
    # One live probe against the first structurally-clean config. A parse-only
    # ✓ is exactly the overclaim this probe exists to refuse.
    clean = [p for (sev, _, _), (_, p) in zip(findings, present) if sev == "ok"]
    if clean:
        findings.append(_probe_finding(clean[0], project_dir))
    return findings
