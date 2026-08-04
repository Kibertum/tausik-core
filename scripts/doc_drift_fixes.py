"""Auto-fix for the doc-drift scanners — repair the counts/versions they report.

Split out of doc_drift_scanners.py (filesize compliance). Imports the shared
regex table + helpers from doc_drift_common; it never imports doc_drift_scanners,
so doc_drift_scanners can safely re-export ``write_cross_file_fixes`` from here
without a cycle.

The check_docs hook told users to "run gen_doc_constants.py and re-commit" — but
that only rewrote constants.json and left the README badges/prose alone, so
following the advice kept the gate red. ``write_cross_file_fixes`` repairs the
very refs the scanners flag, touching only those refs and never inside fenced
blocks or CLAUDE.md's DYNAMIC section.
"""

from __future__ import annotations

import re
from pathlib import Path

from doc_drift_common import (
    _CODE_COUNT_PATTERNS,
    _DYNAMIC_BLOCK_RE,
    _FENCED_BLOCK_RE,
    _MCP_COUNT_PATTERNS,
    _TEST_COUNT_PATTERNS,
    _VERSION_RE,
    CODE_COUNT_EXTRA_TARGETS,
    CROSS_FILE_SCAN_TARGETS,
    VERSION_SCAN_TARGETS,
    _is_foreign_version,
    _version_matches,
)


def _protected_spans(text: str, *, dynamic: bool) -> list[tuple[int, int]]:
    """Byte spans a fix must not touch: fenced code blocks (illustrative numbers)
    and, in CLAUDE.md, the auto-generated DYNAMIC block."""
    spans = [(m.start(), m.end()) for m in _FENCED_BLOCK_RE.finditer(text)]
    if dynamic:
        spans += [(m.start(), m.end()) for m in _DYNAMIC_BLOCK_RE.finditer(text)]
    return spans


def _in_span(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in spans)


def _replace_group1(match: re.Match[str], new_digits: str) -> str:
    """The whole match with only capture group 1 swapped for ``new_digits``."""
    whole = match.group(0)
    g1_start = match.start(1) - match.start(0)
    g1_end = match.end(1) - match.start(0)
    return whole[:g1_start] + new_digits + whole[g1_end:]


def _fix_counts(text: str, pattern: "re.Pattern[str]", expected: int) -> tuple[str, bool]:
    spans = _protected_spans(text, dynamic=False)
    changed = False

    def repl(m: "re.Match[str]") -> str:
        nonlocal changed
        if _in_span(m.start(), spans) or int(m.group(1)) == expected:
            return m.group(0)
        changed = True
        return _replace_group1(m, str(expected))

    return pattern.sub(repl, text), changed


def _fix_versions(text: str, expected_version: str, *, dynamic: bool) -> tuple[str, bool]:
    spans = _protected_spans(text, dynamic=dynamic)
    parts = expected_version.split(".")
    exp_major, exp_minor = parts[0], (parts[1] if len(parts) > 1 else "0")
    exp_patch = parts[2] if len(parts) > 2 else "0"
    changed = False

    def repl(m: "re.Match[str]") -> str:
        nonlocal changed
        if _in_span(m.start(), spans) or _is_foreign_version(text, m.start()):
            return m.group(0)
        major, minor = int(m.group(1)), int(m.group(2))
        patch = int(m.group(3)) if m.group(3) else None
        if _version_matches(major, minor, patch, expected_version):
            return m.group(0)
        changed = True
        # Preserve the ref's own precision: vX.Y stays two-part, vX.Y.Z three.
        return (
            f"v{exp_major}.{exp_minor}"
            if patch is None
            else f"v{exp_major}.{exp_minor}.{exp_patch}"
        )

    return _VERSION_RE.sub(repl, text), changed


def write_cross_file_fixes(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Rewrite every cross-file count / version ref to match ``payload``.

    Returns the repo-relative paths actually changed (empty when in sync — the
    fix is idempotent). Touches only refs the matching scanner would flag, and
    never inside fenced blocks or CLAUDE.md's DYNAMIC section.
    """
    changed_files: list[str] = []

    count_specs: list[tuple[str, "re.Pattern[str]", int]] = []
    test_count = payload.get("test_count")
    if isinstance(test_count, int):
        for pattern, _label in _TEST_COUNT_PATTERNS:
            count_specs.append(("count", pattern, test_count))
    for pattern, key, _label in _MCP_COUNT_PATTERNS:
        val = payload.get(key)
        if isinstance(val, int):
            count_specs.append(("count", pattern, val))
    for pattern, key, _label in _CODE_COUNT_PATTERNS:
        val = payload.get(key)
        if isinstance(val, int):
            count_specs.append(("count", pattern, val))

    # CODE_COUNT_EXTRA_TARGETS (hooks.md) carry historical version refs, so they
    # are repaired for counts only — never versions. That is already enforced
    # structurally: hooks.md is absent from VERSION_SCAN_TARGETS, so the version
    # branch below skips it. Detection (scan_code_counts) and repair therefore
    # stay in lockstep.
    for rel in (*CROSS_FILE_SCAN_TARGETS, *CODE_COUNT_EXTRA_TARGETS):
        path = repo_root / rel
        if not path.is_file():
            continue
        text = original = path.read_text(encoding="utf-8")
        file_changed = False
        for _kind, pattern, expected in count_specs:
            text, ch = _fix_counts(text, pattern, expected)
            file_changed = file_changed or ch
        if rel in VERSION_SCAN_TARGETS:
            text, ch = _fix_versions(
                text, str(payload.get("tausik_version", "")), dynamic=(rel == "CLAUDE.md")
            )
            file_changed = file_changed or ch
        if file_changed and text != original:
            path.write_text(text, encoding="utf-8")
            changed_files.append(rel)
    return sorted(changed_files)
