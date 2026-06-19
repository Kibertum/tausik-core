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

Paths are emitted **rename-proof**: a server living inside the project and the
``--project`` argument use ``${workspaceFolder}`` (which Kilo expands at launch),
so renaming the project folder does not break the config. Servers resolved from
an external lib stay absolute (a project rename doesn't move them).
"""

from __future__ import annotations

import json
import os
from typing import Any

from bootstrap_paths import portable_path

# (server-name, relative path under an mcp/ root) — order is the emit order.
_SERVERS = (
    ("tausik-project", os.path.join("project", "server.py")),
    ("codebase-rag", os.path.join("codebase-rag", "server.py")),
    ("tausik-brain", os.path.join("brain", "server.py")),
)

# Default Kilo config files to write, relative to project_dir (Decision #120).
_DEFAULT_CONFIG_PATHS = (
    os.path.join(".kilo", "kilo.jsonc"),
    os.path.join(".kilocode", "mcp.json"),
)


def _p(path: str) -> str:
    """Forward-slash a path for JSON portability (Windows-safe)."""
    return path.replace("\\", "/")


def _portable_path(abs_path: str, project_dir: str) -> str:
    """Kilo expands ``${workspaceFolder}`` at launch — rename-proof for in-project
    paths. Thin wrapper over the shared helper (see bootstrap_paths)."""
    return portable_path(abs_path, project_dir, "${workspaceFolder}")


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
                _p(python_exe),
                _portable_path(server, project_dir),
                "--project",
                "${workspaceFolder}",
            ],
            "enabled": True,
        }
    return out


def _merge_into_file(path: str, servers: dict[str, Any]) -> None:
    """Merge TAUSIK servers into one Kilo config file under the ``mcp`` key.

    Preserves user-added servers and any other top-level keys. A malformed
    existing file is replaced (not crashed on). Idempotent: re-running rewrites
    the TAUSIK stanzas to the same value without duplicating.
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
    mcp.update(servers)
    existing["mcp"] = mcp
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
    for rel in rel_paths:
        path = os.path.join(project_dir, rel)
        _merge_into_file(path, servers)
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
