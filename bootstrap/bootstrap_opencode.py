"""Bootstrap generator for OpenCode (SST, npm package ``opencode-ai``).

Step 1 of 3 toward OpenCode support (see gotcha #201, decision #131). This module
only *generates* configuration — OpenCode is NOT declared a supported IDE until
the QG-0 plugin exists (``opencode-qg0-plugin``) and the final task flips
``SCAFFOLD_IDES``. Doc claiming support without enforcement is exactly what caused
the incident this work exists to fix.

Three schema facts, taken from the official docs, that make this generator
deliberately unlike ``bootstrap_kilo``:

* ``${workspaceFolder}`` does NOT exist in OpenCode. It substitutes only
  ``{env:VAR}`` and ``{file:path}``. Copying Kilo's portable paths verbatim
  yields a config whose MCP command points at a literal ``${workspaceFolder}``
  directory. Every path in ``command`` is therefore ABSOLUTE.
* The ``tools`` key accepts booleans only (``{"bash": false}``). An object there
  aborts startup with ConfigInvalidError. We never emit the key — and we never
  delete a user's own boolean entries either.
* ``AGENTS.md`` is first-matching-file-wins, so a user's own AGENTS.md would
  shadow ours forever. Rules ship via ``instructions`` (an array of paths that
  OpenCode *merges* with AGENTS.md) — the one non-conflicting channel.
"""

from __future__ import annotations

import json
import ntpath
import os
import re
import shutil
from typing import Any

# The on-disk artifacts (QG-0 plugin, command stubs) live in their own module: they are
# copied files, this one owns opencode.json. Re-exported so callers keep one import.
from bootstrap_opencode_assets import (  # noqa: F401 — re-exported for callers/tests
    PLUGIN_FILE as _PLUGIN_FILE,
)
from bootstrap_opencode_assets import (  # noqa: F401
    PLUGINS_SUBDIR as _PLUGINS_SUBDIR,
)
from bootstrap_opencode_assets import (  # noqa: F401
    OpenCodePluginMissing,
    generate_opencode_commands,
    generate_opencode_plugin,
)

# "C:evil.md" / "C:/evil.md" — a drive-qualified path. os.path.isabs() calls the first one
# relative even on Windows, and both of them False on POSIX, yet either escapes the project.
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")

# (server-name, relative path under an mcp/ root) — order is the emit order.
_SERVERS = (
    ("tausik-project", os.path.join("project", "server.py")),
    ("codebase-rag", os.path.join("codebase-rag", "server.py")),
    ("tausik-brain", os.path.join("brain", "server.py")),
)

# OpenCode reads project config from the project ROOT, not from .opencode/.
_CONFIG_FILE = "opencode.json"
_CONFIG_SCHEMA = "https://opencode.ai/config.json"

# Rules file, project-relative. OpenCode resolves `instructions` entries relative
# to the config file, which lives at the project root — so this stays relative
# (rename-proof) while `command` paths must be absolute.
_DEFAULT_RULES_PATH = ".opencode/tausik-rules.md"


def _rules_path(config: dict | None, project_dir: str | None = None) -> str:
    """Project-relative rules path, overridable via config['opencode']['rules_path'].

    The override is UNTRUSTED: `.tausik/config.json` travels with the repo, so a
    tampered one (a malicious PR, a cloned template) would otherwise turn the next
    `bootstrap --ide opencode` into an arbitrary-file-write primitive — `../../..`
    walks the rules file straight out of the project. An escaping or absolute path is
    refused and the default is used instead, loudly.
    """
    if not isinstance(config, dict):
        return _DEFAULT_RULES_PATH
    oc = config.get("opencode")
    if not isinstance(oc, dict):
        return _DEFAULT_RULES_PATH
    override = oc.get("rules_path")
    if not isinstance(override, str) or not override.strip():
        return _DEFAULT_RULES_PATH

    candidate = override.strip().replace("\\", "/")
    root = os.path.abspath(project_dir or ".")

    def _refuse(reason: str) -> str:
        print(
            f"  WARNING: opencode.rules_path={override!r} refused ({reason}); "
            f"using {_DEFAULT_RULES_PATH} instead."
        )
        return _DEFAULT_RULES_PATH

    # Cheap syntactic refusals FIRST. They must run before any path arithmetic, because
    # the arithmetic itself can raise: os.path.commonpath() throws ValueError on Windows
    # when the two paths sit on different drives. A crash is not a guard — it would take
    # `bootstrap --ide all` down halfway through, on hostile input, with a raw traceback.
    #
    # ntpath.isabs is checked explicitly: on POSIX, os.path.isabs("C:/evil.md") is False,
    # and a drive-RELATIVE "C:evil.md" is not absolute even on Windows — yet both escape.
    if candidate in (".", "..", "/"):
        return _refuse("not a file path")
    if os.path.isabs(candidate) or ntpath.isabs(candidate) or _DRIVE_PREFIX.match(candidate):
        return _refuse("absolute or drive-qualified paths are not allowed")
    if ".." in candidate.split("/"):
        return _refuse("path traversal")

    target = os.path.abspath(os.path.join(root, *candidate.split("/")))
    try:
        inside = os.path.commonpath([root, target]) == root
    except ValueError:
        # Different drives / mixed path flavours — by definition outside the project.
        inside = False
    if not inside:
        return _refuse(f"resolves outside the project ({target})")
    return candidate


def _resolve_server(name_path: str, target_dir: str, lib_dir: str | None) -> str | None:
    """Locate a server.py: prefer the copied IDE-dir copy, else the lib canonical.

    Returns None when neither exists, so the caller omits that server rather than
    emitting a command that would fail at launch.
    """
    copied = os.path.join(target_dir, "mcp", name_path)
    if os.path.isfile(copied):
        return copied
    if lib_dir:
        canonical = os.path.join(lib_dir, "harness", "claude", "mcp", name_path)
        if os.path.isfile(canonical):
            return canonical
    return None


def _build_mcp_servers(
    project_dir: str,
    target_dir: str,
    venv_python: str | None,
    lib_dir: str | None,
) -> dict[str, Any]:
    """Build the ``mcp`` stanza: name -> {type:'local', command:[...], enabled}.

    All paths absolute — OpenCode expands no workspace variable (gotcha #201). That
    includes the interpreter: OpenCode spawns MCP servers itself, and a GUI-launched
    host does not necessarily hand them a shell PATH, so a bare "python" can fail to
    launch with nothing but a dead server to show for it. The bare name survives only
    as a last resort, when no interpreter can be found on PATH at all.
    """
    python_exe = os.path.abspath(venv_python) if venv_python else _fallback_python()
    project_abs = os.path.abspath(project_dir)
    out: dict[str, Any] = {}
    for name, rel in _SERVERS:
        server = _resolve_server(rel, target_dir, lib_dir)
        if server is None:
            continue
        out[name] = {
            "type": "local",
            "command": [python_exe, os.path.abspath(server), "--project", project_abs],
            "enabled": True,
        }
    return out


def _fallback_python() -> str:
    """Absolute interpreter path when no venv python was passed, or "python" if none."""
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return os.path.abspath(found)
    return "python"


def _load_existing(path: str) -> dict[str, Any]:
    """Read an existing opencode.json. A malformed file is replaced, not crashed on.

    Replacement is announced: the file may have held the user's `model`, `provider`,
    `agent` or `permission` keys, and losing those silently is its own small betrayal.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        print(f"  WARNING: {path} was unreadable ({e}) — replacing it. Any keys it held are lost.")
        return {}
    if not isinstance(loaded, dict):
        print(f"  WARNING: {path} was not a JSON object — replacing it.")
        return {}
    return loaded


def _merge_instructions(existing: dict[str, Any], rules_rel: str) -> None:
    """Append the rules path to ``instructions`` exactly once.

    Idempotent by set-membership, not by append: a second bootstrap run must not
    grow the array. Foreign entries keep their order and position.
    """
    current = existing.get("instructions")
    entries = [e for e in current if isinstance(e, str)] if isinstance(current, list) else []
    if rules_rel not in entries:
        entries.append(rules_rel)
    existing["instructions"] = entries


def warn_unbootable_config(project_dir: str, existing: dict[str, Any]) -> list[str]:
    """Report leftovers that keep OpenCode from starting AT ALL. Returns the warnings.

    This is the upgrade path of the very user whose host this release exists to repair.
    Their project still holds the hand-written config that killed it: a `tools.qg0` OBJECT
    (the key is boolean-only) and a plugin under the singular `.opencode/plugin/`. We merge
    our stanzas in beside it and print a cheerful success — while OpenCode still refuses to
    boot on the next launch, for the same reason as before.

    We do not delete it: silently rewriting a user's config is its own betrayal, and the
    file may hold their model/provider settings. But we refuse to let bootstrap look
    successful on a config that cannot start. Say exactly what is fatal and exactly what to
    remove; `tausik doctor` fails on the same conditions.
    """
    warnings: list[str] = []

    tools = existing.get("tools")
    if tools is not None:
        bad = None
        if not isinstance(tools, dict):
            bad = f"`tools` is a {type(tools).__name__}, but OpenCode requires an object"
        else:
            offenders = [k for k, v in tools.items() if not isinstance(v, bool)]
            if offenders:
                bad = f"`tools` entries {offenders} are not booleans"
        if bad:
            warnings.append(
                f"  WARNING: {os.path.join(project_dir, _CONFIG_FILE)} CANNOT START OpenCode.\n"
                f'    {bad}. `tools` accepts booleans only (e.g. "bash": false); anything\n'
                f"    else aborts startup with ConfigInvalidError. TAUSIK did not write this\n"
                f"    key and will not delete it — remove it by hand. Custom tools belong in\n"
                f"    {_PLUGINS_SUBDIR}/, not in `tools`."
            )

    singular = os.path.join(project_dir, ".opencode", "plugin")
    if os.path.isdir(singular):
        warnings.append(
            f"  WARNING: {singular} exists (SINGULAR). OpenCode only loads `plugins/`, so\n"
            f"    anything in there never runs — and if it imports an npm package that is not\n"
            f"    installed, it can take the host down at load. Delete the directory; the QG-0\n"
            f"    gate now lives in {os.path.join('.opencode', _PLUGINS_SUBDIR, _PLUGIN_FILE)}."
        )

    for w in warnings:
        print(w)
    return warnings


def generate_opencode_config(
    project_dir: str,
    target_dir: str,
    venv_python: str | None = None,
    lib_dir: str | None = None,
    config: dict | None = None,
) -> str | None:
    """Write/merge ``opencode.json`` at the project root. Returns the path written.

    Merges into any existing config: user keys (``model``, ``provider``, ``agent``,
    ``permission``, their own MCP servers, their own boolean ``tools``) survive
    untouched. TAUSIK owns exactly two things — its three ``mcp`` stanzas and one
    ``instructions`` entry.

    Never writes a ``tools`` key: in OpenCode it is boolean-only, and an object
    there is a hard ConfigInvalidError at startup. If the existing file already carries
    such an object (the incident's own config), we say so loudly rather than merging
    beside it and reporting success — see warn_unbootable_config.
    """
    servers = _build_mcp_servers(project_dir, target_dir, venv_python, lib_dir)
    path = os.path.join(project_dir, _CONFIG_FILE)
    existing = _load_existing(path)

    warn_unbootable_config(project_dir, existing)

    existing.setdefault("$schema", _CONFIG_SCHEMA)
    if servers:
        mcp = existing.get("mcp")
        if not isinstance(mcp, dict):
            mcp = {}
        mcp.update(servers)
        existing["mcp"] = mcp
    _merge_instructions(existing, _rules_path(config, project_dir))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    return path


def scaffold_opencode(
    project_dir: str,
    target_dir: str,
    venv_python: str | None,
    lib_dir: str | None,
    config: dict | None,
    stacks: list[str],
    context_tier: str = "standard",
    output_mode: str = "off",
) -> None:
    """Full OpenCode scaffold: config + rules + QG-0 plugin + command stubs.

    The whole branch lives here rather than inline in bootstrap.py so the dispatcher
    stays a dispatcher (and under the filesize gate).

    ``output_mode`` arrives ALREADY RESOLVED from the config root (bootstrap_ide). It is
    not re-derived here: `config` is the nested "bootstrap" section, and reading the root
    key out of it silently produced "off" for every user who followed the docs.
    """
    project_name = (config or {}).get("project", "my-project")

    written = generate_opencode_config(project_dir, target_dir, venv_python, lib_dir, config)
    print(f"  OpenCode config: {written}")

    rules = generate_opencode_rules(
        project_dir, project_name, stacks, context_tier, config, output_mode
    )
    print(f"  OpenCode rules: {rules} (delivered via the `instructions` key)")

    plugin = generate_opencode_plugin(target_dir, lib_dir)
    print(f"  OpenCode QG-0 plugin: {plugin}")

    n_cmds = generate_opencode_commands(target_dir)
    if n_cmds:
        print(f"  OpenCode commands: {n_cmds} stub(s)")


def generate_opencode_rules(
    project_dir: str,
    project_name: str,
    stacks: list[str],
    context_tier: str = "standard",
    config: dict | None = None,
    output_mode: str = "off",
) -> str:
    """Write the TAUSIK rules file referenced by ``instructions``.

    Same body as CLAUDE.md / AGENTS.md (bootstrap_templates.build_full_body), so no
    host gets a weaker ruleset. An existing file is preserved — a re-run must not
    stomp user edits (but see warn_output_mode_not_applied: preserving must not be
    silent when the user asked for a mode the existing file lacks).

    ``output_mode`` is passed in already resolved from the config ROOT. Do not re-derive
    it from ``config`` — that dict is the nested "bootstrap" section and yields "off".

    For ide=opencode the caller must NOT also generate AGENTS.md: OpenCode merges
    `instructions` INTO AGENTS.md, so shipping both would put the same rules in the
    context twice.
    """
    from bootstrap_templates import build_full_body, warn_output_mode_not_applied

    rules_rel = _rules_path(config, project_dir)
    path = os.path.join(project_dir, *rules_rel.split("/"))
    if os.path.exists(path):
        warn_output_mode_not_applied(path, output_mode)
        return path

    body = build_full_body(
        project_name,
        stacks,
        "an AI agent (OpenCode)",
        ".opencode",
        ide="opencode",
        context_tier=context_tier,
        output_mode=output_mode,
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# TAUSIK — agent rules\n\n{body}")
    return path
