"""Numeric cells of markdown table columns, checked against computed constants.

Fourth module of the doc-drift split: ``doc_drift_common`` holds the shared
regex tables and text helpers, ``doc_drift_scanners`` the scans, ``doc_drift_fixes``
the auto-fixer, and this one the column scan. It said "third of three" while the
split had already become four — the same self-description drift these modules
exist to catch, in the module that catches it. It carries its OWN subject registry rather than adding it to
``doc_drift_common``: the two together are well past the 500-line filesize cap
(decision #190), so merging them would breach it — and the registry belongs
beside its only consumer for the same reason the fixer does. No line count is
quoted here on purpose: an earlier draft of this sentence said
``doc_drift_common`` sat "within a few dozen lines of the cap" when it had 99 to
spare, and a rationale defended with an unmeasured number is the same defect
this module exists to catch, written about itself. Imports go one way only —
this module reads
``doc_drift_common``, and nothing in the quartet reads this one except
``doc_drift_scanners``, which re-exports the entry point so existing imports
keep resolving.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from doc_drift_common import (
    CODE_COUNT_EXTRA_TARGETS,
    CROSS_FILE_SCAN_TARGETS,
    MCP_COUNT_EXTRA_TARGETS,
    _strip_dynamic_block,
    _strip_fenced_blocks,
)

__all__ = [
    "STATED_ONLY_WHERE_NOTHING_READS",
    "TABLE_SUBJECT_EXEMPT",
    "locate_table_columns",
    "scan_table_count_columns",
    "table_subject_keys",
]


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
# a PLURAL noun that names the count itself.
#
# WHICH CONSTANTS ARE ABSENT FROM THIS TABLE IS ITSELF CHECKED — see
# TABLE_SUBJECT_EXEMPT and the test that pairs it against constants.json, so a
# new computed count cannot arrive without someone stating in writing where the
# documentation binds to it, or why it does not.
#
# PLURAL ONLY, AND THAT IS THE WHOLE DIFFERENCE BETWEEN A COUNT AND A LIST. A
# column headed `Hook` holds hook NAMES — `docs/{en,ru}/hooks.md` has fourteen
# such tables — while a column headed `Hooks` holds how many there are. The
# first cut accepted both, and bound all fourteen listing columns to
# `hooks_count`; nothing broke only because hook filenames do not begin with a
# digit, which is luck standing in for a rule.
#
# EVERY SUBJECT HERE MUST ACTUALLY FIND A COLUMN, and a test enforces it against
# the live tree. The first cut carried six subjects of which three — stacks,
# roles, review agents — matched no header anywhere in the fourteen scanned
# files, and the meta-test scored them "bound" because it asked whether the KEY
# was listed, never whether the pattern reached a document. Three of six
# subjects were unfalsifiable: a mutation making their regexes unmatchable left
# the suite green. They are counted in prose, not in a column, so they now sit
# in TABLE_SUBJECT_EXEMPT beside the other prose-bound constants, where their
# binding is asserted rather than assumed.
_TABLE_COUNT_SUBJECTS: tuple[tuple[re.Pattern[str], str, tuple[str, ...], str], ...] = (
    (
        re.compile(r"\b(?:MCP\s+(?:tools|инструмент(?:ы|ов|а))|tausik\s+tools)\b", re.IGNORECASE),
        "mcp_main_tools",
        ("mcp_project_tools",),
        "MCP tool-count",
    ),
    (
        re.compile(r"\b(?:hooks|хук(?:и|ов))\b", re.IGNORECASE),
        "hooks_count",
        (),
        "hook-count",
    ),
    (
        re.compile(r"\b(?:skills|скилл(?:ы|ов))\b", re.IGNORECASE),
        "skills_core_count",
        (),
        "core-skill-count",
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
    "stacks_count": (
        "no column, and its prose patterns reach no document either — see "
        "STATED_ONLY_WHERE_NOTHING_READS"
    ),
    "roles_count": (
        "no column, and no prose either: every statement of it lives inside a "
        "fenced repository tree — see STATED_ONLY_WHERE_NOTHING_READS"
    ),
    "review_agents_count": (
        "no column and no statement at all in the scanned documents — see "
        "STATED_ONLY_WHERE_NOTHING_READS"
    ),
}

# Constants that NOTHING checks, and the reason each one is like that. The
# separate map exists because a test can verify membership but cannot read a
# sentence: `TABLE_SUBJECT_EXEMPT` says "bound elsewhere" and its test proves
# the binding, so a key whose binding does not exist must say so in a place the
# test can tell apart. Measured in session #224 — three exemptions claimed to be
# "bound by the entries in _CODE_COUNT_PATTERNS" while those entries matched no
# document in the tree, which is an unchecked number wearing a reason.
STATED_ONLY_WHERE_NOTHING_READS: dict[str, str] = {
    "stacks_count": (
        "the plural patterns in _CODE_COUNT_PATTERNS reach no document: the only "
        "unfenced statements are '25 stack-aware verify suites' in the READMEs and "
        "'25 stack guides' inside AGENTS.md's fenced tree, and the repository has "
        "already RULED that neither is a statement of this count — see "
        "test_scan_code_counts_ignores_singular_stack_phrases, which pins that "
        "'stack-aware checks' and 'stack guides' count gates and docs rather than "
        "stacks. Binding them would make a stack without a verify suite read as "
        "drift. Reversing that ruling is a decision, not a patch, so the count "
        "stays unchecked and says so here"
    ),
    "roles_count": (
        "stated as '6 roles' / '6 ролей' inside the fenced repository trees of "
        "AGENTS.md and both architecture.md files. Fences are stripped before "
        "every scan on purpose — they hold illustrations, not claims — so this "
        "count is reconciled by hand, never automatically. Already the standing "
        "convention for this file: see the roles comment in _CODE_COUNT_PATTERNS"
    ),
    "review_agents_count": (
        "no scanned document states it in any form. It is computed because "
        "`harness/skills/review/agents/` is the honest source if a document ever "
        "quotes it; until one does, this constant is written and read by nobody, "
        "and saying so beats leaving a reader to discover it"
    ),
}

# A counted cell: an optionally bolded integer, and nothing glued to it. What
# follows must be empty or begin with a space, which is what separates "21
# (full)" and "13 core + opt-in" (counts wearing a gloss) from "128+", "~121"
# and "1.5" (decorations that change what the number claims).
_TABLE_COUNT_CELL_RE = re.compile(r"^\*{0,2}(\d+)\*{0,2}(?P<rest>.*)$")

# The split a total sometimes spells out: "152 (145+7)". Checked against the
# subject's declared components; a split with more parts than the subject
# declares is a sum the repository no longer computes.
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


def locate_table_columns(repo_root: Path) -> dict[str, list[str]]:
    """Where each subject actually FINDS a column, as ``{key: [rel:line, ...]}``.

    Separated from the drift scan so the registry can be checked against reality
    instead of against itself. `scan_table_count_columns` returning `[]` says
    "no stale cell", and a subject whose header matches nothing anywhere returns
    exactly the same `[]` — which is how three of the first six subjects lived
    as unfalsifiable machinery until a mutation exposed them. Every subject
    reporting at least one location is the property that separates the two, and
    it is asserted against the live tree rather than against a fixture, because
    a fixture would prove only that the registry can match a document somebody
    wrote for it.
    """
    found: dict[str, list[str]] = {}
    for rel, line_no, _cells, columns in _walk_table_rows(repo_root, header_rows_only=True):
        for _index, (key, _parts, _label) in columns.items():
            found.setdefault(key, []).append(f"{rel}:{line_no}")
    return found


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

    NAMED LIMITATIONS — WHAT THIS STILL CANNOT SEE.

    * A count written as PROSE inside a cell that is not itself a number:
      AGENTS.md's "Skills reference (12 core + brain conditional, 25+ official
      opt-in)" carried two wrong counts inside a link label. Those belong to the
      prose patterns, and the split is deliberate — a scanner that read every
      number in every cell would report the SENAR matrix's rule numbers as tool
      counts.
    * A SINGULAR header. `Hook` names a column of hook names, `Hooks` a column
      of how many, and only the plural is a subject here. A genuinely singular
      count column ("Hook count: 22") would be missed; no document writes one,
      and accepting the singular bound fourteen listing tables in
      `docs/{en,ru}/hooks.md` to `hooks_count` for no gain.
    * A number wearing a thousands separator, a link, or inline backticks:
      `1,234`, `[152](x.md)` and `` `152` `` all fail the leading-digit test.

    THE OVERLAP WITH THE PROSE PATTERNS IS DELIBERATE, NOT A PARTITION. A cell
    like `| 21 hooks |` satisfies both this scan and `scan_code_counts`, and the
    same drift is then reported twice in different words. They agree today and
    nothing enforces that they keep agreeing, so whoever tunes one regex should
    look at the other — the two are not divided by responsibility, only by how
    they find the number.

    Said here rather than left to be discovered, because a scanner trusted past
    its reach is the defect this module was written to end.
    """
    messages: list[str] = []
    for rel, line_no, cells, columns in _walk_table_rows(repo_root):
        for i, (key, parts, label) in columns.items():
            if i >= len(cells):
                continue
            messages += _check_cell(rel, line_no, cells[i], key, parts, label, payload)
    return messages


def _walk_table_rows(
    repo_root: Path, *, header_rows_only: bool = False
) -> Iterator[tuple[str, int, list[str], dict[int, tuple[str, tuple[str, ...], str]]]]:
    """Yield ``(rel, line_no, cells, columns)`` for rows under a counted column.

    ONE parser feeds both the drift scan and :func:`locate_table_columns`. Two
    walks would be two opinions about where the columns are, and the check that
    a subject really finds one would then be checking a second implementation
    rather than the shipped one — which is the failure mode this whole module is
    about, moved into the test harness.

    With ``header_rows_only`` the yield happens once per table whose header
    located at least one subject, carrying that header's line.
    """
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
                if header_rows_only and columns:
                    yield rel, line_no, cells, columns
                continue
            if header_rows_only or not columns or _is_delimiter_row(cells):
                continue
            yield rel, line_no, cells, columns


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
    if split is not None:
        groups = (split.group(1), split.group(2))
        if len(parts) != len(groups):
            # "(146+7)" after the brain server left: the doc spells out a sum
            # the repository no longer computes. That is drift even when the
            # total happens to be right.
            messages.append(
                f"{rel}:{line_no}: {label} split '{split.group(0).strip()}' in cell "
                f"'{cell}' names {len(groups)} components but the subject has "
                f"{len(parts)} ({', '.join(parts)})"
            )
        else:
            for got, part_key in zip(groups, parts, strict=True):
                part_expected = payload.get(part_key)
                if isinstance(part_expected, int) and int(got) != part_expected:
                    messages.append(
                        f"{rel}:{line_no}: {label} split '{split.group(0).strip()}' in cell "
                        f"'{cell}' does not match constants.json {part_key}={part_expected}"
                    )
    return messages
