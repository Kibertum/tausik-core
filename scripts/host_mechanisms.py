"""What each host can actually ENFORCE, derived by running the real generators.

cross-model-parity-has-no-gate. A capability can go Claude-only and nothing
notices. Measured on this tree (session #230): claude and qwen carry the same 23
hook commands and that pair IS guarded (tests/test_bootstrap_hooks_parity.py);
the other three hosts are guarded by nothing at all — opencode carries one QG-0
plugin, cursor and kilo carry no real-time mechanism whatsoever.

HOW THE TABLE IS OBTAINED. The generators are RUN, into a throwaway tree, and
what lands on disk is read back. Not a list in the code of what each host is
supposed to get: such a list records intent and drifts from the deployment
exactly as the rules text drifted from the mechanism (decision #335). The three
builders below are the mechanism generators that exist; `cross_check_against_disk`
holds them honest against the profiles bootstrap really deployed, so a fourth one
added and forgotten here is caught rather than silently uncovered.

COMPARISON IS WITHIN A MECHANISM KIND, NEVER ACROSS. OpenCode enforces through a
plugin and Claude through hook commands; asking whether `tausik-qg0.js` is
"missing" from Claude's hook list is a question with no meaning, and answering it
would fill the gate with 23 false differences on day one. So hosts are compared
only with the hosts that share their extension point. Whether a host has an
extension point AT ALL is a different statement, and it is already made twice —
by the enforcement notice each host's rules file opens with, and by `doctor`. It
is not restated here.

WHAT THIS MODULE DOES NOT DO is decide which of the four host registries is the
truth. There are four (`bootstrap_config.IDE_DIRS`, `ide_utils.IDE_REGISTRY`,
`skill_profile_detect.VALID_IDES`, `providers`), and they already disagree —
measured here in session #230: the first two know 7 hosts, the last two know 4
apiece and not the same 4, so `config set ide_profile kilo` is refused for a host
bootstrap fully scaffolds. Collapsing them is
`four-ide-registries-collapse-into-one`, deferred to 1.10. `cross_check_against_disk`
reads `ide_utils.IDE_REGISTRY` and says so out loud, and a test pins the measured
divergence so it cannot widen quietly.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Callable, Iterator

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BOOTSTRAP = os.path.join(_REPO, "bootstrap")
if os.path.isdir(_BOOTSTRAP) and _BOOTSTRAP not in sys.path:
    sys.path.insert(0, _BOOTSTRAP)

#: Prefixes that make a capability name say WHICH extension point carries it.
KIND_HOOK = "hook"
KIND_PLUGIN = "plugin"


def _build_claude(target_dir: str, project_dir: str, lib_dir: str) -> None:
    from bootstrap_generate import generate_settings_claude

    generate_settings_claude(target_dir, project_dir, lib_dir=lib_dir)


def _build_qwen(target_dir: str, project_dir: str, lib_dir: str) -> None:
    from bootstrap_qwen import generate_settings_qwen

    generate_settings_qwen(target_dir, project_dir, venv_python=sys.executable, lib_dir=lib_dir)


def _build_opencode(target_dir: str, project_dir: str, lib_dir: str) -> None:
    from bootstrap_opencode import generate_opencode_plugin

    generate_opencode_plugin(target_dir, lib_dir)


#: Host -> the generator that writes its real-time enforcement payload.
#:
#: A host absent here has no such generator, which is a DECLARED position rather
#: than an oversight: cursor and kilo get MCP config and rules text and nothing
#: that runs. `cross_check_against_disk` is what stops this from becoming a list
#: of good intentions — it compares this table against the profiles on disk.
MECHANISM_BUILDERS: dict[str, Callable[[str, str, str], None]] = {
    "claude": _build_claude,
    "qwen": _build_qwen,
    "opencode": _build_opencode,
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
