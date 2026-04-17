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


def build_memory_block(
    be: Any,
    max_decisions: int = 5,
    max_conventions: int = 10,
    max_deadends: int = 5,
    max_lines: int = 50,
) -> str:
    """Compact markdown: architectural decisions + conventions + recent dead ends."""
    decisions = be.decision_list(max_decisions)
    conventions = be.memory_list("convention", max_conventions)
    deadends = be.memory_list("dead_end", max_deadends)

    if not decisions and not conventions and not deadends:
        return ""

    lines: list[str] = ["## TAUSIK Memory Block"]

    if decisions:
        lines.append("")
        lines.append(f"**Recent decisions ({len(decisions)}):**")
        for d in decisions:
            text = (d.get("decision") or "")[:100]
            lines.append(f"- #{d['id']} {text}")

    if conventions:
        lines.append("")
        lines.append(f"**Conventions ({len(conventions)}):**")
        for c in conventions:
            title = (c.get("title") or "")[:80]
            lines.append(f"- #{c['id']} {title}")

    if deadends:
        lines.append("")
        lines.append(f"**Recent dead ends ({len(deadends)}):**")
        for de in deadends:
            title = (de.get("title") or "")[:80]
            lines.append(f"- #{de['id']} {title}")

    if len(lines) > max_lines:
        overflow = len(lines) - max_lines
        lines = lines[:max_lines]
        lines.append(f"_...(truncated, {overflow} more lines)_")

    return "\n".join(lines)


def build_memory_compact(be: Any, last_n: int = 50) -> str:
    """Aggregate recent task_logs into phases + top words + top files summary."""
    logs = be.task_log_recent(last_n)
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
        "**Phases:** "
        + ", ".join(f"{ph}={n}" for ph, n in phase_counts.most_common(5)),
    ]

    top_words = first_word_counts.most_common(3)
    if top_words:
        parts.append(
            "**Top message openers:** " + ", ".join(f"{w}({n})" for w, n in top_words)
        )

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
