"""Bootstrap generator for Kilo Code (VSCode addon + CLI).

Emits Kilo-native MCP configuration so TAUSIK's MCP server loads inside Kilo
without any Claude-specific scaffolding. Kilo is a runtime *host* (axis-1,
Decision #119); the model it runs (often a z.ai GLM via the Anthropic-compatible
endpoint) is resolved separately from model_profiles.

Config path is version-dependent across Kilo builds, so we write BOTH known
locations with the same stanza (Decision #120): ``.kilo/kilo.jsonc`` (current
kilo.ai docs) and ``.kilocode/mcp.json`` (older Cline-lineage). Whichever the
installed Kilo reads, it finds the server. Override via ``.tausik/config.json``
``kilo.config_paths`` (list of project-relative paths).

Paths are emitted **absolute, forward-slashed**. Historically this generator
wrote ``${workspaceFolder}``-relative paths believing Kilo expands the variable
at launch; that belief was measured false on the live host: Kilo Code 7.8.3
contains ZERO ``${workspaceFolder}`` literals in its ``kilo.exe`` CLI (the
process that spawns MCP servers) or its extension bundle, so a relative stanza
pointed the spawn at a literally-named ``${workspaceFolder}/...`` path and every
server failed to start silently. Absolute paths are the Codex precedent
(bootstrap_codex made the same trade for the same reason): renaming the project
directory requires re-running bootstrap. ``tausik doctor`` runs a live
initialize probe against the configured command, so a config the host cannot
load is reported instead of assumed.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Any

from bootstrap_generate import retire_managed_servers

# (server-name, relative path under an mcp/ root) — order is the emit order.
_SERVERS = (
    ("tausik-project", os.path.join("project", "server.py")),
    ("codebase-rag", os.path.join("codebase-rag", "rag_server.py")),
)

# Default Kilo config files to write, relative to project_dir (Decision #120).
_DEFAULT_CONFIG_PATHS = (
    os.path.join(".kilo", "kilo.jsonc"),
    os.path.join(".kilocode", "mcp.json"),
)

# KILO: the plugins directory is PLURAL. Kilo auto-loads
# `.kilo/plugins/*.{js,ts}`; a singular `plugin/` is not an error, it is
# SILENCE — the gate never loads and QG-0 enforcement is simply absent, the
# one failure this feature exists to prevent. Same precedence rule as the
# OpenCode deployer: the library copy wins, or an upgrade could never reach
# the enforcement artifact (bootstrap_opencode_assets for the full story).
PLUGINS_SUBDIR = "plugins"
PLUGIN_FILES = (
    "tausik-gates.js",  # QG-0 enforcement (port of the OpenCode gate)
    "tausik-observe.js",  # provider-agnostic live model observation
)

# Kilo's SECOND extension point (measured against the live schema
# https://app.kilo.ai/config.json(measured against the live schema): the
# `permission` key accepts a per-operation policy, and the rule-shaped
# operations (`edit`, `bash`, ...) accept `{pattern: "ask"|"allow"|"deny"}`.
# This is HOST-LEVEL enforcement of rules TAUSIK already states in prose —
# the same rules, now refused by the host itself, not merely by the agent's
# good behavior. Managed keys are exactly the ones TAUSIK can argue for:
#
#   edit  ".tausik/tausik.db"  deny — the DB belongs to the service layer;
#                                a raw edit corrupts what every tool reads.
#   edit  ".kilo/plugins/*"    deny — enforcement artifacts are bootstrap-
#                                managed; a hand edit is drift by definition.
#   bash  "git push*"          ask  — publication leaves the machine only
#                                with the owner's word (SENAR Rule 7).
#   bash  "sqlite3*"           ask  — no raw SQLite against the project DB.
#   external_directory        deny — the agent works inside the project
#                                (Rule 2 scope boundaries).
#
# Merge semantics mirror the `mcp` stanza: user keys are preserved, managed
# keys are rewritten idempotently and WIN over a user value on the same
# pattern (a governance rule the user can name is one the file must keep).
# A STRING `permission` (global "allow"/"ask"/"deny") is left untouched: a
# string cannot hold per-pattern rules, and overriding the user's global
# choice is not ours to do. Opt out via config kilo.permission_policy=false.
PERMISSION_POLICY: dict[str, dict[str, str] | str] = {
    "edit": {
        ".tausik/tausik.db": "deny",
        ".kilo/plugins/*": "deny",
    },
    "bash": {
        "git push*": "ask",
        "sqlite3*": "ask",
    },
    "external_directory": "deny",
}


def _merge_permission(existing: dict) -> dict | None:
    """Fold the managed policy into the config's ``permission`` key.

    Returns the merged value to store, or None when nothing should be
    written (existing global string choice left as the user set it).
    """
    perm = existing.get("permission")
    if perm is None:
        merged: dict[str, dict[str, str] | str] = {}
    elif isinstance(perm, str):
        return None  # a global action cannot carry patterns; the user's word stands
    elif isinstance(perm, dict):
        merged = perm
    else:
        return None
    for op, rules in PERMISSION_POLICY.items():
        if isinstance(rules, str):
            merged[op] = rules
        else:
            slot = merged.get(op)
            if not isinstance(slot, dict):
                slot = {}
                merged[op] = slot
            slot.update(rules)
    return merged


def _permission_enabled(config: dict | None) -> bool:
    if not isinstance(config, dict):
        return True
    kilo_cfg = config.get("kilo")
    if isinstance(kilo_cfg, dict):
        flag = kilo_cfg.get("permission_policy")
        if flag is False:
            return False
    return True


def _abs_portable(abs_path: str) -> str:
    """Absolute, forward-slashed path for embedding in Kilo's JSON config.

    Kilo 7.8.3 does not expand ``${workspaceFolder}`` in MCP commands (measured:
    zero literals in kilo.exe), so every path must be absolute. Forward slashes
    keep the JSON readable and Windows-safe.
    """
    return os.path.normpath(abs_path).replace("\\", "/")


def _resolve_server(name_path: str, ide_dir: str, lib_dir: str | None) -> str | None:
    """Locate a server.py: prefer the copied IDE-dir copy, else the lib canonical.

    Returns None when neither exists, so the caller omits that server rather
    than emitting a dead command.
    """
    copied = os.path.join(ide_dir, "mcp", name_path)
    if os.path.isfile(copied):
        return copied
    if lib_dir:
        canonical = os.path.join(lib_dir, "harness", "claude", "mcp", name_path)
        if os.path.isfile(canonical):
            return canonical
    return None


def _build_mcp_servers(
    project_dir: str,
    ide_dir: str,
    venv_python: str | None,
    lib_dir: str | None,
) -> dict[str, Any]:
    """Build the ``mcp`` stanza: name -> {type:'local', command:[...], enabled}."""
    python_exe = venv_python or "python"
    out: dict[str, Any] = {}
    for name, rel in _SERVERS:
        server = _resolve_server(rel, ide_dir, lib_dir)
        if server is None:
            continue
        out[name] = {
            "type": "local",
            "command": [
                _abs_portable(python_exe) if os.path.isabs(python_exe) else python_exe,
                _abs_portable(server),
                "--project",
                _abs_portable(project_dir),
            ],
            "enabled": True,
        }
    return out


def _merge_into_file(
    path: str,
    servers: dict[str, Any],
    permission: dict[str, dict[str, str] | str] | None = PERMISSION_POLICY,
) -> None:
    """Merge TAUSIK servers (and the managed permission policy) into one Kilo
    config file under the ``mcp`` (and ``permission``) keys.

    Preserves user-added servers and any other top-level keys. A malformed
    existing file is replaced (not crashed on). Idempotent: re-running rewrites
    the TAUSIK stanzas to the same value without duplicating. Pass
    ``permission=None`` to skip the policy (the config opt-out path).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing: dict[str, Any] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                existing = loaded
        except (json.JSONDecodeError, OSError):
            existing = {}
    mcp = existing.get("mcp")
    if not isinstance(mcp, dict):
        mcp = {}
    retire_managed_servers(mcp)
    mcp.update(servers)
    existing["mcp"] = mcp
    if permission is not None:
        merged_perm = _merge_permission(existing)
        if merged_perm is not None:
            existing["permission"] = merged_perm
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def generate_kilo_config(
    project_dir: str,
    ide_dir: str,
    venv_python: str | None = None,
    lib_dir: str | None = None,
    config: dict | None = None,
) -> list[str]:
    """Write the TAUSIK MCP stanza into every configured Kilo config path.

    Returns the list of files written (for logging / tests). Robust across Kilo
    versions: writes both default paths unless ``config['kilo']['config_paths']``
    overrides the list. No-op-safe when no server.py can be found.
    """
    servers = _build_mcp_servers(project_dir, ide_dir, venv_python, lib_dir)
    if not servers:
        return []
    rel_paths: tuple[str, ...] | list[str] = _DEFAULT_CONFIG_PATHS
    if isinstance(config, dict):
        kilo_cfg = config.get("kilo")
        if isinstance(kilo_cfg, dict):
            override = kilo_cfg.get("config_paths")
            if isinstance(override, list) and override:
                rel_paths = [str(p) for p in override if isinstance(p, str) and p.strip()]
    written: list[str] = []
    policy = PERMISSION_POLICY if _permission_enabled(config) else None
    for rel in rel_paths:
        path = os.path.join(project_dir, rel)
        _merge_into_file(path, servers, policy)
        written.append(path)
    return written


# Core TAUSIK slash-command surface re-exposed as Kilo commands.
_COMMAND_STUBS = (
    "start",
    "end",
    "checkpoint",
    "plan",
    "task",
    "ship",
    "commit",
    "explore",
    "review",
    "test",
    "debug",
)


def generate_kilo_commands(target_dir: str, skills_dir: str | None = None) -> int:
    """Write lightweight slash-command stubs into ``target_dir/commands/``.

    Each stub instructs the Kilo agent to run the corresponding TAUSIK workflow
    (the full procedure lives in the copied SKILL.md / via the MCP server).
    Returns the count of stubs written. Existing files are left untouched.
    """
    commands_dir = os.path.join(target_dir, "commands")
    os.makedirs(commands_dir, exist_ok=True)
    written = 0
    for name in _COMMAND_STUBS:
        path = os.path.join(commands_dir, f"{name}.md")
        if os.path.exists(path):
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                f"# /{name}\n\n"
                f"Execute the TAUSIK `/{name}` workflow. The MCP server "
                f"`tausik-project` exposes the underlying tools; follow the "
                f"`{name}` SKILL.md procedure.\n"
            )
        written += 1
    return written


class KiloPluginMissing(RuntimeError):
    """The gates plugin source could not be found — bootstrap must not continue quietly.

    Mirrors OpenCodePluginMissing: enforcement is the whole point (decision
    #131). A Kilo project whose profile lacks the plugin runs with QG-0 as
    markdown the host is free to ignore — the exact "doc promises, code
    absent" gap this whole mechanism exists to close. Skipping silently would
    leave a project that *claims* TAUSIK discipline while permitting any
    write at all.
    """


def _resolve_plugin_source(target_dir: str, lib_dir: str | None, name: str) -> str | None:
    """Locate a plugin source. The LIBRARY copy wins over the installed one.

    Same precedence argument as the OpenCode deployer: preferring the
    already-installed copy would make every bootstrap after the first a no-op
    (src == dst), so a user upgrading TAUSIK for a FIXED artifact would keep
    running the broken one forever.
    """
    if lib_dir:
        canonical = os.path.join(lib_dir, "harness", "kilo", PLUGINS_SUBDIR, name)
        if os.path.isfile(canonical):
            return canonical
    copied = os.path.join(target_dir, PLUGINS_SUBDIR, name)
    if os.path.isfile(copied):
        return copied
    return None


def generate_kilo_plugin(target_dir: str, lib_dir: str | None = None) -> list[str]:
    """Install the Kilo plugins into ``<target_dir>/plugins/``.

    Copies the canonical artifacts from ``harness/kilo/plugins/`` — real,
    lintable, directly-runnable JS files, not strings baked into Python. Kilo
    auto-loads ``.kilo/plugins/*.{js,ts}`` (its own config discovery), so
    dropping the files IS the registration; no config stanza exists to write.

    Returns the deployed paths in PLUGIN_FILES order. Raises KiloPluginMissing
    when any source cannot be found.
    """
    deployed: list[str] = []
    for name in PLUGIN_FILES:
        src = _resolve_plugin_source(target_dir, lib_dir, name)
        if src is None:
            raise KiloPluginMissing(
                f"Kilo plugin source not found ({name}). Looked in "
                f"{os.path.join(target_dir, PLUGINS_SUBDIR)} and "
                f"<lib>/harness/kilo/{PLUGINS_SUBDIR}. Without it Kilo runs with a "
                "hole in its TAUSIK wiring — refusing to pretend otherwise."
            )
        dst = os.path.join(target_dir, PLUGINS_SUBDIR, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copyfile(src, dst)
        deployed.append(dst)
    return deployed
