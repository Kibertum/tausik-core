"""Apply the DYNAMIC:START/END section into agent-instruction files.

Shared by `tausik update-claudemd` so CLAUDE.md and AGENTS.md (and any future
sibling) stay in sync from one dynamic-content source. (v15p-agents-md-bootstrap)
"""

from __future__ import annotations

import difflib
import logging
import os
import sys

_log = logging.getLogger(__name__)

_MARKER_START = "<!-- DYNAMIC:START -->"
_MARKER_END = "<!-- DYNAMIC:END -->"

# The agent-instruction sibling that `update-claudemd` keeps in lockstep with
# CLAUDE.md. The name lives HERE, in the producer, so every consumer that needs
# to recognise this file as framework-maintained ceremony (e.g. the
# complexity-understatement proxy, which must NOT count it as behaviour-bearing)
# reads it from one place instead of hand-listing a copy that can drift.
CLAUDEMD_SIBLING_BASENAME = "AGENTS.md"


def apply_dynamic_section(path: str, dynamic_content: str, dry_run: bool) -> tuple[str, bool]:
    """Replace the DYNAMIC section of `path` with `dynamic_content`.

    Returns (message, changed). `changed` is False when the marker is absent or
    the file is already up-to-date. On dry_run a unified diff is printed and
    `changed` reflects whether the file would change (no write performed).
    """
    dry_run = bool(dry_run)
    name = os.path.basename(path)
    try:
        with open(path, encoding="utf-8") as f:
            original = f.read()
    except OSError as e:
        return f"Error reading {name}: {e}", False

    if _MARKER_START not in original:
        return f"Warning: {_MARKER_START} marker not found in {name} — skipped", False

    start_at = original.index(_MARKER_START)
    before = original[: start_at + len(_MARKER_START)]
    # Locate END strictly AFTER START so a marker mentioned earlier in body text,
    # or a second marker pair, cannot mis-slice and drop content.
    end_at = original.find(_MARKER_END, start_at + len(_MARKER_START))
    if end_at != -1:
        after = original[end_at:]
        new_content = f"{before}\n{dynamic_content}\n{after}"
    else:
        new_content = f"{before}\n{dynamic_content}\n{_MARKER_END}\n"

    if new_content == original:
        return f"{name} already up-to-date ({path})", False

    if dry_run:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"{name} (current)",
            tofile=f"{name} (would write)",
            lineterm="",
        )
        sys.stdout.write("".join(diff))
        sys.stdout.write("\n")
        return f"{name} would change ({path})", True

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return f"{name} updated ({path})", True


#: `claudemd.sibling_dynamic` in config: True (default) — the AGENTS.md sibling
#: is refreshed with the block TRIMMED of other projects' knowledge; False — the
#: sibling is not written at all. GitLab #14: in a project that keeps CLAUDE.md
#: out of git for the sake of auto-refresh, AGENTS.md stays tracked, and every
#: session put the session number, the counters and "Shared knowledge — from
#: other projects" into the repository's history.
SIBLING_DYNAMIC_KEY = "sibling_dynamic"


def sibling_dynamic_enabled(tausik_dir: str | None = None) -> bool:
    """Read `claudemd.sibling_dynamic`; only the JSON boolean `false` turns it off."""
    try:
        from project_config import load_config

        section = load_config(tausik_dir).get("claudemd")
    except Exception as e:  # noqa: BLE001 — an unreadable config keeps today's behaviour, out loud
        _log.warning("claudemd.sibling_dynamic: config unreadable (%s) — sibling stays enabled", e)
        return True
    if not isinstance(section, dict):
        return True
    return section.get(SIBLING_DYNAMIC_KEY, True) is not False


def strip_foreign_knowledge(block: str) -> str:
    """The block a TRACKED sibling may carry: the shared-knowledge section removed.

    The section runs from its heading to the next blank line (the producer
    separates sections with one). A memory-tail heading left with nothing under
    it is dropped too — a heading over nothing is not a tail, and the state gate
    says so.
    """
    from service_knowledge_aggregates import MEMORY_TAIL_HEADING, SHARED_KNOWLEDGE_HEADING

    kept: list[str] = []
    skipping = False
    for line in block.splitlines():
        if line.startswith(SHARED_KNOWLEDGE_HEADING):
            skipping = True
            continue
        if skipping:
            if line.strip():
                continue
            skipping = False
        kept.append(line)
    # The producer's separators (a blank before the shared heading, a lone space
    # before a warning) would stack once the section between them is gone.
    collapsed: list[str] = []
    for line in kept:
        if not line.strip() and collapsed and not collapsed[-1].strip():
            continue
        collapsed.append(line)
    kept = collapsed
    while kept and not kept[-1].strip():
        kept.pop()
    if kept and kept[-1].strip() == MEMORY_TAIL_HEADING:
        kept.pop()
        while kept and not kept[-1].strip():
            kept.pop()
    return "\n".join(kept)


def plan_dynamic_writes(
    primary: str, block: str, tausik_dir: str | None = None
) -> list[tuple[str, str]]:
    """(path, content) for every file `update-claudemd` writes.

    The primary gets the whole block. The AGENTS.md sibling — tracked in most
    projects — gets it without other projects' knowledge, or nothing at all when
    `claudemd.sibling_dynamic` is false. Both callers AND the state gate go
    through this plan, so what is written and what is judged cannot disagree.

    The knob is read from the project that OWNS the files being written — the
    `.tausik/` beside the primary — not from whichever database the caller
    holds: `update-claudemd --claudemd <other project>/CLAUDE.md` must honour
    that project's opt-out, not this one's (review, session #259; the same
    one-source rule as resolve_project_dir).
    """
    if tausik_dir is None:
        tausik_dir = os.path.join(os.path.dirname(os.path.abspath(primary)), ".tausik")
    plan = [(primary, block)]
    if sibling_dynamic_enabled(tausik_dir):
        plan.extend(
            (path, strip_foreign_knowledge(block)) for path in resolve_sibling_targets(primary)[1:]
        )
    return plan


def resolve_sibling_targets(primary: str) -> list[str]:
    """Return [primary] plus an existing AGENTS.md sibling in the SAME directory
    as `primary`, de-duplicated. The sibling is resolved relative to primary's
    dir (never a bare cwd-relative 'AGENTS.md', which under an MCP server's cwd
    could hit an unrelated file)."""
    targets = [primary]
    sibling = os.path.join(os.path.dirname(primary) or ".", CLAUDEMD_SIBLING_BASENAME)
    if os.path.exists(sibling) and os.path.abspath(sibling) != os.path.abspath(primary):
        targets.append(sibling)
    return targets
