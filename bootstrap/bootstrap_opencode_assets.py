"""OpenCode artifacts that live on disk: the QG-0 plugin and the command stubs.

Split out of bootstrap_opencode.py, which owns `opencode.json` itself. The two have
different reasons to change — the config is schema-driven, these are files we copy — and
keeping them apart keeps both under the filesize gate.
"""

from __future__ import annotations

import os
import shutil

# The plugin directory is PLURAL. OpenCode loads `.opencode/plugins/`; a singular
# `plugin/` is not an error, it is SILENCE — the plugin never loads and enforcement is
# simply absent (gastown#1614). A silent bypass of QG-0 is the one failure this whole
# feature exists to prevent, so the name is pinned here and asserted in tests rather than
# left to a typo.
PLUGINS_SUBDIR = "plugins"
PLUGIN_FILE = "tausik-qg0.js"

# Same story for commands: `.opencode/commands/` (verified against opencode.ai/docs, not
# inferred from the plugins/ spelling).
COMMANDS_SUBDIR = "commands"

# Core TAUSIK slash-command surface re-exposed as OpenCode commands.
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


class OpenCodePluginMissing(RuntimeError):
    """The QG-0 plugin source could not be found — bootstrap must not continue quietly.

    Enforcement is the whole point (decision #131). Skipping it silently would leave a
    project that *claims* TAUSIK discipline while permitting any write at all — the exact
    "doc promises, code absent" gap that caused the incident.
    """


def _resolve_plugin_source(target_dir: str, lib_dir: str | None) -> str | None:
    """Locate the QG-0 plugin source. The LIBRARY copy wins over the installed one.

    Precedence matters more than it looks. If the already-installed
    ``<target>/plugins/tausik-qg0.js`` were preferred, it would always exist after the
    first bootstrap — so every later run would resolve src == dst, skip the copy, and
    leave the old plugin in place. A user upgrading TAUSIK to get a FIXED gate would run
    bootstrap, watch it succeed, and keep running the broken one: the enforcement artifact
    would be the single file in the project that an upgrade could never reach.

    The installed copy is the fallback, for a project working without a library checkout.
    """
    if lib_dir:
        canonical = os.path.join(lib_dir, "harness", "opencode", PLUGINS_SUBDIR, PLUGIN_FILE)
        if os.path.isfile(canonical):
            return canonical
    copied = os.path.join(target_dir, PLUGINS_SUBDIR, PLUGIN_FILE)
    if os.path.isfile(copied):
        return copied
    return None


def generate_opencode_plugin(target_dir: str, lib_dir: str | None = None) -> str:
    """Install the QG-0 plugin into ``<target_dir>/plugins/tausik-qg0.js``.

    Copies the canonical artifact from ``harness/opencode/plugins/`` — the plugin is a
    real, lintable, directly-runnable JS file, not a string baked into Python.

    Raises OpenCodePluginMissing when the source cannot be found: a project without the
    gate is a project without QG-0, and that must fail loudly.
    """
    src = _resolve_plugin_source(target_dir, lib_dir)
    if src is None:
        raise OpenCodePluginMissing(
            f"QG-0 plugin source not found ({PLUGIN_FILE}). Looked in "
            f"{os.path.join(target_dir, PLUGINS_SUBDIR)} and "
            f"<lib>/harness/opencode/{PLUGINS_SUBDIR}. Without it OpenCode has no "
            "enforcement and TAUSIK rules become advisory — refusing to pretend otherwise."
        )
    dst = os.path.join(target_dir, PLUGINS_SUBDIR, PLUGIN_FILE)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copyfile(src, dst)
    return dst


def generate_opencode_commands(target_dir: str) -> int:
    """Write slash-command stubs into ``<target_dir>/commands/``.

    Returns the count written. Existing files are left untouched — a user who edited a
    command keeps their version. The frontmatter carries `description`, which is what
    OpenCode shows in the command picker.
    """
    commands_dir = os.path.join(target_dir, COMMANDS_SUBDIR)
    os.makedirs(commands_dir, exist_ok=True)
    written = 0
    for name in _COMMAND_STUBS:
        path = os.path.join(commands_dir, f"{name}.md")
        if os.path.exists(path):
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                f"---\ndescription: TAUSIK /{name} workflow\n---\n\n"
                f"Execute the TAUSIK `/{name}` workflow. The `tausik-project` MCP server "
                f"exposes the underlying tools; follow the `{name}` SKILL.md procedure.\n"
            )
        written += 1
    return written
