"""Deterministic context header attached to a chunk before indexing.

Contextual retrieval (onyx / Anthropic) fixes a specific failure: a chunk cut
out of a file no longer carries what the file was ABOUT, so a query phrased in
the document's terms cannot reach a passage phrased in its own. The published
technique asks an LLM to write a sentence of context per chunk. This does the
same job from metadata the indexer already has — no model call, so the same
input always yields the same header, byte for byte, and indexing stays
reproducible and offline (a generated summary would make the index depend on a
model version and a network).

What the header adds is only what the chunk has LOST. `file_path` and
`language` are already indexed columns, and a chunk cut at a definition
boundary already contains its own `def foo(...)` line. The gap is elsewhere:

  * a CONTINUATION chunk (part 2..n of a long function, or any chunk from the
    line-based fallback used for languages with no boundary pattern) can start
    mid-body, carrying no definition line at all;
  * no chunk carries the module's own summary — its docstring first line —
    so "what is this file for" is unsearchable from any chunk but the first;
  * path segments are punctuation-joined, so `service_doctor_drift.py` does not
    reliably match a query that says "doctor drift".

The header is stored in its own column and indexed there. It is never part of
the chunk's content, so search results show the source exactly as written.
"""

from __future__ import annotations

import os
import re

# Definition-ish opening lines across the languages the indexer splits on.
# Deliberately loose: this extracts a NAME for search, it does not parse code.
_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+|public\s+|private\s+|protected\s+|pub\s+|async\s+)*"
    r"(?:def|class|function|func|fn|impl|struct|enum|trait|interface|type|module|"
    r"defmodule|defp|object|data\s+class|const|namespace)\s+"
    r"([A-Za-z_][\w]*)"
)
_MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_DOCSTRING_RE = re.compile(r'^\s*(?:"""|\'\'\'|/\*\*?|//!|#!)?\s*(.+?)\s*$')

_MAX_SUMMARY_CHARS = 160


def split_path_words(file_path: str) -> list[str]:
    """Path split into searchable words, order preserved, duplicates dropped.

    `harness/claude/mcp/codebase-rag/rag_store.py` becomes
    `harness claude mcp codebase rag store`. The extension is dropped: `py` as
    a search term matches every Python chunk in the index and so carries no
    information.
    """
    normalized = file_path.replace("\\", "/")
    stem, _ext = os.path.splitext(normalized)
    words: list[str] = []
    seen: set[str] = set()
    for word in re.split(r"[^A-Za-z0-9]+", stem):
        if not word:
            continue
        lowered = word.lower()
        if lowered not in seen:
            seen.add(lowered)
            words.append(lowered)
    return words


def extract_symbol(chunk_content: str) -> str:
    """Name defined on the chunk's first meaningful line, or "".

    Only the opening line is considered. A chunk that begins mid-body has no
    symbol of its own — returning something from deeper inside would attach a
    name the chunk does not actually define.
    """
    for line in chunk_content.split("\n"):
        if not line.strip():
            continue
        heading = _MARKDOWN_HEADING_RE.match(line)
        if heading:
            return heading.group(1).strip()
        match = _SYMBOL_RE.match(line)
        return match.group(1) if match else ""
    return ""


def extract_module_summary(file_content: str) -> str:
    """First prose line of the file — its docstring or leading comment.

    This is the "what is this file about" sentence that every chunk except the
    first one loses. Truncated, because a header is a search aid and not a
    second copy of the file.
    """
    for raw in file_content.split("\n")[:20]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("import ", "from ", "package ", "using ")):
            continue
        if line.startswith(("#!", "// ", "# ", '"""', "'''", "/*", "*", "//!")):
            match = _DOCSTRING_RE.match(line)
            text = (match.group(1) if match else line).strip(" *#/\"'")
            if len(text) >= 8:
                return text[:_MAX_SUMMARY_CHARS]
            continue
        return ""
    return ""


def build_context_prefix(
    file_path: str,
    chunk_content: str,
    *,
    module_summary: str = "",
    enclosing_symbol: str = "",
    chunk_type: str = "code",
) -> str:
    """The header indexed alongside a chunk. Same inputs → same bytes.

    `enclosing_symbol` is what the caller believes this chunk sits inside; it
    is used only when the chunk defines nothing itself, which is exactly the
    continuation case the header exists for.
    """
    parts: list[str] = list(split_path_words(file_path))
    symbol = extract_symbol(chunk_content) or enclosing_symbol
    if symbol:
        parts.append(symbol)
        # Split camelCase / snake_case so `check_claudemd_drift` is also
        # reachable as "claudemd drift".
        for word in re.split(r"[^A-Za-z0-9]+|(?<=[a-z0-9])(?=[A-Z])", symbol):
            if word and word.lower() not in {p.lower() for p in parts}:
                parts.append(word.lower())
    if chunk_type and chunk_type != "code":
        parts.append(chunk_type)
    if module_summary:
        parts.append(module_summary)
    return " ".join(parts)
