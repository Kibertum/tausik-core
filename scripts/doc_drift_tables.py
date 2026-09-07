"""Numeric cells of markdown table columns, checked against computed constants.

Third module of the doc-drift split (``doc_drift_common`` holds the shared
regex tables and text helpers, ``doc_drift_fixes`` the auto-fixer, this one the
column scan). It carries its OWN subject registry rather than adding it to
``doc_drift_common``: that module sits within a few dozen lines of the filesize
cap, and the registry belongs beside its only consumer for the same reason the
fixer does. Imports go one way only — this module reads ``doc_drift_common``
and nothing in the trio reads this one except ``doc_drift_scanners``, which
re-exports the entry point so existing imports keep resolving.
"""

from __future__ import annotations

import re
from pathlib import Path

from doc_drift_common import (
    CODE_COUNT_EXTRA_TARGETS,
    CROSS_FILE_SCAN_TARGETS,
    MCP_COUNT_EXTRA_TARGETS,
    _strip_dynamic_block,
    _strip_fenced_blocks,
)

__all__ = ["TABLE_SUBJECT_EXEMPT", "scan_table_count_columns", "table_subject_keys"]


# Markdown table columns whose numeric cells assert a count THE REPOSITORY
# ALREADY COMPUTES. Each entry is (header regex, constants key, component keys,
# label); the components are checked as well when the cell spells out a split,
# as in "152 (145+7)".
#
# THE PREDECESSOR GUARDED ONE SUBJECT IN ONE SPELLING — `^MCP tools$`, anchored
# on the whole header cell. Measured on this tree in session #224 while
# `gen_doc_constants --check` was GREEN: AGENTS.md carried three cells reading
# `**100** (93+7)` under the header "Main `tausik_*` tools (two servers)" — the
# same column as the row above them, which reads the correct `152 (145+7)` —
# and both READMEs carried `21` under `Hooks` / `Хуки` against hooks_count=22,
# ten lines below prose saying 22 that WAS checked. Neither header matched the
# anchor, so no column was located, so the scan passed. A scanner that cannot
# find its column reports SUCCESS, and that silence is indistinguishable from
# coverage; ending that particular silence is why this table exists.
#
# Headers are matched by KEYWORD against a NORMALISED cell (runs of punctuation
# collapsed to spaces, so "Main `tausik_*` tools (two servers)" reads as "Main
# tausik tools two servers"), never by full-cell equality. The price of the
# looser match is landing on somebody else's column, so every keyword below is
# a noun that NAMES the count itself and never an adjective standing near one.
#
# WHICH CONSTANTS ARE ABSENT FROM THIS TABLE IS ITSELF CHECKED — see
# TABLE_SUBJECT_EXEMPT and the test that pairs it against constants.json, so a
# new computed count cannot arrive without someone stating in writing where the
# documentation binds to it, or why it does not.
_TABLE_COUNT_SUBJECTS: tuple[tuple[re.Pattern[str], str, tuple[str, ...], str], ...] = (
    (
        re.compile(r"\b(?:MCP\s+(?:tools?|инструмент\w*)|tausik\s+tools?)\b", re.IGNORECASE),
        "mcp_main_tools",
        ("mcp_project_tools", "mcp_brain_tools"),
        "MCP tool-count",
    ),
    (
        re.compile(r"^(?:hooks?|хук(?:и|ов|а)?)$", re.IGNORECASE),
        "hooks_count",
        (),
        "hook-count",
    ),
    (
        re.compile(r"^(?:skills?|скилл\w*)$", re.IGNORECASE),
        "skills_core_count",
        (),
        "core-skill-count",
    ),
    (
        re.compile(r"^(?:stacks?|стек(?:и|ов|а)?)$", re.IGNORECASE),
        "stacks_count",
        (),
        "stack-count",
    ),
    (
        re.compile(r"^(?:roles?|рол(?:и|ей|ь))$", re.IGNORECASE),
        "roles_count",
        (),
        "role-count",
    ),
    (
        re.compile(r"^(?:review\s+agents?|агент\w*\s+ревью)$", re.IGNORECASE),
        "review_agents_count",
        (),
        "review-agent-count",
    ),
)

# Integer constants that deliberately have NO table subject, each with the
# reason. Paired against constants.json by a test: an int constant that is
# neither a subject above, nor a declared component of one, nor listed here,
# fails — because "nothing checks this number" must be a sentence somebody
# wrote, not a gap somebody has to notice.
TABLE_SUBJECT_EXEMPT: dict[str, str] = {
    "schema_version": (
        "the constants file's own format version — an internal handshake between "
        "generator and reader, never quoted as a product count"
    ),
    "test_count": (
        "a LOWER BOUND by decision #182, and a bare cell cannot say 'at least'; "
        "the decorated-number exclusion in scan_table_count_columns says the rest"
    ),
    "mcp_rag_tools": (
        "the optional codebase-rag server is quoted in prose, not in a counted "
        "column — bound by the codebase-rag entries in _MCP_COUNT_PATTERNS"
    ),
    "mcp_tools_with_optional_rag": (
        "same prose sentence as mcp_rag_tools, and bound by the same pair of "
        "patterns rather than by a column"
    ),
    "skills_official_count": (
        "the opt-in catalogue is quoted in prose beside the core count, never as "
        "its own column — bound by the official-skills entries in "
        "_CODE_COUNT_PATTERNS"
    ),
}

# A counted cell: an optionally bolded integer, and nothing glued to it. What
# follows must be empty or begin with a space, which is what separates "21
# (full)" and "13 core + opt-in" (counts wearing a gloss) from "128+", "~121"
# and "1.5" (decorations that change what the number claims).
_TABLE_COUNT_CELL_RE = re.compile(r"^\*{0,2}(\d+)\*{0,2}(?P<rest>.*)$")

# The split a total sometimes spells out: "152 (145+7)". Read only when the
# subject declares which constants the components are.
_TABLE_COUNT_SPLIT_RE = re.compile(r"^\s*\((\d+)\s*\+\s*(\d+)\)")

# Punctuation, backticks and emphasis carry no meaning in a header cell, and
# they are exactly what kept "Main `tausik_*` tools (two servers)" from being
# recognised as a tool-count column.
_HEADER_NOISE_RE = re.compile(r"[^0-9A-Za-zА-Яа-яЁё]+")


def _normalise_header(cell: str) -> str:
    """A header cell reduced to its words, so decoration cannot hide the noun."""
    return _HEADER_NOISE_RE.sub(" ", cell).strip()


def _match_subject(cell: str) -> tuple[str, tuple[str, ...], str] | None:
    """The (key, components, label) this header names, or None."""
    normalised = _normalise_header(cell)
    if not normalised:
        return None
    for pattern, key, parts, label in _TABLE_COUNT_SUBJECTS:
        if pattern.search(normalised):
            return key, parts, label
    return None


def table_subject_keys() -> frozenset[str]:
    """Every constants key this scanner reads — subjects and their components."""
    keys: set[str] = set()
    for _pattern, key, parts, _label in _TABLE_COUNT_SUBJECTS:
        keys.add(key)
        keys.update(parts)
    return frozenset(keys)


def _is_delimiter_row(cells: list[str]) -> bool:
    return bool(cells) and all(set(c) <= set("-: ") for c in cells if c)


def scan_table_count_columns(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Return drift messages for numeric cells of counted table columns.

    Every :data:`doc_drift_common._MCP_COUNT_PATTERNS` entry needs a WORD beside
    the number, so a bare table cell (``| 128 |``) matched none of them. This
    scan reads the column instead: the HEADER names the subject, so inserting a
    column ahead of it cannot silently move the check onto someone else's
    numbers, and a table may carry several counted columns at once (the READMEs'
    IDE table counts MCP tools, skills and hooks side by side).

    The header row is the first row of each table, per markdown, rather than
    "whichever row happens to match first": a data row that reads like a header
    would otherwise take the check with it.

    A DECORATED NUMBER ("128+", "~128") IS SKIPPED, and that is a declared
    exclusion rather than an oversight (external review #40). Checking it would
    require a convention for what the decoration CLAIMS, and these columns have
    none: `test_count` has one — decision #182 makes it a lower bound, so "N+"
    is honest while an overclaim reddens — but nothing says whether a "128+"
    here means "at least" or "about". Inventing that rule inside a scanner would
    be policy written where nobody looks for it. A PARENTHETICAL GLOSS is NOT a
    decoration and IS read: "21 (full)" and "13 core + opt-in" claim 21 and 13
    exactly, and both were carrying stale numbers when this scan was written.

    NAMED LIMITATION — WHAT THIS STILL CANNOT SEE. A count written as prose
    inside a cell that is not itself a number stays invisible: AGENTS.md's
    "Skills reference (12 core + brain conditional, 25+ official opt-in)" sat in
    a link label, two counts wrong, and no column scan can reach it. Those are
    the business of the prose patterns, and the split is deliberate — a scanner
    that tried to read every number in every cell would report the SENAR
    matrix's rule numbers as tool counts. Said here rather than left to be
    discovered, because a scanner trusted past its reach is the defect this
    module was written to end.
    """
    messages: list[str] = []
    for rel in (*CROSS_FILE_SCAN_TARGETS, *MCP_COUNT_EXTRA_TARGETS, *CODE_COUNT_EXTRA_TARGETS):
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_dynamic_block(_strip_fenced_blocks(path.read_text(encoding="utf-8")))
        columns: dict[int, tuple[str, tuple[str, ...], str]] = {}
        in_table = False
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not line.lstrip().startswith("|"):
                in_table = False
                columns = {}
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not in_table:
                in_table = True
                columns = {}
                for i, cell in enumerate(cells):
                    subject = _match_subject(cell)
                    if subject is not None:
                        columns[i] = subject
                continue
            if not columns or _is_delimiter_row(cells):
                continue
            for i, (key, parts, label) in columns.items():
                if i >= len(cells):
                    continue
                messages += _check_cell(rel, line_no, cells[i], key, parts, label, payload)
    return messages


def _check_cell(
    rel: str,
    line_no: int,
    cell: str,
    key: str,
    parts: tuple[str, ...],
    label: str,
    payload: dict[str, object],
) -> list[str]:
    """Drift messages for one cell: the total, then the split it may spell out."""
    expected = payload.get(key)
    if not isinstance(expected, int):
        return []
    match = _TABLE_COUNT_CELL_RE.match(cell)
    if match is None:
        return []
    rest = match.group("rest")
    if rest and not rest.startswith(" "):
        return []
    messages: list[str] = []
    found = int(match.group(1))
    if found != expected:
        messages.append(
            f"{rel}:{line_no}: {label} cell '{cell}' does not match constants.json {key}={expected}"
        )
    split = _TABLE_COUNT_SPLIT_RE.match(rest)
    if split is not None and len(parts) == 2:
        for got, part_key in zip((split.group(1), split.group(2)), parts, strict=True):
            part_expected = payload.get(part_key)
            if isinstance(part_expected, int) and int(got) != part_expected:
                messages.append(
                    f"{rel}:{line_no}: {label} split '{split.group(0).strip()}' in cell "
                    f"'{cell}' does not match constants.json {part_key}={part_expected}"
                )
    return messages
