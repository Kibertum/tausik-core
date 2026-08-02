"""Memory-aggregation helpers — memory_block and memory_compact.

Extracted from service_knowledge.py to keep that file under the 400-line gate.
These are pure functions over the backend; the mixin methods below delegate here.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


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


def build_compact_memory_tail(be: Any) -> list[str]:
    """One-line-per-item memory recap for CLAUDE.md Current State.

    Used by `tausik update-claudemd` to embed the latest decisions /
    conventions / dead ends inside the dynamic block, so /start no longer
    needs a separate `tausik_memory_block` re-injection call. Empty DB
    (or any backend exception) → return [] and the caller omits the
    subsection entirely.
    """
    try:
        decisions = be.decision_list(5) or []
        conventions = be.memory_list("convention", 5) or []
        deadends = be.memory_list("dead_end", 3) or []
        # `context` = durable environment facts (hosts, machines, access, paths).
        # Surfaced every session so the agent never "forgets" them and asks the
        # user for something already recorded (v15p-memory-first-recall).
        contexts = be.memory_list("context", 5) or []
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return []

    if not decisions and not conventions and not deadends and not contexts:
        return []

    out: list[str] = ["### Memory tail"]
    if contexts:
        out.append(f"Context ({len(contexts)}):")
        for ctx in contexts:
            out.append(f"- #{ctx.get('id')} {flatten_for_injection(ctx.get('title'), 100)}")
    if decisions:
        out.append(f"Decisions ({len(decisions)}):")
        for d in decisions:
            out.append(f"- #{d.get('id')} {flatten_for_injection(d.get('decision'), 120)}")
    if conventions:
        out.append(f"Conventions ({len(conventions)}):")
        for c in conventions:
            out.append(f"- #{c.get('id')} {flatten_for_injection(c.get('title'), 100)}")
    if deadends:
        out.append(f"Dead ends ({len(deadends)}):")
        for de in deadends:
            out.append(f"- #{de.get('id')} {flatten_for_injection(de.get('title'), 100)}")
    return out


def build_memory_block(
    be: Any,
    max_decisions: int = 5,
    max_conventions: int = 10,
    max_deadends: int = 5,
    max_lines: int = 50,
    max_contexts: int = 5,
) -> str:
    """Compact markdown: context + decisions + conventions + recent dead ends.

    Best-effort like build_compact_memory_tail: any backend error → '' (the
    block is display-only; it must never break the caller)."""
    try:
        decisions = be.decision_list(max_decisions)
        conventions = be.memory_list("convention", max_conventions)
        deadends = be.memory_list("dead_end", max_deadends)
        contexts = be.memory_list("context", max_contexts)
    except Exception:  # noqa: BLE001 — display-only aggregate, non-fatal
        return ""

    if not decisions and not conventions and not deadends and not contexts:
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
            lines.append(f"- #{ctx.get('id')} {flatten_for_injection(ctx.get('title'), 80)}")

    if decisions:
        lines.append("")
        lines.append(f"**Recent decisions ({len(decisions)}):**")
        for d in decisions:
            lines.append(f"- #{d.get('id')} {flatten_for_injection(d.get('decision'), 100)}")

    if conventions:
        lines.append("")
        lines.append(f"**Conventions ({len(conventions)}):**")
        for c in conventions:
            lines.append(f"- #{c.get('id')} {flatten_for_injection(c.get('title'), 80)}")

    if deadends:
        lines.append("")
        lines.append(f"**Recent dead ends ({len(deadends)}):**")
        for de in deadends:
            lines.append(f"- #{de.get('id')} {flatten_for_injection(de.get('title'), 80)}")

    if len(lines) > max_lines:
        overflow = len(lines) - max_lines
        lines = lines[:max_lines]
        lines.append(f"_...(truncated, {overflow} more lines)_")

    return "\n".join(lines)


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
