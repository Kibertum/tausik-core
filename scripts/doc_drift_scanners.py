"""Cross-file drift scanners for `gen_doc_constants`.

Extracted from gen_doc_constants.py for filesize compliance
(v15p-doc-drift-gate). Each `scan_*` function walks its target list, strips
fenced code blocks, and returns a list of human-readable drift messages (empty
when clean). gen_doc_constants re-exports these names, so existing imports keep
working unchanged.

The regex table + line-preserving text helpers live in :mod:`doc_drift_common`;
the auto-fixer (``write_cross_file_fixes``) lives in :mod:`doc_drift_fixes` and
is re-exported here so `from doc_drift_scanners import write_cross_file_fixes`
keeps resolving. The four-module split keeps each file under the 500-line cap (decision #190)
with no duplication and no circular import (scanners→common, scanners→fixes,
scanners→tables, fixes→common, tables→common; neither fixes nor tables imports
scanners).

Covered drift classes:
  - version refs (`vX.Y` / `vX.Y.Z`) vs `tausik_version`
  - MCP tool counts (`**N tools**`, `N project tools`, stale `brain = N` sums)
  - test counts (badge URL/label, `pytest suite (N tests)`, `**N tests**`)
  - repo-state counts (stacks / hooks / review agents / roles / skills)
  - counted table columns (delegated to :mod:`doc_drift_tables`)
"""

from __future__ import annotations

from pathlib import Path

from doc_drift_common import (
    _CLOSED_LIST_COUNT_RE,
    _CLOSED_LIST_ENUM_RE,
    _CODE_COUNT_PATTERNS,
    _MCP_COUNT_PATTERNS,
    _PY_VERSION_RE,
    _TEST_COUNT_PATTERNS,
    _VERSION_RE,
    CLOSED_LIST_COUNT_LOOKBEHIND,
    CLOSED_LIST_MIN_OVERLAP,
    CODE_COUNT_EXTRA_TARGETS,
    CROSS_FILE_SCAN_TARGETS,
    MCP_COUNT_EXTRA_TARGETS,
    PY_VERSION_SCAN_TARGETS,
    VERSION_SCAN_TARGETS,
    _is_foreign_version,
    _strip_dynamic_block,
    _strip_fenced_blocks,
    _version_matches,
)

# Re-exported so `from doc_drift_scanners import write_cross_file_fixes` keeps
# working (gen_doc_constants relies on it). Safe from a cycle: doc_drift_fixes
# imports only doc_drift_common, never this module.
from doc_drift_fixes import write_cross_file_fixes

# Re-exported because gen_doc_constants and repo_coherence import it from here;
# the registry itself and its exemption maps are read only by their own tests,
# which import doc_drift_tables directly rather than through this module.
from doc_drift_tables import scan_table_count_columns

__all__ = [
    "CROSS_FILE_SCAN_TARGETS",
    "scan_version_refs",
    "scan_py_version_constants",
    "scan_mcp_tool_counts",
    "scan_table_count_columns",
    "scan_closed_list_enums",
    "scan_test_counts",
    "scan_code_counts",
    "write_cross_file_fixes",
]


def scan_version_refs(repo_root: Path, expected_version: str) -> list[str]:
    """Return drift messages for cross-file version refs.

    Walks :data:`VERSION_SCAN_TARGETS`, strips fenced code blocks, and
    flags every ``vX.Y`` / ``vX.Y.Z`` occurrence whose major.minor (and
    patch, if present) does not match ``expected_version``. Refs preceded
    by a foreign-version prefix (SENAR / Python / OWASP) are skipped —
    those products version independently.

    Only docs where a version ref means "the current release" are scanned.
    Docs that record *when* a feature landed are excluded, or the gate would
    demand that history be rewritten at every bump.
    """
    messages: list[str] = []
    for rel in VERSION_SCAN_TARGETS:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_fenced_blocks(path.read_text(encoding="utf-8"))
        # The generated DYNAMIC block (memory tail, decision titles) is not an
        # authored version claim wherever it appears: CLAUDE.md AND its sibling
        # AGENTS.md carry the same block. Keyed on the markers, not the file
        # name — a filename key let a decision titled "... corpus v1.1" in
        # AGENTS.md read as a TAUSIK version (session #250). A file without
        # the markers is left untouched by the substitution.
        text = _strip_dynamic_block(text)
        for m in _VERSION_RE.finditer(text):
            if _is_foreign_version(text, m.start()):
                continue
            major = int(m.group(1))
            minor = int(m.group(2))
            patch = int(m.group(3)) if m.group(3) else None
            if _version_matches(major, minor, patch, expected_version):
                continue
            line_no = text[: m.start()].count("\n") + 1
            messages.append(
                f"{rel}:{line_no}: version ref '{m.group(0)}' "
                f"(major.minor={major}.{minor}) does not match "
                f"constants.json tausik_version={expected_version!r}"
            )
    return messages


def scan_py_version_constants(repo_root: Path, expected_version: str) -> list[str]:
    """Return drift messages for hardcoded ``__version__`` literals in .py source.

    pyproject's ``project.version`` is the single source of truth, but a few
    runtime modules duplicate it as a ``__version__ = "X.Y.Z"`` literal
    (consumed by the CLI 'Current State' line and the MCP version handler).
    Those literals are invisible to the markdown cross-file scanners and have
    drifted before, so flag any in :data:`PY_VERSION_SCAN_TARGETS` whose value
    no longer matches ``expected_version``.
    """
    messages: list[str] = []
    for rel in PY_VERSION_SCAN_TARGETS:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for m in _PY_VERSION_RE.finditer(text):
            found = m.group(1)
            if found == expected_version:
                continue
            line_no = text[: m.start()].count("\n") + 1
            messages.append(
                f"{rel}:{line_no}: __version__ '{found}' does not match "
                f"pyproject version {expected_version!r} — bump it (or "
                f"single-source from pyproject)"
            )
    return messages


def scan_mcp_tool_counts(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Return drift messages for cross-file MCP tool-count refs.

    Walks :data:`CROSS_FILE_SCAN_TARGETS`, strips fenced code blocks, and flags
    every ``**N tools**`` / ``N project tools`` / ``brain = N tools`` whose
    captured int does not match the corresponding constants.json key.

    Patterns are deliberately specific-context (require "project"/
    backtick-wrapped server name nearby) to avoid noise on generic phrases like
    "200 tool calls" or "Should have 26+ tools".

    Scans CROSS_FILE_SCAN_TARGETS plus MCP_COUNT_EXTRA_TARGETS — the latter are
    count-bearing docs that carry historical version refs, so only the
    MCP-count scanner (not the version scanner) runs over them.
    """
    messages: list[str] = []
    for rel in (*CROSS_FILE_SCAN_TARGETS, *MCP_COUNT_EXTRA_TARGETS):
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_fenced_blocks(path.read_text(encoding="utf-8"))

        for pattern, key, label in _MCP_COUNT_PATTERNS:
            expected = payload.get(key)
            if not isinstance(expected, int):
                continue
            for m in pattern.finditer(text):
                found = int(m.group(1))
                if found == expected:
                    continue
                line_no = text[: m.start()].count("\n") + 1
                messages.append(
                    f"{rel}:{line_no}: MCP {label} drift '{m.group(0)}' "
                    f"(found={found}) does not match constants.json {key}={expected}"
                )

    return messages


def scan_closed_list_enums(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Return drift messages for closed lists the docs spell out.

    The docs quote the standard's closed lists in full — SPEC types, ADAPT
    backward-finding categories, ADAPT lifecycle statuses — and the guard that
    forbids a second literal copy walks ``scripts/``, ``harness/`` and
    ``tests/`` only, so documentation was outside every closed-list control.
    Measured: ``docs/{en,ru}/mcp.md`` still said "closed list of 9
    (ARCH/…/OPS)" after migration v49 widened SPEC types to eleven.

    THE SUBJECT IS DERIVED. An enumeration is matched to the closed list it
    OVERLAPS most (:data:`CLOSED_LIST_MIN_OVERLAP` shared values at least), not
    to a phrase near it: the enumeration this exists to catch is one whose
    content is wrong, so it can only be recognised by partial match. The count
    written immediately before it, if any, is judged as part of the same claim.
    """
    lists = payload.get("closed_lists")
    if not isinstance(lists, dict) or not lists:
        return []
    known = [
        (name, str(spec.get("label", name)), [str(v) for v in spec.get("values", [])])
        for name, spec in lists.items()
        if isinstance(spec, dict) and spec.get("values")
    ]
    messages: list[str] = []
    for rel in (*CROSS_FILE_SCAN_TARGETS, *MCP_COUNT_EXTRA_TARGETS):
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_fenced_blocks(path.read_text(encoding="utf-8"))
        for m in _CLOSED_LIST_ENUM_RE.finditer(text):
            found = [tok for tok in m.group(1).split("/") if tok]
            name, label, values, overlap = _best_closed_list(found, known)
            if overlap < CLOSED_LIST_MIN_OVERLAP:
                continue  # not a quotation of a list we know
            line_no = text[: m.start()].count("\n") + 1
            # Compared case-insensitively for the same reason the subject is
            # matched that way: a doc spelling the list in another case quotes
            # the same list. Reported in the DOC's own spelling, so the message
            # points at what the reader will find on the line.
            found_lower = {v.lower() for v in found}
            values_lower = {v.lower() for v in values}
            missing = [v for v in values if v.lower() not in found_lower]
            extra = [v for v in found if v.lower() not in values_lower]
            if missing or extra:
                messages.append(
                    f"{rel}:{line_no}: {label} enumerated as '{m.group(1)}' — "
                    f"missing {missing or 'nothing'}, unknown {extra or 'nothing'} "
                    f"vs constants.json closed_lists.{name} ({len(values)} values)"
                )
            before = text[max(0, m.start() - CLOSED_LIST_COUNT_LOOKBEHIND) : m.start()]
            count_m = _CLOSED_LIST_COUNT_RE.search(before)
            if count_m and int(count_m.group(1)) != len(values):
                messages.append(
                    f"{rel}:{line_no}: {label} written as a closed list of "
                    f"{count_m.group(1)} — constants.json closed_lists.{name} "
                    f"holds {len(values)}"
                )
    return messages


def _best_closed_list(
    found: list[str], known: list[tuple[str, str, list[str]]]
) -> tuple[str, str, list[str], int]:
    """The known closed list sharing most values with *found*, and that count."""
    # CASE-INSENSITIVELY. A doc that spells the list in another case is quoting
    # the same list, and a case-sensitive intersection scored it zero — below
    # the floor, so the enumeration was skipped entirely and its content went
    # unchecked (external review #40, reproduced on an all-lowercase quotation
    # of every SPEC type). The message still shows the doc's own spelling.
    lowered = {v.lower() for v in found}
    best: tuple[str, str, list[str], int] = ("", "", [], 0)
    for name, label, values in known:
        overlap = len(lowered & {v.lower() for v in values})
        if overlap > best[3]:
            best = (name, label, values, overlap)
    return best


def scan_test_counts(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Return drift messages for cross-file test-count refs.

    Walks :data:`CROSS_FILE_SCAN_TARGETS`, strips fenced code blocks, and
    flags every match of :data:`_TEST_COUNT_PATTERNS` whose captured int does
    not match ``constants.json["test_count"]``. Patterns are narrow
    (badge URL, ``pytest suite (N tests)``, ``**N tests**``, badge label) to
    avoid noise on illustrative numbers in prose.
    """
    expected = payload.get("test_count")
    if not isinstance(expected, int):
        return []
    # test_count is a LOWER BOUND ("N+ tests"), not an exact pin (decision #182):
    # a doc that claims N tests is honest as long as the suite has AT LEAST N.
    # So growth (found <= expected) is never drift — only an OVERCLAIM (a doc
    # asserting MORE tests than the live suite actually has) is flagged. This is
    # what closes the "add tests -> every doc number goes red" trap while still
    # catching a genuinely false claim.
    messages: list[str] = []
    for rel in CROSS_FILE_SCAN_TARGETS:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_fenced_blocks(path.read_text(encoding="utf-8"))
        for pattern, label in _TEST_COUNT_PATTERNS:
            for m in pattern.finditer(text):
                found = int(m.group(1))
                if found <= expected:
                    continue
                line_no = text[: m.start()].count("\n") + 1
                messages.append(
                    f"{rel}:{line_no}: test-count OVERCLAIM '{m.group(0)}' "
                    f"({label}, found={found}) exceeds live suite size "
                    f"test_count={expected} — docs claim more tests than exist"
                )
    return messages


def scan_code_counts(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Return drift messages for cross-file repo-state count refs.

    Walks :data:`CROSS_FILE_SCAN_TARGETS` plus :data:`CODE_COUNT_EXTRA_TARGETS`
    (hooks.md — version-ref-bearing, so scanned for counts only, like
    MCP_COUNT_EXTRA_TARGETS), strips fenced code blocks, and flags every
    :data:`_CODE_COUNT_PATTERNS` match whose captured int does not equal the
    corresponding ``constants.json`` count (stacks / hooks / review agents).
    """
    messages: list[str] = []
    for rel in (*CROSS_FILE_SCAN_TARGETS, *CODE_COUNT_EXTRA_TARGETS):
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_fenced_blocks(path.read_text(encoding="utf-8"))
        for pattern, key, label in _CODE_COUNT_PATTERNS:
            expected = payload.get(key)
            if not isinstance(expected, int):
                continue
            for m in pattern.finditer(text):
                found = int(m.group(1))
                if found == expected:
                    continue
                line_no = text[: m.start()].count("\n") + 1
                messages.append(
                    f"{rel}:{line_no}: {label} drift '{m.group(0)}' "
                    f"(found={found}) does not match constants.json {key}={expected}"
                )
    return messages
