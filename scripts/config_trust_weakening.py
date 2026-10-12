"""What the tiers ABOVE the project hold weaker than the framework default.

`config_trust.enforce_project_tier` polices the tier below and names every
rejection it makes. Nothing polices the tiers above — deliberately; they are the
operator's word, and the module docstring next door calls that an honest threat
boundary rather than an oversight. But nothing NAMED them either, and that is a
different failure: `doctor` printed "no project-scope key weakens enforcement",
literally true, at the moment `~/.tausik/config.json` was bypassing the signed
QG-2 receipt in this repository and holding a blocking gate off in every project
on the machine. A reader takes that line to mean nothing is weakened.

This module moves no boundary and refuses nothing. It answers one question the
resolver structurally cannot: WHICH guarded keys does a trusted tier hold weaker
than the framework's own default, and which file says so. The resolver cannot
answer it because it measures a candidate against the trusted tiers themselves —
and a tier compared against itself is never weaker than itself.
"""

from __future__ import annotations

import sys
from typing import Any, NamedTuple

# `_dig` and `_expand` are internal to the resolver but shared on purpose: a
# second walk over GUARDS written here would be a second answer to "which keys
# are guarded", and the two would drift the first time a guard is added.
from config_trust import (
    GUARDS,
    _dig,
    _expand,
    deep_merge,
    framework_default,
    managed_config_path,
    raw_layers,
    user_config_path,
)
from config_trust_projects import PROJECTS_KEY, machine_wide, project_key, scoped_entry

REASON_CLIP_CHARS = 180

# Operator notes already written beside a weakened key in the wild, least
# specific last. `~/.tausik/config.json` carries `_reason` beside
# `task_done.auto_verify`; a gate carries `_disabled_reason` beside `enabled`;
# `.tausik/config.json` here carries the key-specific `_auto_verify_reason`.
REASON_KEYS = ("_reason", "_disabled_reason")


class Weakening(NamedTuple):
    """One guarded key a TRUSTED tier holds weaker than the framework default.

    Not a `Rejection`, and it never becomes one: nothing was refused and the
    value below IS in effect. So this type carries no verdict — only the facts a
    reader needs to judge for themselves, the source tier and file among them.
    """

    key: str
    tier: str  # "user" | "managed"
    value: Any
    default: Any
    note: str
    reason: str  # operator's note beside the key; "" when none was recorded
    source: str  # the file the value comes from
    in_effect: bool  # False when the project tier tightens it back here
    scope: str = "machine"  # "machine" (top level) | "project" (a `projects` entry)

    def describe(self, project_dir: str | None = None) -> str:
        why = f"reason: {clip_reason(self.reason)}" if self.reason else "NO REASON RECORDED"
        standing = (
            "IN EFFECT and not rejected"
            if self.in_effect
            else "NOT in effect here — this project tightens it back"
        )
        where = (
            "scoped to this project"
            if self.scope == "project"
            else "MACHINE-WIDE (every project on this box)"
        )
        text = (
            f"{self.key}={self.value!r} weakens {self.note} "
            f"(framework default {self.default!r}); set by the {self.tier} tier, "
            f"{where}, {standing}; {why} [{self.source}]"
        )
        if self.scope == "machine" and self.in_effect and project_dir:
            text += (
                " — if it belongs to this project only, move it under "
                f'{PROJECTS_KEY}["{project_key(project_dir)}"] in that file'
            )
        return text


def _console_safe(text: str) -> str:
    """Survive a legacy code page instead of taking the whole check down with it.

    An operator writes the reason in their own language. `doctor` prints through
    plain `print`, which raises UnicodeEncodeError on a cp1252 console, and the
    try/except around that block would turn the crash into "Config knobs: load
    failed" — losing the very line this module exists to produce, and losing it
    under a message about something else.
    """
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        return text.encode(enc, "replace").decode(enc, "replace")
    except (LookupError, UnicodeError):
        return text


def clip_reason(text: str) -> str:
    """One bounded line. The full note stays in the file `describe` names: a
    health check that spills three paragraphs teaches the reader to skip it."""
    flat = " ".join(text.split())
    if len(flat) > REASON_CLIP_CHARS:
        flat = flat[:REASON_CLIP_CHARS].rsplit(" ", 1)[0] + " [...]"
    return _console_safe(flat)


def reason_for(layer: dict, path: tuple[str, ...]) -> str:
    """The operator's note sitting beside a weakened key, "" when absent.

    A weakening with a recorded reason and one without are different events, and
    the first must not reach the reader looking like a mystery — so the note is
    shown rather than swallowed.
    """
    found, parent = _dig(layer, path[:-1])
    if not found or not isinstance(parent, dict):
        return ""
    for name in (f"_{path[-1]}_reason", *REASON_KEYS):
        value = parent.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def foreign_scoped_entries(user: dict, managed: dict, project_dir: str | None) -> int:
    """How many ``projects`` entries across both tiers name OTHER projects.

    They are not applied here, so they are not weakenings — but an operator
    reading ``doctor`` on a fresh box deserves to know the mechanism gotcha #690
    describes is in use and pointed elsewhere.
    """
    wanted = project_key(project_dir) if project_dir else None
    count = 0
    for layer in (user, managed):
        section = layer.get(PROJECTS_KEY)
        if not isinstance(section, dict):
            continue
        for spelled, entry in section.items():
            if isinstance(spelled, str) and isinstance(entry, dict) and project_key(spelled) != wanted:
                count += 1
    return count


def trusted_tier_weakenings(
    user: dict | None = None,
    managed: dict | None = None,
    effective: dict | None = None,
    project_dir: str | None = None,
) -> list[Weakening]:
    """Guarded keys the trusted tiers hold WEAKER than the framework default.

    Tiers are read from disk unless supplied (tests, callers already holding
    them). Passing only `user` leaves `managed` empty, and vice versa.

    `effective` is the RESOLVED config, and it decides `in_effect`. A project
    may tighten a guarded key back — on guarded keys the stricter value wins in
    both directions — so a weak user tier does not by itself mean weak
    enforcement here, and reporting it as such would be the mirror image of the
    defect this module repairs: an alarm that is literally true and misread.
    Defaults to the trusted tiers alone, which is the honest answer for a caller
    that has no project layer; a caller holding the resolved config must pass it.
    """
    if user is None and managed is None:
        user, managed = raw_layers()
    user, managed = user or {}, managed or {}
    source = {"user": user_config_path(), "managed": managed_config_path()}
    weakenings: list[Weakening] = []
    # Two passes: the machine-wide part of each tier, then the entry scoped to
    # THIS project. A scoped entry for another project is neither — it does
    # not apply here and is counted by `foreign_scoped_entries` instead.
    passes = (
        ("machine", machine_wide(user), machine_wide(managed)),
        (
            "project",
            scoped_entry(user, "user", project_dir),
            scoped_entry(managed, "managed", project_dir),
        ),
    )
    if effective is None:
        effective = deep_merge(
            deep_merge(passes[0][1], passes[1][1]), deep_merge(passes[0][2], passes[1][2])
        )
    for scope, user_part, managed_part in passes:
        merged = deep_merge(user_part, managed_part)
        for guard in GUARDS:
            for path in _expand(guard, merged):
                found, value = _dig(merged, path)
                if not found:
                    continue
                default = framework_default(guard, path)
                if default is None or not guard.is_weaker(value, default):
                    continue
                # Managed wins the merge, so it owns the effective value whenever
                # both tiers name the key. Naming the other file would send the
                # reader to a line whose edit changes nothing.
                tier = "managed" if _dig(managed_part, path)[0] else "user"
                live, live_value = _dig(effective, path)
                weakenings.append(
                    Weakening(
                        key=".".join(path),
                        tier=tier,
                        value=value,
                        default=default,
                        note=guard.note,
                        reason=reason_for(merged, path),
                        source=source[tier],
                        in_effect=live and guard.is_weaker(live_value, default),
                        scope=scope,
                    )
                )
    return weakenings


def summary(effective: dict, project_dir: str | None = None) -> tuple[list[str], str | None]:
    """(warning lines, OK detail) for doctor's trust-tier check.

    Four outcomes, and each says something the others do not: a weakening that
    IS in effect warns; one the project tightens back is named inside the OK
    line, because silence would lose the fact that the machine's tier is set
    that way at all; nothing weak at all prints the plain OK. Rejections are the
    caller's to print — they come from the resolver, not from here. Entries
    scoped to OTHER projects are counted, never applied: the count is the
    visible sign that the mechanism of gotcha #690 is in use and points away.
    """
    user, managed = raw_layers()
    weakened = trusted_tier_weakenings(user, managed, effective=effective, project_dir=project_dir)
    live = [w for w in weakened if w.in_effect]
    if live:
        return [w.describe(project_dir) for w in live], None
    detail = "no key weakens enforcement (project, user, managed)"
    if weakened:
        keys = ", ".join(w.key for w in weakened)
        detail += f"; a trusted tier holds {keys} weaker — tightened back here"
    foreign = foreign_scoped_entries(user, managed, project_dir)
    if foreign:
        noun = "entry" if foreign == 1 else "entries"
        detail += f"; {foreign} project-scoped {noun} for other projects, not applied here"
    return [], detail
