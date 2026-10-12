"""OpenCode config validation for `tausik doctor` (v1.7.0).

Runs only when a project looks like an OpenCode install (`.opencode/` exists).
Structural validation only — no live OpenCode build required.

Each check below corresponds to a way the host actually died, or silently
under-enforced, in the incident that produced OpenCode support:

  * `tools` as an OBJECT -> ConfigInvalidError at startup, host unusable. The key
    is boolean-only. TAUSIK never writes it, but a hand-edit (or an agent trying to
    "help") can, and the resulting error message points nowhere near the cause.
  * QG-0 plugin missing, or sitting in a SINGULAR `.opencode/plugin/` -> no error,
    no warning, no enforcement. Writes proceed with no active task and nobody
    notices. A silent bypass is the worst outcome in this framework.
  * `instructions` missing or pointing at a file that does not exist -> the rules
    are simply never loaded, and the agent free-styles.
"""

from __future__ import annotations

import json
import os

_CONFIG = "opencode.json"
_PROJECT_SERVER = "tausik-project"
_PLUGIN_REL = os.path.join(".opencode", "plugins", "tausik-qg0.js")
_SINGULAR_PLUGIN_DIR = os.path.join(".opencode", "plugin")
_REBOOTSTRAP = "re-run `bootstrap --ide opencode`, then restart OpenCode"


def is_opencode_project(project_dir: str) -> bool:
    """True when the project carries an `.opencode/` dir (so the check should run)."""
    return os.path.isdir(os.path.join(project_dir, ".opencode"))


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("top-level value is not a JSON object")
    return data


def _check_config(project_dir: str) -> list[tuple[str, str, str]]:
    label = f"OpenCode config ({_CONFIG})"
    path = os.path.join(project_dir, _CONFIG)
    if not os.path.isfile(path):
        return [("warn", label, f"`.opencode/` present but no {_CONFIG} — {_REBOOTSTRAP}")]

    try:
        data = _load(path)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        return [("fail", label, f"invalid JSON: {e} — {_REBOOTSTRAP}")]

    out: list[tuple[str, str, str]] = []

    # 1. `tools` must be an OBJECT OF BOOLEANS. Gate on PRESENCE, not on type.
    #    An earlier version of this check only looked inside dicts, so `"tools": ["qg0"]`
    #    walked straight past it and doctor printed "valid — no `tools` object": an OK that
    #    affirmed the exact thing that was broken. A list or a string is just as fatal at
    #    startup as a nested object, and an improvising agent reaches for an array as
    #    readily as for an object.
    if "tools" in data:
        tools = data["tools"]
        bad = None
        if not isinstance(tools, dict):
            bad = f"`tools` is a {type(tools).__name__}, but OpenCode requires an object"
        else:
            offenders = [k for k, v in tools.items() if not isinstance(v, bool)]
            if offenders:
                bad = f"`tools` entries {offenders} are not booleans"
        if bad:
            out.append(
                (
                    "fail",
                    label,
                    f'{bad}. OpenCode accepts an object of booleans only (e.g. "bash": false); '
                    f"anything else aborts startup with ConfigInvalidError and the host will "
                    f"not boot. Custom tools belong in {_PLUGIN_REL}, not in `tools`.",
                )
            )

    # 2. MCP stanza must resolve to a real server.py.
    mcp = data.get("mcp")
    if not isinstance(mcp, dict) or _PROJECT_SERVER not in mcp:
        out.append(("warn", label, f"no `{_PROJECT_SERVER}` MCP server — {_REBOOTSTRAP}"))
    else:
        server = mcp[_PROJECT_SERVER]
        command = server.get("command") if isinstance(server, dict) else None
        if not isinstance(command, list) or len(command) < 2:
            out.append(
                (
                    "fail",
                    label,
                    f"`{_PROJECT_SERVER}.command` must be [python, server.py, ...] — {_REBOOTSTRAP}",
                )
            )
        else:
            if any("${workspaceFolder}" in str(part) for part in command):
                out.append(
                    (
                        "fail",
                        label,
                        "`command` contains ${workspaceFolder}. OpenCode does not expand it "
                        f"(only {{env:VAR}} and {{file:path}}), so the path is dead — {_REBOOTSTRAP}",
                    )
                )
            elif not os.path.isfile(str(command[1])):
                out.append(("warn", label, f"server.py not found at {command[1]} — {_REBOOTSTRAP}"))
            elif isinstance(server, dict) and server.get("enabled") is False:
                out.append(
                    ("warn", label, f"`{_PROJECT_SERVER}` is disabled — set `enabled: true`")
                )

    # 3. Rules must actually be wired in AND actually exist.
    instructions = data.get("instructions")
    entries = (
        [e for e in instructions if isinstance(e, str)] if isinstance(instructions, list) else []
    )
    if not entries:
        out.append(
            (
                "warn",
                label,
                "no `instructions` key — TAUSIK rules are not loaded. (They cannot ship via "
                f"AGENTS.md: OpenCode takes the first matching file only.) {_REBOOTSTRAP}",
            )
        )
    else:
        missing = [
            e for e in entries if not os.path.isfile(os.path.join(project_dir, *e.split("/")))
        ]
        if missing:
            out.append(
                (
                    "warn",
                    label,
                    f"`instructions` points at missing file(s) {missing} — the rules never "
                    f"load. {_REBOOTSTRAP}",
                )
            )

    if not out:
        out.append(
            ("ok", label, f"valid — `{_PROJECT_SERVER}` resolves, rules wired, no `tools` object")
        )
    return out


def _cli_wrapper_missing(project_dir: str) -> str | None:
    """The wrapper the plugin shells out to on every write, or None if present.

    The plugin has no other way to ask whether a task is active (it may not read the
    DB directly). If the wrapper is gone, `_queryActive` throws on every call and the
    default fail-open lets every write through — so a doctor that reports "writes are
    refused" without checking this is making a promise it never verified.

    Windows needs `tausik.cmd`: the bare `tausik` is a bash script, and Bun's shell has
    no bash to hand it to.
    """
    needed = "tausik.cmd" if os.name == "nt" else "tausik"
    path = os.path.join(project_dir, ".tausik", needed)
    return None if os.path.isfile(path) else os.path.join(".tausik", needed)


def _check_plugin(project_dir: str) -> list[tuple[str, str, str]]:
    label = "OpenCode QG-0 plugin"
    if os.path.isfile(os.path.join(project_dir, _PLUGIN_REL)):
        missing_cli = _cli_wrapper_missing(project_dir)
        if missing_cli:
            return [
                (
                    "fail",
                    label,
                    f"plugin is installed but {missing_cli} — the CLI it queries on every "
                    "write — is missing. The gate then fails OPEN: writes proceed with no "
                    "active-task check. Re-run `bootstrap` to reinstall the wrapper.",
                )
            ]
        return [("ok", label, f"{_PLUGIN_REL} present — writes without an active task are refused")]

    # A singular `plugin/` dir is the trap: OpenCode ignores it without a word.
    if os.path.isdir(os.path.join(project_dir, _SINGULAR_PLUGIN_DIR)):
        return [
            (
                "fail",
                label,
                f"found `{_SINGULAR_PLUGIN_DIR}` (singular). OpenCode only loads "
                f"`.opencode/plugins/` — the gate is silently not running. {_REBOOTSTRAP}",
            )
        ]
    return [
        (
            "fail",
            label,
            f"{_PLUGIN_REL} missing — QG-0 is NOT enforced in OpenCode: writes with no active "
            f"task will go through. {_REBOOTSTRAP}",
        )
    ]


def check_opencode_config(project_dir: str) -> list[tuple[str, str, str]]:
    """Doctor findings for an OpenCode install, or [] for non-OpenCode projects.

    Each finding is (severity, label, detail) with severity in {ok, warn, fail}.
    Never raises: a broken config is a diagnostic result, not a doctor crash.
    """
    if not is_opencode_project(project_dir):
        return []
    return _check_config(project_dir) + _check_plugin(project_dir)
