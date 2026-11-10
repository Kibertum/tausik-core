"""Shared validation for the generated Codex authorization capability."""

from __future__ import annotations

import base64
import json
import os
import shlex
import subprocess

CAPABILITY_VERSION = 5
TRANSPORT_MODES = frozenset({"direct", "functions.exec"})


def _powershell_script(argv: list[str]) -> str:
    payload = base64.b64encode(
        json.dumps(argv, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return (
        f"$p='{payload}';$a=[Text.Encoding]::UTF8.GetString("
        "[Convert]::FromBase64String($p))|ConvertFrom-Json;"
        "& $a[0] $a[1..($a.Count-1)];exit $LASTEXITCODE"
    )


def serialize_hook_argv(argv: list[str], *, platform: str | None = None) -> str:
    """Serialize argv for the shell grammar used by the current Codex host."""
    selected = platform or os.name
    if selected != "nt":
        return shlex.join(argv)
    encoded = base64.b64encode(_powershell_script(argv).encode("utf-16-le")).decode("ascii")
    return subprocess.list2cmdline(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]
    )


def split_hook_command(command: str, *, platform: str | None = None) -> list[str]:
    """Parse the exact counterpart of :func:`serialize_hook_argv`."""
    selected = platform or os.name
    if selected == "nt":
        tokens = [token.strip("\"'") for token in shlex.split(command, posix=False)]
        if len(tokens) != 5 or tokens[:4] != [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
        ]:
            raise ValueError("unsupported Windows Codex hook command")
        script = base64.b64decode(tokens[4], validate=True).decode("utf-16-le")
        marker = "$p='"
        if not script.startswith(marker) or "';" not in script:
            raise ValueError("invalid encoded Windows Codex hook command")
        payload = script[len(marker) : script.index("';", len(marker))]
        argv = json.loads(base64.b64decode(payload, validate=True).decode("utf-8"))
        if not isinstance(argv, list) or not all(isinstance(value, str) for value in argv):
            raise ValueError("invalid Windows Codex hook argv")
        if script != _powershell_script(argv):
            raise ValueError("non-canonical Windows Codex hook command")
        return argv
    return shlex.split(command, posix=True)


def manifest_error(manifest: object) -> str | None:
    """Return a stable reason when a capability manifest is malformed or stale."""
    if not isinstance(manifest, dict):
        return "manifest is invalid"
    if manifest.get("capability_version") != CAPABILITY_VERSION:
        return "transport version is stale"
    modes = manifest.get("mcp_transport_modes")
    if not isinstance(modes, list) or not all(isinstance(mode, str) for mode in modes):
        return "transport modes are invalid"
    if not TRANSPORT_MODES.issubset(set(modes)):
        return "composite transport is absent"
    if not isinstance(manifest.get("adapters"), dict):
        return "adapter manifest is invalid"
    if (
        not isinstance(manifest.get("python_executable"), str)
        or not manifest["python_executable"].strip()
    ):
        return "hook interpreter is invalid"
    return None


def exact_hook_command(
    command: object,
    script_path: str,
    project_dir: str,
    python_executable: str,
    *,
    platform: str | None = None,
) -> bool:
    """Accept only the complete command grammar emitted by bootstrap."""
    try:
        tokens = split_hook_command(str(command), platform=platform)
    except ValueError:
        return False
    if len(tokens) != 6:
        return False
    actual_python = os.path.normcase(os.path.realpath(tokens[0]))
    expected_python = os.path.normcase(os.path.realpath(python_executable))
    if actual_python != expected_python:
        return False
    if tokens[1:3] != ["-X", "utf8"]:
        return False
    actual_script = os.path.normcase(os.path.realpath(tokens[3]))
    expected_script = os.path.normcase(os.path.realpath(script_path))
    if tokens[4] == "--trusted-host":
        return actual_script == expected_script and tokens[5] == "codex"
    if tokens[4] != "--project":
        return False
    actual_project = os.path.normcase(os.path.realpath(tokens[5]))
    expected_project = os.path.normcase(os.path.realpath(project_dir))
    return actual_script == expected_script and actual_project == expected_project
