"""Shared constants + helpers for the doc-drift scanners and their auto-fixer.

Split out of doc_drift_scanners.py so the scanner module and the auto-fix module
(doc_drift_fixes.py) can both depend on one copy of the regex table and the
line-preserving text helpers without a circular import. Dependency direction is
one-way: doc_drift_scanners → doc_drift_common, doc_drift_fixes → doc_drift_common
(fixes never imports scanners; scanners re-exports write_cross_file_fixes at its
own module bottom, which is safe because common has no back-edge to either).

Covered drift classes (see the scanners for the walking logic):
  - version refs (`vX.Y` / `vX.Y.Z`) vs `tausik_version`
  - MCP tool counts (`**N tools**`, `N project tools`, brain header, pair)
  - test counts (badge URL/label, `pytest suite (N tests)`, `**N tests**`)
  - repo-state counts (stacks / hooks / review agents)
"""

from __future__ import annotations

import re

_VERSION_RE = re.compile(r"\bv(\d+)\.(\d+)(?:\.(\d+))?(?:\.x)?\b")
_FENCED_BLOCK_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)

# Python source files that hardcode a `__version__ = "X.Y.Z"` literal which
# must track pyproject's project.version. gen_doc_constants treats pyproject as
# the single source of truth; these modules duplicate it for runtime use (the
# 'Current State' line via claudemd_state.resolve_version, shared by the CLI and
# the MCP handler, and the MCP version handler). The literal stays a literal — the running copy under
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

# Extra files scanned for CODE-STATE counts ONLY (hooks / stacks / review agents /
# roles), never version/test/MCP. hooks.md hardcodes the registered-hook count in
# its header ("22 Python hooks + 1 shell") and drifted silently (a stale "20
# Python hooks / = 21" sat there across 1.8) because it was outside every scan
# list — scan_code_counts only walked CROSS_FILE_SCAN_TARGETS. It carries
# legitimate historical version refs (title "# Hooks (v1.4)", "ship with v1.4")
# that would false-positive the version scanner, so — exactly like
# MCP_COUNT_EXTRA_TARGETS — it is guarded by the code-count scanner alone.
CODE_COUNT_EXTRA_TARGETS: tuple[str, ...] = (
    "docs/en/hooks.md",
    "docs/ru/hooks.md",
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
    # "brain = N tools" / "brain = N инструментов" — the sum written after a
    # pair, where the bold spans the whole phrase so the bold pattern above
    # cannot see the count (docs/ru/architecture.md sat at "117 + 7 = 124"
    # through two releases with `--check` green; review #208, record #23).
    # Anchored on `brain =`: the auto-fixer rewrites what this matches, and an
    # unanchored "= N tools" would rewrite unrelated prose (record #24).
    (
        re.compile(rf"brain\s*(?:{_TOOL_WORD})?\s*=\s*(\d+)\s+{_TOOL_WORD}\b", re.IGNORECASE),
        "mcp_main_tools",
        "main count (after =)",
    ),
    # "MCP coverage N tools" / "MCP coverage (N инструментов)" — the compliance
    # matrix headline, which carries no bold at all (same review).
    (
        re.compile(rf"MCP coverage\s*\(?(\d+)\s+{_TOOL_WORD}\b", re.IGNORECASE),
        "mcp_main_tools",
        "MCP coverage headline",
    ),
    # "project-scoped tools (N)" / "project-scoped инструменты (N)" — the count
    # AFTER the noun, in mcp.md's server list; sat at 117 with `--check` green
    # (record #24).
    (
        re.compile(r"project-scoped\s+(?:tools?|инструмент\w*)\s*\((\d+)\)", re.IGNORECASE),
        "mcp_project_tools",
        "project-scoped count",
    ),
    # The optional `codebase-rag` server: its increment and the grand total it
    # produces. Both constants existed and NOTHING in the docs was checked
    # against either, which is how AGENTS.md went on saying "+7 tools -> **107**
    # total" after the total reached 159 (measured session #224). Anchored on
    # the server's own name and confined to one line (`.` never crosses a
    # newline without DOTALL), because "**N** total" on
    # its own would rewrite any total in any document.
    (
        re.compile(rf"codebase-rag`?.*?\+\s*(\d+)\s+{_TOOL_WORD}", re.IGNORECASE),
        "mcp_rag_tools",
        "codebase-rag increment",
    ),
    (
        re.compile(r"codebase-rag`?.*?\*\*(\d+)\*\*\s+total", re.IGNORECASE),
        "mcp_tools_with_optional_rag",
        "grand total with the optional server",
    ),
    # "the main N count" / "основной счёт N" — the sentence that EXCLUDES the
    # optional server from the main total, at the foot of both mcp.md files.
    # It names the count without the word "tools", so every pattern above
    # walked past it: line 7 of the same file said 152 and line 370 said 128,
    # both unchecked, one of them wrong (measured session #224).
    (
        re.compile(r"main\s+(\d+)\s+count\b", re.IGNORECASE),
        "mcp_main_tools",
        "main count (excluding the optional server)",
    ),
    (
        re.compile(r"основно\w+\s+счёт\s+(\d+)", re.IGNORECASE),
        "mcp_main_tools",
        "main count (excluding the optional server, ru)",
    ),
    # "the same N tools" — README prose beside the IDE table (record #24). The
    # table's own cells carry no word at all and are NOT guarded: dropping the
    # per-row count in favour of the headline number is the owner's call.
    (
        re.compile(rf"the same\s+(\d+)\s+{_TOOL_WORD}\b", re.IGNORECASE),
        "mcp_main_tools",
        "README prose count",
    ),
)

# Pair pattern: "(N project + M brain ...)" — both groups checked independently.
# The parenthesis is optional: "**121 project + 7 brain = 128 инструментов**"
# carries the pair without one and was invisible to the guard (review #208).
_MCP_COUNT_PAIR_PATTERN: tuple[re.Pattern[str], tuple[str, str], str] = (
    re.compile(r"\(?\b(\d+)\s+project\s*\+\s*(\d+)\s+brain", re.IGNORECASE),
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
#   - hooks: an OPTIONAL qualifier is allowed between the number and
#     "hooks"/"хук…" — "real-time" (README bullet "21 real-time hooks"), "Python"
#     and "active"/"активн…" (hooks.md header "22 Python hooks", "21 активный
#     хук"). All three evaded the old adjacency-anchored `\b(\d+)\s+hooks\b` and
#     drifted uncaught. The qualifier is an explicit allow-list, not `\w+`, so it
#     never swallows an unrelated noun ("3 tests where hooks fire"). RU side
#     matches the singular "хук" plus genitive/plural forms (хука/хуки/хуков) and
#     a hyphen-attached prefix ("Python-хука"), which the old `хуков`-only
#     pattern missed.
_CODE_COUNT_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\b(\d+)\s+stacks\b", re.IGNORECASE), "stacks_count", "stacks count"),
    (
        re.compile(r"\b(\d+)\s+(?:стека|стеков)\b", re.IGNORECASE),
        "stacks_count",
        "stacks count (ru)",
    ),
    (
        re.compile(r"\b(\d+)\s+(?:real[-\s]?time[-\s]|python\s+|active\s+)?hooks\b", re.IGNORECASE),
        "hooks_count",
        "hooks count",
    ),
    (
        re.compile(
            r"\b(\d+)\s+(?:real[-\s]?time[-\s]|python[-\s]|активн\w+\s+)?хук(?:а|ов|и)?\b",
            re.IGNORECASE,
        ),
        "hooks_count",
        "hooks count (ru)",
    ),
    (
        re.compile(r"\b(\d+)\s+review\s+agents\b", re.IGNORECASE),
        "review_agents_count",
        "review-agents count",
    ),
    # roles: built-in role profiles under harness/roles/. The count is quoted in
    # prose ("6 roles", "6 ролей") and drifted silently once — architecture.md
    # stayed at "5 roles" after devops landed as the sixth. Anchored on the noun
    # so it never catches "6 role-scoped gates" or "3 roles.md fixtures"; the RU
    # side matches роль/роли/ролей. The stale copy in architecture.md lives inside
    # a ``` fence (illustrative tree), so _strip_fenced_blocks hides it from this
    # pattern by design — it is reconciled as a literal, not auto-fixed.
    (re.compile(r"\b(\d+)\s+roles\b", re.IGNORECASE), "roles_count", "roles count"),
    (
        re.compile(r"\b(\d+)\s+рол(?:ь|и|ей)\b", re.IGNORECASE),
        "roles_count",
        "roles count (ru)",
    ),
    # skills: quoted two ways in one breath -- "13 core skills ... 20 official"
    # -- and neither was checked. AGENTS.md said "12 core" and "25+ official"
    # against 13 and 20. Anchored on the adjective so "3 skills.md fixtures" is
    # never caught; the "+"-decorated form ("25+") is deliberately NOT matched,
    # so a claim written as a lower bound has to be rewritten into a plain count
    # before anything can check it -- the same rule the table cells follow.
    (
        re.compile(r"\b(\d+)\s+core[-\s]skills?\b", re.IGNORECASE),
        "skills_core_count",
        "core-skills count",
    ),
    (
        re.compile(r"\b(\d+)\s+core[-\s]скилл\w*", re.IGNORECASE),
        "skills_core_count",
        "core-skills count (ru)",
    ),
    (
        re.compile(r"\b(\d+)\s+official[-\s](?:skills?|скилл\w*)", re.IGNORECASE),
        "skills_official_count",
        "official-skills count",
    ),
)

# Closed-list ENUMERATIONS spelled out in prose: three or more slash-joined
# tokens, e.g. "ARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS" or
# "draft/review/asked/answered/approved/frozen/superseded".
#
# THE THREE-TOKEN BOUND IS NOT THE GUARD, and saying so here is the honest
# reading of a mutation that SURVIVED: relaxing it to two changes no verdict,
# because a two-token run cannot reach CLOSED_LIST_MIN_OVERLAP and is dropped a
# step later regardless. The bound is here to keep the scan off the "and/or"
# pairs and two-segment paths of ordinary prose — cheaper and clearer, not
# load-bearing. The overlap floor below is what decides.
#
# THE SUBJECT IS DERIVED, NOT ANCHORED. An earlier shape keyed each pattern to a
# phrase near the enumeration ("closed list of N (", "§7.8.1 closed list:") and
# would have read a FORMULATION rather than a property — the mistake memory #488
# records. Worse, it cannot work here: the enumeration this guard exists to
# catch is one whose CONTENT is wrong, so the subject has to be recognised from
# a partial match. `scan_closed_list_enums` therefore picks the closed list with
# the largest overlap and reports the difference against it.
_CLOSED_LIST_ENUM_RE = re.compile(r"\b([A-Za-z][A-Za-z\-]*(?:/[A-Za-z][A-Za-z\-]*){2,})\b")

# A count written immediately before such an enumeration: "closed list of 9 (",
# "закрытый список 9 (". Searched in the text PRECEDING a matched enumeration,
# so the number and the values are judged as one claim rather than two.
_CLOSED_LIST_COUNT_RE = re.compile(
    r"(?:closed\s+list\s+of|закрытый\s+список)\s+(\d+)\s*\(?\s*$", re.IGNORECASE
)

# How far back to look for that count. One clause of prose; long enough for
# "`type` is a closed list of 9 (", short enough not to reach the previous
# sentence's number.
CLOSED_LIST_COUNT_LOOKBEHIND = 40

# Overlap below which an enumeration is NOT one of our closed lists. Two shared
# tokens is coincidence ("draft/review" in a sentence about workflow); three is
# a quotation of the list.
CLOSED_LIST_MIN_OVERLAP = 3

# RENAR/renar: the sibling spec at renar.tech versions on its own timeline (the
# auto-generated CLAUDE.md memory-tail cites "renar.tech v1.0-draft"), so its
# refs must not be checked against TAUSIK's version — same as SENAR. Both cases
# (lowercase "renar.tech", uppercase "RENAR v1.0" prose) are covered.
_FOREIGN_VERSION_PREFIXES: tuple[str, ...] = ("SENAR", "Python", "OWASP", "RENAR", "renar")

_DYNAMIC_BLOCK_RE = re.compile(r"<!-- DYNAMIC:START -->.*?<!-- DYNAMIC:END -->", re.DOTALL)


def _strip_fenced_blocks(text: str) -> str:
    """Replace fenced code blocks with same-line-count whitespace.

    Preserves line numbers in the returned text so matches outside fences
    can be reported with their original line number.
    """

    def _repl(m: re.Match[str]) -> str:
        return "\n" * m.group().count("\n")

    return _FENCED_BLOCK_RE.sub(_repl, text)


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
