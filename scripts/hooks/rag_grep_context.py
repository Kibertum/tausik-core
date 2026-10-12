#!/usr/bin/env python3
"""PostToolUse hook: after a Grep, hand the agent what the RAG index knows too.

rag-first-by-mechanism-not-text (1.10, decision #391). RAG is the route to code,
and text telling the agent so did nothing: a paired replay measured 0
search_code calls in 62 with every rag-first text delivered. So the index is
consulted FOR the agent: the identifiers of the Grep pattern are searched in
.tausik/rag/rag.db and the top chunks come back as additionalContext, next to
the Grep result.

Read-only on the index. An absent, empty or locked index, a non-Grep tool or a
pattern with no identifier adds nothing. Always exits 0. TAUSIK_SKIP_HOOKS=1 skips.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys

MAX_CHUNKS = 3
MAX_LINES_PER_CHUNK = 6
MAX_CHARS = 1500
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_KEYWORDS = {
    "def",
    "class",
    "return",
    "import",
    "from",
    "self",
    "function",
    "const",
    "let",
    "var",
    "the",
    "and",
    "for",
    "async",
    "await",
}


def identifiers(pattern: str) -> list[str]:
    """Identifier-like words of a regex pattern, regex syntax dropped."""
    cleaned = re.sub(r"\\[a-zA-Z]", " ", pattern or "")
    seen: list[str] = []
    for word in _IDENT.findall(cleaned):
        if word not in seen and word.lower() not in _KEYWORDS:
            seen.append(word)
    return seen[:6]


def rag_context(project_dir: str, pattern: str) -> str | None:
    words = identifiers(pattern)
    db = os.path.join(project_dir, ".tausik", "rag", "rag.db")
    if not words or not os.path.isfile(db):
        return None
    query = " OR ".join(f'"{w}"' for w in words)
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=0.5)
        try:
            rows = conn.execute(
                "SELECT r.file_path, r.start_line, r.end_line, r.content "
                "FROM fts_code fc JOIN rag_chunks r ON r.id = fc.rowid "
                "WHERE fts_code MATCH ? ORDER BY rank LIMIT ?",
                (query, MAX_CHUNKS),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if not rows:
        return None
    parts = [f"**[TAUSIK RAG]** Index hits for {', '.join(words)}:"]
    for path, start, end, content in rows:
        body = "\n".join((content or "").splitlines()[:MAX_LINES_PER_CHUNK])
        parts.append(f"- {path}:{start}-{end}\n{body}")
    text = "\n".join(parts)
    return text[:MAX_CHARS]


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0
    try:
        payload = json.load(sys.stdin)
    except (ValueError, EOFError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Grep":
        return 0
    tool_input = payload.get("tool_input") or {}
    pattern = tool_input.get("pattern") if isinstance(tool_input, dict) else None
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    context = rag_context(project_dir, pattern if isinstance(pattern, str) else "")
    if context:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": context,
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
