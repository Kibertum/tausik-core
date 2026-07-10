"""Cross-file drift scanners for `gen_doc_constants`.

Extracted from gen_doc_constants.py for filesize compliance
(v15p-doc-drift-gate). Each `scan_*` function walks
:data:`CROSS_FILE_SCAN_TARGETS`, strips fenced code blocks, and returns a list
of human-readable drift messages (empty when clean). gen_doc_constants
re-exports these names, so existing imports keep working unchanged.

Covered drift classes:
  - version refs (`vX.Y` / `vX.Y.Z`) vs `tausik_version`
  - MCP tool counts (`**N tools**`, `N project tools`, brain header, pair)
  - test counts (badge URL/label, `pytest suite (N tests)`, `**N tests**`)
  - repo-state counts (stacks / hooks / review agents)
"""

from __future__ import annotations

import re
from pathlib import Path

_VERSION_RE = re.compile(r"\bv(\d+)\.(\d+)(?:\.(\d+))?(?:\.x)?\b")
_FENCED_BLOCK_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)

# Python source files that hardcode a `__version__ = "X.Y.Z"` literal which
# must track pyproject's project.version. gen_doc_constants treats pyproject as
# the single source of truth; these modules duplicate it for runtime use (the
# CLI 'Current State' line via project_cli_extra._get_version and the MCP
# version handler). The literal stays a literal — the running copy under
# `.claude/scripts/` has no pyproject to read — but it silently drifted once
# (tausik_version.py stuck at 1.4.0 across the 1.4.1/1.4.2 releases), so the
# scanner below makes that drift visible at `--check` time.
PY_VERSION_SCAN_TARGETS: tuple[str, ...] = ("scripts/tausik_version.py",)
_PY_VERSION_RE = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.MULTILINE)

CROSS_FILE_SCAN_TARGETS: tuple[str, ...] = (
    "README.md",
    "README.ru.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/en/architecture.md",
    "docs/ru/architecture.md",
    "docs/en/mcp.md",
    "docs/ru/mcp.md",
)

# Files where a bare `vX.Y` means "the version you are running now", so a stale
# one is a bug worth failing on.
#
# architecture.md and mcp.md are deliberately absent. They annotate *when a thing
# arrived* — `tausik_session_open (v1.5)`, `hooks/check_docs.py (v1.5)`, "like in
# pre-v1.5 releases". Scanning them against the current version forced every minor
# bump to rewrite those markers, turning true statements into false ones. That is
# the same reason MCP_COUNT_EXTRA_TARGETS exists; the list simply missed these two.
# Their MCP tool counts are still checked — see scan_mcp_counts.
VERSION_SCAN_TARGETS: tuple[str, ...] = (
    "README.md",
    "README.ru.md",
    "AGENTS.md",
    "CLAUDE.md",
)

# Extra files scanned for MCP tool counts ONLY (not version/test/code-state).
# These docs hardcode the MCP count and drifted silently (93/98/100/105 vs 123)
# because they were outside CROSS_FILE_SCAN_TARGETS. They carry legitimate
# historical version refs (e.g. "introduced in v1.4") that would false-positive
# the version scanner, so they are guarded by the MCP-count scanner alone.
MCP_COUNT_EXTRA_TARGETS: tuple[str, ...] = (
    "docs/ru/agent-contract.md",
    "docs/ru/senar-compliance-matrix.md",
    "docs/en/senar-compliance-matrix.md",
    "docs/README.md",
)

# RU/EN word for "tool" in MCP-count contexts. Matches singular + plural genitive
# forms: tools, tool, инструмент, инструмента, инструментов.
_TOOL_WORD = r"(?:tools?|инструмент(?:а|ов)?)"

# MCP tool-count patterns. Each entry is (compiled regex, constants_key, label).
# The capture group is a single integer compared against constants.json[key].
# Patterns are ordered specific-first so context-rich matches (brain header)
# fire before generic ones (`X project tools`).
_MCP_COUNT_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    # `tausik-brain`, N tools — brain server header, e.g. "## Shared Brain (`tausik-brain`, 7 tools)"
    (
        re.compile(rf"`tausik-brain`[^)]*?,\s*(\d+)\s+{_TOOL_WORD}", re.IGNORECASE),
        "mcp_brain_tools",
        "tausik-brain server header",
    ),
    # **N tools** / **N MCP tools** / **N MCP-инструментов** — markdown bold main count
    (
        re.compile(rf"\*\*(\d+)\s+(?:MCP[-\s]+)?{_TOOL_WORD}\*\*", re.IGNORECASE),
        "mcp_main_tools",
        "main count (bold)",
    ),
    # N project tools — explicit project count, e.g. "93 project tools"
    (
        re.compile(rf"\b(\d+)\s+project\s+{_TOOL_WORD}\b", re.IGNORECASE),
        "mcp_project_tools",
        "project count",
    ),
    # N brain tools — explicit brain count, e.g. "7 brain tools"
    (
        re.compile(rf"\b(\d+)\s+brain\s+{_TOOL_WORD}\b", re.IGNORECASE),
        "mcp_brain_tools",
        "brain count",
    ),
)

# Pair pattern: "(N project + M brain ...)" — both groups checked independently.
_MCP_COUNT_PAIR_PATTERN: tuple[re.Pattern[str], tuple[str, str], str] = (
    re.compile(r"\((\d+)\s+project\s*\+\s*(\d+)\s+brain", re.IGNORECASE),
    ("mcp_project_tools", "mcp_brain_tools"),
    "project+brain pair",
)

# Test-count patterns. Each entry is (compiled regex, label). The capture
# group is a single integer compared against constants.json["test_count"].
# Patterns are deliberately narrow to avoid false positives on illustrative
# numbers like "Never add 5 tests where one parametrized test covers".
_TEST_COUNT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # "pytest suite (N tests)"
    (re.compile(r"pytest\s+suite\s+\((\d+)\s+tests?\)", re.IGNORECASE), "pytest suite count"),
    # shields.io badge URL: "tests-4540-brightgreen" (the actual badge format).
    # The old "%20passed" form below never matched our badges — the ru count
    # therefore drifted unchecked (a stale "4341 тестов" sat in README.ru.md
    # across releases). Anchored on the `tests-<n>-<color>` shields shape.
    (
        re.compile(
            r"tests-(\d+)-(?:brightgreen|green|yellowgreen|yellow|orange|red)", re.IGNORECASE
        ),
        "badge URL count",
    ),
    (re.compile(r"tests-(\d+)%20passed", re.IGNORECASE), "badge URL count (passed)"),
    # Badge alt-text: EN "![2590 tests]" and RU "![2590 тестов]".
    (re.compile(r"!\[(\d+)\s+tests?\]"), "badge label count"),
    (re.compile(r"!\[(\d+)\s+тест\w*\]"), "badge label count (ru)"),
    # Markdown bold: "**N tests**" / "**N тестов**" (changelogs, release notes).
    (re.compile(r"\*\*(\d+)\s+tests?\*\*"), "bold tests count"),
    (re.compile(r"\*\*(\d+)\s+тест\w*\*\*"), "bold tests count (ru)"),
    # Prose sentence in the README's pitch: "covered by N tests" / "покрыто N
    # тестами". Not bold-anchored, so the patterns above miss it — it drifted
    # apart from the badge (badge 4552, prose still 4540). These two phrasings
    # are specific enough not to catch illustrative numbers elsewhere.
    (re.compile(r"covered by (\d+)\s+tests?\b", re.IGNORECASE), "prose tests count"),
    (re.compile(r"покрыт[оаы]\w*\s+(\d+)\s+тест\w*", re.IGNORECASE), "prose tests count (ru)"),
)

# Code-state count patterns (stacks / hooks / review agents). Each entry is
# (compiled regex, constants_key, label); the capture group is compared to
# constants.json[key]. Deliberately narrow to dodge known false positives:
#   - PLURAL "stacks"/"стек(а|ов)" only — never matches the singular
#     "stack-aware checks" / "stack guides" / "stack-scoped gates" (those count
#     gates, not stacks).
#   - skills is intentionally absent — docs say "38 skills" (full vendor set)
#     while skills_core_count tracks the 12 core dirs, so a generic pattern
#     would false-positive. Skills drift is covered by constants.json itself.
_CODE_COUNT_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\b(\d+)\s+stacks\b", re.IGNORECASE), "stacks_count", "stacks count"),
    (
        re.compile(r"\b(\d+)\s+(?:стека|стеков)\b", re.IGNORECASE),
        "stacks_count",
        "stacks count (ru)",
    ),
    (re.compile(r"\b(\d+)\s+hooks\b", re.IGNORECASE), "hooks_count", "hooks count"),
    (re.compile(r"\b(\d+)\s+хуков\b", re.IGNORECASE), "hooks_count", "hooks count (ru)"),
    (
        re.compile(r"\b(\d+)\s+review\s+agents\b", re.IGNORECASE),
        "review_agents_count",
        "review-agents count",
    ),
)

# RENAR/renar: the sibling spec at renar.tech versions on its own timeline (the
# auto-generated CLAUDE.md memory-tail cites "renar.tech v1.0-draft"), so its
# refs must not be checked against TAUSIK's version — same as SENAR. Both cases
# (lowercase "renar.tech", uppercase "RENAR v1.0" prose) are covered.
_FOREIGN_VERSION_PREFIXES: tuple[str, ...] = ("SENAR", "Python", "OWASP", "RENAR", "renar")


def _strip_fenced_blocks(text: str) -> str:
    """Replace fenced code blocks with same-line-count whitespace.

    Preserves line numbers in the returned text so matches outside fences
    can be reported with their original line number.
    """

    def _repl(m: re.Match[str]) -> str:
        return "\n" * m.group().count("\n")

    return _FENCED_BLOCK_RE.sub(_repl, text)


_DYNAMIC_BLOCK_RE = re.compile(r"<!-- DYNAMIC:START -->.*?<!-- DYNAMIC:END -->", re.DOTALL)


def _strip_dynamic_block(text: str) -> str:
    """Blank CLAUDE.md's auto-generated DYNAMIC section (line-count preserving).

    The memory-tail there cites memory/decision titles verbatim — which can
    legitimately name historical TAUSIK versions (e.g. 'parity for v1.4
    features'). Those are not authored version claims, so they must not trip the
    version-ref drift check. Authored refs in the static body are still scanned.
    """

    def _repl(m: re.Match[str]) -> str:
        return "\n" * m.group().count("\n")

    return _DYNAMIC_BLOCK_RE.sub(_repl, text)


def _version_matches(major: int, minor: int, patch: int | None, expected: str) -> bool:
    """``patch`` is None for ``vX.Y`` refs — match major+minor only in that case."""
    parts = expected.split(".")
    exp_major = int(parts[0])
    exp_minor = int(parts[1]) if len(parts) > 1 else 0
    exp_patch = int(parts[2]) if len(parts) > 2 else 0
    if patch is None:
        return major == exp_major and minor == exp_minor
    return major == exp_major and minor == exp_minor and patch == exp_patch


def _is_foreign_version(text: str, match_start: int) -> bool:
    """True if the version ref belongs to another product (SENAR / Python / etc.).

    Looks 24 chars back from ``match_start`` for any of
    :data:`_FOREIGN_VERSION_PREFIXES` — these are products with independent
    version timelines that must not be checked against TAUSIK's.
    """
    window = text[max(0, match_start - 24) : match_start]
    return any(prefix in window for prefix in _FOREIGN_VERSION_PREFIXES)


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
    messages: list[str] = []
    for rel in CROSS_FILE_SCAN_TARGETS:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = _strip_fenced_blocks(path.read_text(encoding="utf-8"))
        for pattern, label in _TEST_COUNT_PATTERNS:
            for m in pattern.finditer(text):
                found = int(m.group(1))
                if found == expected:
                    continue
                line_no = text[: m.start()].count("\n") + 1
                messages.append(
                    f"{rel}:{line_no}: test-count drift '{m.group(0)}' "
                    f"({label}, found={found}) does not match "
                    f"constants.json test_count={expected}"
                )
    return messages


def scan_code_counts(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Return drift messages for cross-file repo-state count refs.

    Walks :data:`CROSS_FILE_SCAN_TARGETS`, strips fenced code blocks, and flags
    every :data:`_CODE_COUNT_PATTERNS` match whose captured int does not equal
    the corresponding ``constants.json`` count (stacks / hooks / review agents).
    """
    messages: list[str] = []
    for rel in CROSS_FILE_SCAN_TARGETS:
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


# ---------------------------------------------------------------------------
# Auto-fix: make `gen_doc_constants.py --write` able to repair the very things
# the scanners above report. The check_docs hook told users to "run
# gen_doc_constants.py and re-commit" — but that only rewrote constants.json and
# left the README badges/prose alone, so following the advice kept the gate red.
# ---------------------------------------------------------------------------


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

    for rel in CROSS_FILE_SCAN_TARGETS:
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
