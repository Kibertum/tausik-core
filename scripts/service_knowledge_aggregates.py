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
            title = (ctx.get("title") or "").strip().replace("\n", " ")
            out.append(f"- #{ctx.get('id')} {title[:100]}")
    if decisions:
        out.append(f"Decisions ({len(decisions)}):")
        for d in decisions:
            text = (d.get("decision") or "").strip().replace("\n", " ")
            out.append(f"- #{d.get('id')} {text[:120]}")
    if conventions:
        out.append(f"Conventions ({len(conventions)}):")
        for c in conventions:
            title = (c.get("title") or "").strip().replace("\n", " ")
            out.append(f"- #{c.get('id')} {title[:100]}")
    if deadends:
        out.append(f"Dead ends ({len(deadends)}):")
        for de in deadends:
            title = (de.get("title") or "").strip().replace("\n", " ")
            out.append(f"- #{de.get('id')} {title[:100]}")
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
            title = (ctx.get("title") or "")[:80]
            lines.append(f"- #{ctx.get('id')} {title}")

    if decisions:
        lines.append("")
        lines.append(f"**Recent decisions ({len(decisions)}):**")
        for d in decisions:
            text = (d.get("decision") or "")[:100]
            lines.append(f"- #{d.get('id')} {text}")

    if conventions:
        lines.append("")
        lines.append(f"**Conventions ({len(conventions)}):**")
        for c in conventions:
            title = (c.get("title") or "")[:80]
            lines.append(f"- #{c.get('id')} {title}")

    if deadends:
        lines.append("")
        lines.append(f"**Recent dead ends ({len(deadends)}):**")
        for de in deadends:
            title = (de.get("title") or "")[:80]
            lines.append(f"- #{de.get('id')} {title}")

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
