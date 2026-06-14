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
    # Badge URL: "tests-2590%20passed-brightgreen"
    (re.compile(r"tests-(\d+)%20passed", re.IGNORECASE), "badge URL count"),
    # Badge alt-text: "[![2590 tests](...)]"
    (re.compile(r"!\[(\d+)\s+tests?\]"), "badge label count"),
    # Markdown bold: "**N tests**" (used in changelogs / release notes)
    (re.compile(r"\*\*(\d+)\s+tests?\*\*"), "bold tests count"),
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

    Walks :data:`CROSS_FILE_SCAN_TARGETS`, strips fenced code blocks, and
    flags every ``vX.Y`` / ``vX.Y.Z`` occurrence whose major.minor (and
    patch, if present) does not match ``expected_version``. Refs preceded
    by a foreign-version prefix (SENAR / Python / OWASP) are skipped —
    those products version independently.
    """
    messages: list[str] = []
    for rel in CROSS_FILE_SCAN_TARGETS:
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
