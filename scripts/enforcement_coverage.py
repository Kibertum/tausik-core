"""Is a rule on this host CHECKED, or only stated?

Bootstrap hands every host the same rules text. That text opened with "Quality
gates enforce these automatically", and on two of the five hosts it was false:
measured on this project (session #230), claude and qwen carry 23 hook commands
over 6 events, opencode one plugin, cursor and kilo nothing at all. Nothing said
so, and the single hand-written caveat that did exist covered one rule of eleven,
for one host, and named the wrong reason.

THE ANSWER IS DERIVED, NEVER DECLARED. A rule-to-mechanism table would record
what we meant to deploy and drift from what we did — the same drift, one level
up. So the notice counts the artifacts bootstrap actually left in the host's
profile directory (decision #335).

WHAT THIS MODULE REFUSES TO DO is close the gap. Cursor and kilo get an honest
sentence, not a generated hooks payload: shipping one would be a different task
and a much larger claim. Declaring the gap is the whole deliverable.
"""

from __future__ import annotations

import json
import os

# The one map of host -> profile directory and host -> rules file. Imported
# rather than restated: a second list is what rots.
#
# THIS MODULE LIVES IN scripts/, NOT bootstrap/, and the direction is load-bearing.
# Bootstrap deploys `scripts/` into every host profile and does NOT deploy
# `bootstrap/`, so a scripts module importing from bootstrap resolves in this
# repository and fails everywhere it is installed — which is exactly what `doctor`
# reported the first time this was tried.
from ide_utils import IDE_REGISTRY

#: Where a host keeps the payload bootstrap writes for it. Both entries name an
#: ARTIFACT SHAPE, not a host: whatever profile directory is handed in gets
#: probed for both, so a host that grows a second mechanism is counted without
#: anyone remembering to add it here.
# `hooks.json` is Codex's name for the same payload. Added in session #241 with
# the Codex scaffold, and the omission was not cosmetic: `doctor` reported
# "codex: none" while twenty-four hook commands sat deployed in `.codex/`, i.e.
# a report ABOUT ENFORCEMENT understated enforcement. A reader deciding whether
# that host is guarded would have been told the opposite of the truth.
SETTINGS_FILES = ("settings.json", "settings.local.json", "hooks.json")
PLUGIN_SUBDIR = "plugins"
PLUGIN_SUFFIXES = (".js", ".mjs")


def profile_dir_for(project_dir: str | None, ide: str | None) -> str | None:
    """The host profile bootstrap writes for ``ide``, or None when there is none.

    None for a host-agnostic file — AGENTS.md passes ``ide=None``, and kilo reads
    it rather than a file of its own. The answer there is UNKNOWN, and unknown is
    not zero (decision #334): the caller must say so rather than pick a host.
    """
    if not project_dir or not ide:
        return None
    entry = IDE_REGISTRY.get(ide)
    return os.path.join(project_dir, entry["config_dir"]) if entry else None


def deployed_enforcement(profile_dir: str | None) -> dict[str, int]:
    """Real-time enforcement artifacts bootstrap actually left in a host profile.

    Counted from the FILES ON DISK, never from a rule-to-mechanism table. Such a
    table is the defect this exists to end: it would record what we meant to
    deploy and drift from what we did, exactly as the rules text drifted from the
    mechanism.

    Returns counts BY SHAPE (``hooks``, ``plugins``) rather than one total,
    because the sentence built from it names what is deployed, and calling
    OpenCode's plugin a hook would be a small lie of the same family as the one
    being fixed.

    Zero on anything unreadable. Failing to read a profile means we cannot show
    that enforcement is deployed, and the honest answer to "cannot show" is the
    cautious one — never the flattering one.
    """
    found = {"hooks": 0, "plugins": 0}
    if not profile_dir or not os.path.isdir(profile_dir):
        return found
    for name in SETTINGS_FILES:
        path = os.path.join(profile_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        hooks = data.get("hooks") if isinstance(data, dict) else None
        if not isinstance(hooks, dict):
            continue
        for entries in hooks.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("hooks"), list):
                    found["hooks"] += len(entry["hooks"])
    plugins = os.path.join(profile_dir, PLUGIN_SUBDIR)
    if os.path.isdir(plugins):
        try:
            found["plugins"] = sum(1 for n in os.listdir(plugins) if n.endswith(PLUGIN_SUFFIXES))
        except OSError:
            pass
    return found


def describe_enforcement(found: dict[str, int]) -> str:
    """ "23 hook commands", "1 plugin", "23 hook commands and 1 plugin", or ""."""
    parts = []
    if found.get("hooks"):
        n = found["hooks"]
        parts.append(f"{n} hook command{'s' if n != 1 else ''}")
    if found.get("plugins"):
        n = found["plugins"]
        parts.append(f"{n} plugin{'s' if n != 1 else ''}")
    return " and ".join(parts)


#: Emitted where the host is known and carries no mechanism. Kept as a module
#: constant so a test can assert the honest text is what shipped, without
#: re-typing a sentence that would then drift from the one in use.
NO_MECHANISM_NOTICE = (
    "**NO REAL-TIME MECHANISM IS DEPLOYED HERE.** Bootstrap wrote no hook and "
    "no plugin into this host's profile, so nothing intercepts this host's own "
    "editor or shell. That is a statement about what TAUSIK deployed, not about "
    "what the host supports. It does NOT mean nothing is checked — see below.\n"
)

#: Emitted where the file is read by more than one host and cannot know which.
UNKNOWN_HOST_NOTICE = (
    "**WHETHER THE RULES BELOW ARE ENFORCED DEPENDS ON THE HOST READING THIS "
    "FILE.** This file is host-agnostic, so it cannot answer that; "
    "`.tausik/tausik doctor` prints the coverage measured on disk per host. "
    "On a host where TAUSIK deployed no real-time mechanism, everything below "
    "is instructions, not checks: the gates still exist in the CLI "
    "(`.tausik/tausik verify`, `task done`) and you reach them by running them.\n"
)


def build_enforcement_notice(profile_dir: str | None) -> str:
    """Say, per host, whether the constraints below are CHECKED or merely stated.

    Three answers, not two. A boolean would have to call the host-agnostic file
    either enforced or unenforced, and both are guesses about a host nobody has
    named yet.
    """
    if profile_dir is None:
        return UNKNOWN_HOST_NOTICE
    what = describe_enforcement(deployed_enforcement(profile_dir))
    if not what:
        return NO_MECHANISM_NOTICE
    return (
        f"Quality gates enforce these automatically: bootstrap deployed {what} "
        "into this host's profile, so a violation is refused rather than reported.\n"
    )
