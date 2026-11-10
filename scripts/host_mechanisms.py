"""What each host can actually ENFORCE, derived by running the real generators.

cross-model-parity-has-no-gate. A capability can go Claude-only and nothing
notices. Measured on this tree (session #230): claude and qwen carry the same 23
hook commands and that pair IS guarded (tests/test_bootstrap_hooks_parity.py);
the other hosts were guarded by nothing at all — opencode carried one QG-0
plugin, cursor and kilo carried no real-time mechanism whatsoever. Since the
kilo-gate-plugin task, kilo deploys the same one-plugin shape as opencode
(`.kilo/plugins/tausik-gates.js`, a port of the same contract); cursor remains
the only declared-none host.

HOW THE TABLE IS OBTAINED. The generators are RUN, into a throwaway tree, and
what lands on disk is read back. Not a list in the code of what each host is
supposed to get: such a list records intent and drifts from the deployment
exactly as the rules text drifted from the mechanism (decision #335). The
builders below are the mechanism generators that exist; `cross_check_against_disk`
holds them honest against the profiles bootstrap really deployed, so a new one
added and forgotten here is caught rather than silently uncovered.

COMPARISON IS WITHIN A MECHANISM KIND, NEVER ACROSS. OpenCode enforces through a
plugin and Claude through hook commands; asking whether `tausik-qg0.js` is
"missing" from Claude's hook list is a question with no meaning, and answering it
would fill the gate with 23 false differences on day one. So hosts are compared
only with the hosts that share their extension point. Whether a host has an
extension point AT ALL is a different statement, and it is already made twice —
by the enforcement notice each host's rules file opens with, and by `doctor`. It
is not restated here.

WHAT THIS MODULE DOES NOT DO is restate a host registry. Since
four-ide-registries-collapse there is ONE: `ide_utils.IDE_REGISTRY` holds the
per-host facts; `bootstrap_config.IDE_DIRS` derives its config_dir column from
it, and `skill_profile_detect.VALID_IDES` takes the scaffolded subset from
`bootstrap_config.SCAFFOLD_IDES` — each through a guarded import with an
annotated mirror for consumers that vendor only `scripts/`. The `providers`
registry is code, not data: it stays the pinned subset of hosts that implement
model observation (no windsurf, no opencode provider yet), held by tests
rather than derived from a list. `cross_check_against_disk` reads
`ide_utils.IDE_REGISTRY` and says so out loud.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Callable, Iterator

from hooks.cursor_command import split_cursor_command

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BOOTSTRAP = os.path.join(_REPO, "bootstrap")
if os.path.isdir(_BOOTSTRAP) and _BOOTSTRAP not in sys.path:
    sys.path.insert(0, _BOOTSTRAP)

#: Prefixes that make a capability name say WHICH extension point carries it.
KIND_HOOK = "hook"
KIND_PLUGIN = "plugin"

_CURSOR_SOURCE_EVENTS = {
    "preToolUse": "PreToolUse",
    "postToolUse": "PostToolUse",
    "sessionStart": "SessionStart",
    "beforeSubmitPrompt": "UserPromptSubmit",
    "stop": "Stop",
    "sessionEnd": "SessionEnd",
}


def _shared_cursor_matcher(matcher: str) -> str:
    mapped: list[str] = []
    reverse_mcp = {
        "MCP:FileSystem": "mcp__windows-mcp__FileSystem",
        "MCP:PowerShell": "mcp__windows-mcp__PowerShell",
        "MCP:replace_symbol_body": "mcp__serena__replace_symbol_body",
        "MCP:replace_content": "mcp__serena__replace_content",
        "MCP:insert_after_symbol": "mcp__serena__insert_after_symbol",
        "MCP:insert_before_symbol": "mcp__serena__insert_before_symbol",
        "MCP:rename_symbol": "mcp__serena__rename_symbol",
        "MCP:safe_delete_symbol": "mcp__serena__safe_delete_symbol",
        "MCP:tausik_task_done": "mcp__tausik-project__tausik_task_done",
    }
    for name in matcher.split("|") if matcher else []:
        values: tuple[str, ...]
        if name == "Shell":
            values = ("Bash", "PowerShell")
        elif name == "Write":
            values = ("Write", "Edit", "MultiEdit", "NotebookEdit")
        elif name == "Delete":
            values = ()  # Cursor-only tool covered by the same write policy.
        else:
            values = (reverse_mcp.get(name, name),)
        for value in values:
            if value not in mapped:
                mapped.append(value)
    return "|".join(mapped)


def _build_claude(target_dir: str, project_dir: str, lib_dir: str) -> None:
    from bootstrap_generate import generate_settings_claude

    generate_settings_claude(target_dir, project_dir, lib_dir=lib_dir)


def _build_qwen(target_dir: str, project_dir: str, lib_dir: str) -> None:
    from bootstrap_qwen import generate_settings_qwen

    generate_settings_qwen(target_dir, project_dir, venv_python=sys.executable, lib_dir=lib_dir)


def _build_cursor(target_dir: str, project_dir: str, lib_dir: str) -> None:
    from bootstrap_generate import generate_cursor_hooks_json

    generate_cursor_hooks_json(project_dir, target_dir)


def _build_opencode(target_dir: str, project_dir: str, lib_dir: str) -> None:
    from bootstrap_opencode import generate_opencode_plugin

    generate_opencode_plugin(target_dir, lib_dir)


def _build_kilo(target_dir: str, project_dir: str, lib_dir: str) -> None:
    from bootstrap_kilo import generate_kilo_plugin

    generate_kilo_plugin(target_dir, lib_dir)


#: Host -> the generator that writes its real-time enforcement payload.
#:
#: A host absent here has no such generator, which is a DECLARED position rather
#: than an oversight. Cursor is present because it receives native hooks.
#: `cross_check_against_disk` is what stops this from becoming a list of
#: good intentions — it compares this table against the profiles on disk.
MECHANISM_BUILDERS: dict[str, Callable[[str, str, str], None]] = {
    "claude": _build_claude,
    "cursor": _build_cursor,
    "qwen": _build_qwen,
    "opencode": _build_opencode,
    "kilo": _build_kilo,
}


def _hook_entries(settings: dict) -> Iterator[tuple[str, str]]:
    """(capability id, matcher) for every hook script named in a settings payload.

    The capability id carries the EVENT as well as the script basename, because a
    hook moved from PreToolUse to PostToolUse is a different capability wearing
    the same file name. The rest of the command — interpreter, absolute paths —
    differs between hosts by construction and comparing it would report every host
    as different from every other, every time.

    The MATCHER rides alongside rather than inside the id. It is what the two
    hosts actually disagree about today, and folding it into the id would report
    the disagreement as "a capability Claude has and Qwen lacks", which is the
    wrong sentence about the right fact.
    """
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            matcher = str(entry.get("matcher", ""))
            for hook in entry.get("hooks") or []:
                if not isinstance(hook, dict):
                    continue
                for token in str(hook.get("command", "")).replace("\\", "/").split():
                    if token.endswith(".py"):
                        yield f"{KIND_HOOK}:{event}:{os.path.basename(token)}", matcher


def _merge_matchers(a: str, b: str) -> str:
    """The matcher of a capability registered on two entries: the union of names."""
    if a.strip() in ("", "*") or b.strip() in ("", "*"):
        return ""
    return "|".join(sorted(set(a.split("|")) | set(b.split("|"))))


def _read_profile(profile_dir: str) -> dict[str, str]:
    """Capabilities visible in a host profile directory, mapped to their matcher.

    Hooks and plugins alike: a plugin has no matcher, so it maps to the empty
    string. That is a real absence, not a placeholder — OpenCode's plugin runs on
    what it decides internally, and inventing a matcher for it would put a fact in
    the table that no file supports.
    """
    found: dict[str, str] = {}
    if not os.path.isdir(profile_dir):
        return found
    for name in ("settings.json", "settings.local.json"):
        path = os.path.join(profile_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            for cap, matcher in _hook_entries(data):
                # A hook may sit on more than one entry (PR #5 registers the
                # MCP editors on their own line); the capability's matcher is
                # the UNION, and "every tool" absorbs anything narrower. A dict
                # update here kept only the LAST entry, which made two hosts
                # look equal the moment both ended on the same MCP line.
                found[cap] = _merge_matchers(found[cap], matcher) if cap in found else matcher
    native_hooks = os.path.join(profile_dir, "hooks.json")
    if os.path.isfile(native_hooks):
        try:
            with open(native_hooks, encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, ValueError):
            payload = {}
        hooks = payload.get("hooks", {}) if isinstance(payload, dict) else {}
        if isinstance(hooks, dict):
            for event, entries in hooks.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    command = str(entry.get("command", ""))
                    try:
                        parts = split_cursor_command(command)
                    except ValueError:
                        continue
                    if parts[:1] == ["&"]:
                        parts = parts[1:]
                    try:
                        script = parts[parts.index("--script") + 1]
                    except (ValueError, IndexError):
                        continue
                    source_event = _CURSOR_SOURCE_EVENTS.get(str(event), str(event))
                    kind = (
                        "cursor-adapter"
                        if os.path.basename(script)
                        in {"codex_write_gate.py", "memory_preflight_posttool.py"}
                        else KIND_HOOK
                    )
                    cap = f"{kind}:{source_event}:{os.path.basename(script)}"
                    matcher = _shared_cursor_matcher(str(entry.get("matcher", "")))
                    found[cap] = _merge_matchers(found[cap], matcher) if cap in found else matcher
    plugins = os.path.join(profile_dir, "plugins")
    if os.path.isdir(plugins):
        try:
            for n in sorted(os.listdir(plugins)):
                if n.endswith((".js", ".mjs")):
                    found[f"{KIND_PLUGIN}:{n}"] = ""
        except OSError:
            pass
    return found


def matcher_table(lib_dir: str | None = None) -> dict[str, dict[str, str]]:
    """Run every mechanism generator into a clean tree; return what each produced.

    A clean tree, not the repository's own profiles: the subject is what bootstrap
    WOULD deploy from the source as it stands, so a stale deployed profile cannot
    make a regression look settled.
    """
    lib = lib_dir or _REPO
    # The generators import from <lib>/bootstrap. The import-time path above is
    # module-relative and misses it from the deployed copy (`.claude/scripts/`).
    bootstrap_dir = os.path.join(lib, "bootstrap")
    if os.path.isdir(bootstrap_dir) and bootstrap_dir not in sys.path:
        sys.path.insert(0, bootstrap_dir)
    table: dict[str, dict[str, str]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = os.path.join(tmp, "project")
        os.makedirs(project_dir, exist_ok=True)
        for ide, build in sorted(MECHANISM_BUILDERS.items()):
            target = os.path.join(tmp, ide)
            os.makedirs(target, exist_ok=True)
            try:
                build(target, project_dir, lib)
            except Exception as exc:  # noqa: BLE001 — a broken generator IS the finding
                table[ide] = {f"error:{type(exc).__name__}": str(exc)[:200]}
                continue
            table[ide] = _read_profile(target)
    return table


def cross_check_against_disk(project_dir: str) -> list[str]:
    """Complaints where a DEPLOYED profile bears a kind this module cannot build.

    The guard on MECHANISM_BUILDERS. If someone teaches bootstrap to deploy hooks
    for Cursor and does not add a builder here, the gate would go on reporting
    Cursor as mechanism-free — green, and wrong. The deployed profile is an
    independent witness, so ask it.

    Silent about a host that is simply not deployed here: a consumer project has
    one profile, and "the other four are missing" is not a finding.
    """
    from ide_utils import IDE_REGISTRY

    problems: list[str] = []
    for ide, entry in sorted(IDE_REGISTRY.items()):
        if ide in MECHANISM_BUILDERS:
            continue
        deployed = _read_profile(os.path.join(project_dir, entry["config_dir"]))
        if deployed:
            problems.append(
                f"{ide} has {len(deployed)} deployed capability/ies "
                f"({', '.join(sorted(deployed)[:3])}...) but no builder in "
                "MECHANISM_BUILDERS — the parity table cannot see them"
            )
    return problems
