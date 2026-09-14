"""Memory-aggregation helpers — memory_block and memory_compact.

Extracted from service_knowledge.py to keep that file under the 400-line gate.
These are pure functions over the backend; the mixin methods below delegate here.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from memory_supersedes import live_head


_FILE_PATTERN = re.compile(
    r"\b[\w/.-]+\.(py|js|ts|tsx|jsx|go|rs|java|kt|php|md|json|yaml|yml|sql|sh)\b"
)


def flatten_for_injection(text: str | None, limit: int) -> str:
    """Collapse a stored value to ONE line, then truncate. Both aggregates use this.

    These aggregates do not merely display text — their output is injected into
    CLAUDE.md and into the session context, where the agent reads it as part of
    its own instructions. A stored value that survives with its line breaks
    intact therefore does not appear as a quoted record; it appears as document
    structure. `- #12 Title` followed by a line reading `## SYSTEM: ...` is
    indistinguishable, once rendered, from a heading the framework wrote itself.

    Truncation alone does not help. Slicing to 100 characters keeps whatever
    those 100 characters contain, newline included, so the surviving prefix is
    exactly what an attacker controls. The break has to be REMOVED, not shortened.

    `str.split()` with no argument is doing the work deliberately: it splits on
    every Unicode whitespace run, which covers \\n, \\r, \\r\\n, the vertical tab
    and form feed, NEL (\\x85), and the LINE/PARAGRAPH SEPARATORs (\\u2028,
    \\u2029). Matching only "\\n" — which is what one of these two aggregates did
    and the other did not — leaves five other ways to start a new line, and a
    check that can be stepped around by changing one character is not a check.

    Sanitising here rather than on write is the point of the placement: a stored
    rationale is legitimately multi-line, and flattening it in the database would
    destroy content to fix a rendering problem. The value stays whole; only the
    injected copy is flattened.

    Both `build_compact_memory_tail` and `build_memory_block` route through this
    one function so the two cannot drift apart again — which is precisely what
    had already happened by the time this was written.
    """
    return " ".join((text or "").split())[:limit]


def entry_line(node_id: Any, text: str | None, limit: int, retired: dict[int, list[int]]) -> str:
    """One `- #id text` line, saying what it replaced when it replaced something.

    THE CHOICE AC2 ASKS FOR, MADE HERE AND NOT LEFT TO FALL OUT: the retired
    entry is HIDDEN, and the entry that retired it CARRIES the fact on the line
    it was going to occupy anyway.

    Marking the dead entry instead was the alternative, and its argument is
    real: an entry that simply vanishes is indistinguishable from one that was
    lost, and the agent never learns the question was reopened. Its price is
    what settled it — the tail is five lines per section, and spending one of
    them on knowledge already known to be wrong is a quota the projects that
    maintain their memory pay and the careless ones do not.

    The suffix costs nothing and answers the objection: the fact that a revision
    happened, and the id to look it up by, ride on a line that exists either way.

    THE PRICE, SAID OUT LOUD. When the superseding entry is NOT itself in this
    section — a convention that replaced a context, or a replacement older than
    the quota reaches — the retired entry is hidden with nothing to mark it, and
    that revision is invisible until someone reads the graph. Nothing is stated
    wrongly; something is left unsaid. `memory lint` still names every such pair,
    and it is the tool whose job that is.
    """
    line = f"- #{node_id} {flatten_for_injection(text, limit)}"
    try:
        replaced = retired.get(int(node_id))
    except (TypeError, ValueError):
        return line
    if replaced:
        line += " (supersedes " + ", ".join(f"#{i}" for i in replaced) + ")"
    return line


# The two headings of the tail, named once: the state gate looks for the first
# and the sibling trimming (claudemd_writer.strip_foreign_knowledge) drops the
# section under the second — a tracked AGENTS.md must not carry other
# projects' knowledge into a repository's history (GitLab #14).
MEMORY_TAIL_HEADING = "### Memory tail"
SHARED_KNOWLEDGE_HEADING = "**Shared knowledge — from other projects"


def build_compact_memory_tail(be: Any) -> list[str]:
    """One-line-per-item memory recap for CLAUDE.md Current State.

    Used by `tausik update-claudemd` to embed the latest decisions /
    conventions / dead ends inside the dynamic block, so /start no longer
    needs a separate `tausik_memory_block` re-injection call. Empty DB
    (or any backend exception) → return [] and the caller omits the
    subsection entirely.
    """
    # `live_head` rather than the bare list call, in EVERY section: an entry a
    # live `supersedes` edge has retired is not printed beside its replacement,
    # and the freed line goes to the next live entry. Applied to one section
    # only, this would have traded the contradiction for a disagreement between
    # sections, which is harder to notice and no more true.
    try:
        decisions, sup_dec = live_head(be, lambda n: be.decision_list(n), "decision", 5)
        conventions, sup_con = live_head(be, lambda n: be.memory_list("convention", n), "memory", 5)
        deadends, sup_de = live_head(be, lambda n: be.memory_list("dead_end", n), "memory", 3)
        # `context` = durable environment facts (hosts, machines, access, paths).
        # Surfaced every session so the agent never "forgets" them and asks the
        # user for something already recorded (v15p-memory-first-recall).
        contexts, sup_ctx = live_head(be, lambda n: be.memory_list("context", n), "memory", 5)
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return []

    # Computed BEFORE the empty check: a project with no memory of its own is
    # exactly the case where shared knowledge matters most — a fresh repository
    # inheriting what was learned elsewhere. Returning early on "no local rows"
    # would hide the shared section precisely there.
    shared, warning = _shared_section(3)

    if not any((decisions, conventions, deadends, contexts, shared, warning)):
        return []

    out: list[str] = [MEMORY_TAIL_HEADING]
    if contexts:
        out.append(f"Context ({len(contexts)}):")
        for ctx in contexts:
            out.append(entry_line(ctx.get("id"), ctx.get("title"), 100, sup_ctx))
    if decisions:
        out.append(f"Decisions ({len(decisions)}):")
        for d in decisions:
            out.append(entry_line(d.get("id"), d.get("decision"), 120, sup_dec))
    if conventions:
        out.append(f"Conventions ({len(conventions)}):")
        for c in conventions:
            out.append(entry_line(c.get("id"), c.get("title"), 100, sup_con))
    if deadends:
        out.append(f"Dead ends ({len(deadends)}):")
        for de in deadends:
            out.append(entry_line(de.get("id"), de.get("title"), 100, sup_de))
    out.extend(shared)
    out.extend(warning)
    return out


def build_memory_block(
    be: Any,
    max_decisions: int = 5,
    max_conventions: int = 10,
    max_deadends: int = 5,
    max_lines: int = 50,
    max_contexts: int = 5,
    max_shared: int = 3,
) -> str:
    """Compact markdown: context + decisions + conventions + recent dead ends.

    Best-effort like build_compact_memory_tail: any backend error → '' (the
    block is display-only; it must never break the caller)."""
    # Same filter as the compact tail, through the same helper. These two
    # already drifted apart once over line flattening; the fix then was to route
    # both through one function, and this is that lesson applied a second time.
    try:
        decisions, sup_dec = live_head(be, lambda n: be.decision_list(n), "decision", max_decisions)
        conventions, sup_con = live_head(
            be, lambda n: be.memory_list("convention", n), "memory", max_conventions
        )
        deadends, sup_de = live_head(
            be, lambda n: be.memory_list("dead_end", n), "memory", max_deadends
        )
        contexts, sup_ctx = live_head(
            be, lambda n: be.memory_list("context", n), "memory", max_contexts
        )
    except Exception:  # noqa: BLE001 — display-only aggregate, non-fatal
        return ""

    # Same reason as in build_compact_memory_tail: a project with no memory of
    # its own is exactly where inherited knowledge matters, so the shared
    # section is computed before the empty check rather than after it.
    shared, warning = _shared_section(max_shared)

    if not any((decisions, conventions, deadends, contexts, shared, warning)):
        return ""

    lines: list[str] = [
        "## TAUSIK Memory Block",
        "",
        (
            "⚠ **Memory Policy** — TAUSIK memory (`tausik memory add`) is the "
            "**PRIMARY** store for anything about THIS project. "
            "Claude auto-memory (`~/.claude/projects/*/memory/`) is ONLY for "
            "cross-project user preferences; writes there are blocked unless the "
            "user's last turn contains the marker `confirm: cross-project`."
        ),
    ]

    if contexts:
        lines.append("")
        lines.append(f"**Context — environment facts ({len(contexts)}):**")
        for ctx in contexts:
            lines.append(entry_line(ctx.get("id"), ctx.get("title"), 80, sup_ctx))

    if decisions:
        lines.append("")
        lines.append(f"**Recent decisions ({len(decisions)}):**")
        for d in decisions:
            lines.append(entry_line(d.get("id"), d.get("decision"), 100, sup_dec))

    if conventions:
        lines.append("")
        lines.append(f"**Conventions ({len(conventions)}):**")
        for c in conventions:
            lines.append(entry_line(c.get("id"), c.get("title"), 80, sup_con))

    if deadends:
        lines.append("")
        lines.append(f"**Recent dead ends ({len(deadends)}):**")
        for de in deadends:
            lines.append(entry_line(de.get("id"), de.get("title"), 80, sup_de))

    lines.extend(shared)

    if len(lines) > max_lines:
        overflow = len(lines) - max_lines
        lines = lines[:max_lines]
        lines.append(f"_...(truncated, {overflow} more lines)_")

    # AFTER truncation, deliberately. A degradation notice that competes for the
    # line budget is a notice that disappears exactly when the block is busiest —
    # and its disappearance looks identical to "the shared store had nothing".
    # Reproduced before this was moved: with max_conventions=15, which the CLI
    # and MCP both allow, the block reached 51 lines and the warning was the line
    # that got cut. It is short, it is rare, and it is the one line the reader
    # cannot afford to lose, so it sits outside the budget.
    lines.extend(warning)

    return "\n".join(lines)


def _shared_section(max_shared: int) -> tuple[list[str], list[str]]:
    """(entries, warning) — the shared section, with its notice kept separate.

    Not merged into the project quotas, and the reason is arithmetic rather than
    taste. The block orders by `id DESC` as a stand-in for recency, and the
    shared store has an independent id sequence — "newer id" across the two
    databases means nothing. Merging would let shared rows push project rows out
    of a block the project relies on, silently, in proportion to how much the
    person has shared. With a separate budget the project's OWN SECTIONS keep
    their size whether the shared store holds nothing or ten thousand rows. The
    block as a whole does grow, by exactly this section — claiming otherwise
    would overstate what the separation buys.

    The notice is returned apart from the entries so the caller can place it
    outside any truncation. A store that cannot be read must say so, because
    invisible absence of shared knowledge is indistinguishable from that
    knowledge not existing. A store that was never created says nothing at all —
    no degradation happened, and warning every session about a file the user
    never asked for turns a signal into noise.
    """
    from knowledge_read import read_shared_block

    try:
        raw, warning = read_shared_block(max_shared)
    except Exception as e:  # noqa: BLE001 — see below; this aggregate must not break
        # A version skew is FATAL on the paths a person asked for — writing a
        # shared entry, searching shared knowledge — because refusing loudly is
        # the whole point of the guard. It must NOT be fatal here.
        #
        # This aggregate is display-only and documented as never breaking its
        # caller, and its callers are the session-start hook and the CLAUDE.md
        # refresh. Letting the guard through would mean a newer store in one
        # project stops every OTHER project from starting a session at all —
        # punishing the wrong people for a skew they did not create, and far
        # beyond what "tell the user to update" asks for.
        #
        # It is still not silent: the notice is rendered in the block, where the
        # agent and the person both see it every session until it is fixed.
        return [], ["", f"⚠ {e}"]

    out: list[str] = []
    if raw:
        out.append("")
        out.append(f"{SHARED_KNOWLEDGE_HEADING} ({len(raw)}):**")
        out.extend(f"- [{kind}] {flatten_for_injection(text, 100)}" for kind, text in raw)

    return out, ([" ", f"⚠ {warning}"] if warning else [])


def build_memory_compact(be: Any, last_n: int = 50) -> str:
    """Aggregate recent task_logs into phases + top words + top files summary.

    Best-effort like the sibling aggregates: a backend error → '' (never crash)."""
    try:
        logs = be.task_log_recent(last_n)
    except Exception:  # noqa: BLE001 — display-only aggregate, non-fatal
        return ""
    if not logs:
        return ""

    phase_counts: Counter[str] = Counter()
    first_word_counts: Counter[str] = Counter()
    file_mentions: Counter[str] = Counter()

    for row in logs:
        phase = (row.get("phase") or "none").strip() or "none"
        phase_counts[phase] += 1

        message = (row.get("message") or "").strip()
        if not message:
            continue

        first = message.split(None, 1)[0].lower().strip(":,.")[:20]
        if first:
            first_word_counts[first] += 1

        for match in _FILE_PATTERN.finditer(message):
            file_mentions[match.group(0)] += 1

    parts = [
        f"## Compacted logs ({len(logs)} entries)",
        "",
        "**Phases:** " + ", ".join(f"{ph}={n}" for ph, n in phase_counts.most_common(5)),
    ]

    top_words = first_word_counts.most_common(3)
    if top_words:
        parts.append("**Top message openers:** " + ", ".join(f"{w}({n})" for w, n in top_words))

    top_files = file_mentions.most_common(5)
    if top_files:
        parts.append("")
        parts.append("**Top files mentioned:**")
        for path, count in top_files:
            parts.append(f"- {path} ({count}×)")

    parts.append("")
    parts.append(
        "_Hint: recurring patterns worth turning into `memory add convention` or `dead_end`._"
    )
    return "\n".join(parts)
