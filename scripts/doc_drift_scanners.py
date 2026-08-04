"""Cross-file drift scanners for `gen_doc_constants`.

Extracted from gen_doc_constants.py for filesize compliance
(v15p-doc-drift-gate). Each `scan_*` function walks its target list, strips
fenced code blocks, and returns a list of human-readable drift messages (empty
when clean). gen_doc_constants re-exports these names, so existing imports keep
working unchanged.

The regex table + line-preserving text helpers live in :mod:`doc_drift_common`;
the auto-fixer (``write_cross_file_fixes``) lives in :mod:`doc_drift_fixes` and
is re-exported here so `from doc_drift_scanners import write_cross_file_fixes`
keeps resolving. The three-module split keeps each file under the 400-line cap
with no duplication and no circular import (scanners→common, scanners→fixes,
fixes→common; fixes never imports scanners).

Covered drift classes:
  - version refs (`vX.Y` / `vX.Y.Z`) vs `tausik_version`
  - MCP tool counts (`**N tools**`, `N project tools`, brain header, pair)
  - test counts (badge URL/label, `pytest suite (N tests)`, `**N tests**`)
  - repo-state counts (stacks / hooks / review agents)
"""

from __future__ import annotations

from pathlib import Path

from doc_drift_common import (
    _CODE_COUNT_PATTERNS,
    _MCP_COUNT_PAIR_PATTERN,
    _MCP_COUNT_PATTERNS,
    _PY_VERSION_RE,
    _TEST_COUNT_PATTERNS,
    _VERSION_RE,
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

__all__ = [
    "CROSS_FILE_SCAN_TARGETS",
    "scan_version_refs",
    "scan_py_version_constants",
    "scan_mcp_tool_counts",
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
        if rel == "CLAUDE.md":
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
    every ``**N tools**`` / ``N project tools`` / ``N brain tools`` /
    ``(N project + M brain`` / ```tausik-brain`, N tools`` whose captured int
    does not match the corresponding constants.json key.

    Patterns are deliberately specific-context (require "project"/"brain"/
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

        pair_re, (k1, k2), pair_label = _MCP_COUNT_PAIR_PATTERN
        exp1 = payload.get(k1)
        exp2 = payload.get(k2)
        if isinstance(exp1, int) and isinstance(exp2, int):
            for m in pair_re.finditer(text):
                got1, got2 = int(m.group(1)), int(m.group(2))
                if got1 == exp1 and got2 == exp2:
                    continue
                line_no = text[: m.start()].count("\n") + 1
                messages.append(
                    f"{rel}:{line_no}: MCP {pair_label} drift '{m.group(0)}' "
                    f"(found={got1} project + {got2} brain) does not match "
                    f"constants.json {k1}={exp1}, {k2}={exp2}"
                )
    return messages


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
