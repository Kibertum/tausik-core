"""Does the rules file a host reads still tell that host the truth?

enforcement-coverage-is-two-of-five-hosts. Bootstrap handed all five hosts the
same opening line — "Quality gates enforce these automatically" — while, measured
on this project in session #230, only claude and qwen carried hooks (23 commands
over 6 events) and opencode a plugin. Cursor and kilo carried nothing. Two of the
five were told their rules were enforced, and nothing anywhere said otherwise.

`bootstrap_enforcement` now composes that opening line from what is on disk, so a
FRESH generation cannot repeat the claim. This check exists because that is not
enough twice over:

  * Rules files are preserve-if-exists. Every install that already has a
    CLAUDE.md or a .cursorrules keeps the old sentence forever, and re-running
    bootstrap will not replace it.
  * The disk moves after generation. Delete the hooks stanza from
    `.claude/settings.json` and the file still claims automatic enforcement, with
    nothing to notice.

So the check compares the CLAIM IN THE FILE against the MECHANISM ON DISK, which
is the defect itself rather than a proxy for it. Three states, and only one red:

  * AGREES      — the file's claim matches what is deployed.
  * NO CLAIM    — an old or hand-written file that says nothing either way. Not
                  a red: silence is not a false statement, and reddening here
                  would light up every project that predates this check.
  * CONTRADICTS — the file claims enforcement the profile does not have, or
                  denies enforcement the profile does have. Nobody chose this
                  state; it is what the defect produces.

THE GAP ITSELF IS NOT A RED. Cursor and kilo having no mechanism is a declared
position, not a fault — declaring it was the deliverable, closing it was not. A
warning there would train the reader to ignore this check on every install.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from enforcement_coverage import (
    NO_MECHANISM_NOTICE,
    deployed_enforcement,
    describe_enforcement,
    profile_dir_for,
)
from ide_utils import IDE_REGISTRY

_LABEL = "Enforcement coverage"

#: The claim, matched on the words that survive every wording of it. NOT the
#: whole sentence: the current one carries a count that changes with the profile,
#: and the one this check exists to catch is the LEGACY line —
#: "Quality gates (`.tausik/tausik gates status`) enforce these automatically." —
#: sitting in every rules file generated before this release. A matcher tuned to
#: the new sentence would be blind to precisely the files that are still lying.
_CLAIM_MARKER = "enforce these automatically"

#: The first words of NO_MECHANISM_NOTICE. Taken FROM the constant rather than
#: retyped, so the two cannot drift apart.
_DENIAL_PREFIX = NO_MECHANISM_NOTICE.split(".**", 1)[0] + ".**"


def host_specific_rules_file(ide: str) -> str | None:
    """The rules file that speaks for THIS host alone, or None.

    Derived, not listed. `IDE_REGISTRY` already records what each host reads, and
    a file two hosts read — AGENTS.md, which codex and kilo share — cannot make a
    statement about either of them in particular. Comparing such a file against
    one host's profile would manufacture a contradiction out of a sentence
    written for nobody.
    """
    entry = IDE_REGISTRY.get(ide)
    if not entry:
        return None
    rules = entry.get("rules_file")
    if not rules:
        return None
    shared = sum(1 for e in IDE_REGISTRY.values() if e.get("rules_file") == rules)
    return None if shared > 1 else rules


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def check_enforcement_coverage(project_dir: str) -> Iterator[tuple[str, str, str]]:
    """Per-host coverage, plus a warning wherever a rules file contradicts disk."""
    covered: list[str] = []
    bare: list[str] = []
    contradictions: list[str] = []

    for ide in sorted(IDE_REGISTRY):
        rules_rel = host_specific_rules_file(ide)
        profile = profile_dir_for(project_dir, ide)
        if not profile or not os.path.isdir(profile):
            continue  # host not scaffolded here — nothing measured, nothing claimed
        what = describe_enforcement(deployed_enforcement(profile))
        (covered if what else bare).append(f"{ide}: {what or 'none'}")

        if rules_rel is None:
            continue
        text = _read(os.path.join(project_dir, rules_rel))
        if text is None:
            continue
        claims = _CLAIM_MARKER in text
        denies = _DENIAL_PREFIX in text
        if claims and not what:
            contradictions.append(
                f"{rules_rel} tells {ide} the gates enforce automatically, but no "
                f"mechanism is deployed in {os.path.basename(profile)}"
            )
        elif denies and what:
            contradictions.append(
                f"{rules_rel} tells {ide} the rules are instructions only, but "
                f"{what} are deployed in {os.path.basename(profile)}"
            )

    if not covered and not bare:
        return

    summary = "; ".join(covered + bare)
    if bare:
        summary += (
            " - where none is deployed, nothing intercepts that host's own editor "
            "or shell; what goes through our tools is still refused (next line)"
        )
    yield ("ok", _LABEL, summary)

    # By RULE, not by host. "cursor: none" is true and coarse: on a host with no
    # interception every task closure, knowledge write and task opening is still
    # refused, because those go through our own tools. Saying only the first half
    # understates the product to the reader who most needs the truth.
    if bare:
        from rule_coverage import NEEDS_INTERCEPTION, coverage_for_host

        example = bare[0].split(":", 1)[0]
        unheld = [
            r.rule
            for r, holds in coverage_for_host(profile_dir_for(project_dir, example))
            if holds == NEEDS_INTERCEPTION
        ]
        held = [
            r.rule
            for r, holds in coverage_for_host(profile_dir_for(project_dir, example))
            if holds != NEEDS_INTERCEPTION
        ]
        yield (
            "ok",
            _LABEL,
            f"by rule, where no mechanism is deployed: REFUSED anyway via our own "
            f"tools — {', '.join(held)}; NOT enforced — {', '.join(unheld)} "
            "(each governs an action the host's own editor or shell performs)",
        )

    for detail in contradictions:
        yield (
            "warn",
            _LABEL,
            detail + ". Re-run `bootstrap --ide all`, or delete the file to have it regenerated",
        )
