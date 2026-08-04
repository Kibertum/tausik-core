r"""Detectors the AC-evidence parser applies to one evidence line.

Split out of `service_ac_evidence` (which hit the 400-line gate): WHAT counts as
a marker is a separate concern from HOW lines are segmented and matched to AC
items, and the split is what gives the parity registry below a home.

Two kinds, and the difference is the whole point of this module:

* PROSE detectors read natural language the agent writes about its own
  verification. They must cover every language the project's evidence is
  actually written in.
* STRUCTURAL detectors read markup — paths, check marks, numbering. They are
  language-independent by construction.

Language parity (task-done-evidence-written-after-the-gate-that-reads-it):
`DOMAIN_RE` was bilingual from birth; `NEGATIVE_RE`, `MANUAL_RE` and
`REVIEW_RE` were English-only in a project whose working language is Russian.
Of the two NOTEs printed side by side at closure ("no `Negative:` evidence" /
"domain challenge"), only the second was satisfiable in the language the
evidence is written in — measured on three real closures of session #134, whose
negative scenarios WERE exercised and pinned, in Russian. Worse, MANUAL and
REVIEW feed `checklist_missing`, a HARD block for substantial/deep tiers, so
the gap could BLOCK a closure whose manual run was described in Russian.

Each detector is deliberately equally loose in both languages (bare stem, not a
required phrase). Two once broke that symmetry in opposite directions and were
realigned: REVIEW_RE required a structural English phrase (`/review`, `review
record`) while crediting the bare Russian `ревью`, so `code review completed`
was HARD-blocked where `код прошёл ревью` passed — English is now a bare
`\breview\w*` too. DOMAIN_RE was the mirror image: `\bdomain\b` is bounded but
the Russian stem was not, so `поддоменное` (subdomain) earned a domain-challenge
credit English never gave `subdomain` — the Russian stem is now bounded
(`\bдоменн\w*`). Convention #301: when you port a detector to a new dialect,
port the false-positive list it already paid for — inventing a stricter (or
looser) dialect is how two judges start disagreeing.

Both halves therefore share the same known weakness: they match a WORD, not a
fact ("no negative scenario" / "негативных сценариев нет" both credit evidence).
That is the pre-existing keyword-theater class (see
`gate_ac_check.checklist_missing`), it is symmetric across languages, and it is
NOT fixed here.
"""

from __future__ import annotations

import re

CHECK_MARK_RE = re.compile(r"[✓✔✅]|\[v\]")
AC_NUMBER_PREFIX_RE = re.compile(r"^\s*(?:AC[-\s]*)?(\d+)[\.\):]?\s*(.*)$", re.IGNORECASE)

# The `AC` token above is OPTIONAL, and that is right for the input it was
# written for: the `acceptance_criteria` FIELD, whose lines are numbered by
# construction, so a leading digit there is an index and nothing else.
#
# Free-form task NOTES are not that input. `3 retries were added to the flaky
# client` opens with a digit and is a sentence. This stricter form exists so the
# notes parser can tell a heading from prose: only an explicit `AC` token may
# open a section that following lines inherit. Without it, one ordinary sentence
# silently donates its number to whatever citation comes next.
AC_SECTION_HEADING_RE = re.compile(r"^\s*AC[-\s]*(\d+)\b", re.IGNORECASE)
# The two prefixes an evidence line legitimately carries in front of its AC
# number, both authored by the project's own tooling — so the start-anchored
# AC_NUMBER_PREFIX_RE fails to see the number behind them
# (ac-evidence-parser-format-strict, measured session #133):
#   * task_log ALWAYS prepends "[<iso-timestamp>] " to every note line;
#   * agents/fixtures write an "AC verified:" / "AC:" header before "1. ...".
# Stripped ONLY for index detection — never widening what counts as a marker:
# after stripping, the SAME strict regex runs, so a numberless prose line still
# earns no credit. The header strip is colon-anchored so it can never eat an
# "AC-1:" token (which carries the number itself and is matched elsewhere).
TIMESTAMP_PREFIX_RE = re.compile(r"^\s*\[[^\]]*\]\s*")
AC_HEADER_PREFIX_RE = re.compile(r"^\s*AC(?:\s+[a-zA-Z]+)?\s*:\s*", re.IGNORECASE)
TEST_REF_RE = re.compile(
    r"(tests?/[\w/.\-]+\.py(?:::[\w_]+)?|test_[\w_]+\.py(?:::[\w_]+)?)",
    re.IGNORECASE,
)
# MEASUREMENT — the strongest evidence in the project (a real gate run) was the
# ONLY kind the parser could not see (ac-evidence-parser-cannot-see-a-measurement):
# a criterion proven by `5778 passed ... in 564s` / `verification_run #1285`
# scored as "no evidence", so a bare check mark was the cheaper path. Two forms,
# both read by NUMBER, not by a word:
#   * a signed run citation `verification_run #NNNN` — the run id is captured so
#     the GATE layer can fact-check it against the verification_runs table (exists,
#     same task, green); the detector reads form, the gate reads fact.
#   * a pytest summary `N passed ... in T s` — recognised by the passed-count shape.
VERIFICATION_RUN_RE = re.compile(r"verification[_\s]run\s*#?(\d+)", re.IGNORECASE)
PYTEST_SUMMARY_RE = re.compile(r"\b(\d+)\s+passed\b", re.IGNORECASE)
NEGATIVE_RE = re.compile(r"\bnegative\b|негативн\w*|отрицательн\w*", re.IGNORECASE)
MANUAL_RE = re.compile(r"\bmanual(?:ly)?\b|\bвручную\b|\bручн\w+\b", re.IGNORECASE)
# A bare `review` stem, symmetric with the Russian bare `ревью`: English used to
# require a structural phrase (`/review`, `review record`) — stricter than the
# Russian side — so `code review completed` was HARD-blocked where `код прошёл
# ревью` passed. `\breview\w*` subsumes the old phrases and covers reviewed/
# reviewer, matching the looseness the module already accepts for both languages.
REVIEW_RE = re.compile(
    r"\breview\w*|adversarial|\bревью\b|состязательн\w*",
    re.IGNORECASE,
)
# SENAR Rule 4 domain challenge (v15s-rule4-domain-challenge): does the result
# make sense OUTSIDE the tests? arXiv 2605.30353 — agents pass tests with
# physically meaningless outputs. An evidence line answering the domain question.
DOMAIN_RE = re.compile(
    r"\bdomain\b|\bsanity\b|makes?\s+sense|имеет\s+смысл|\bдоменн\w*|real[\s\-]?world",
    re.IGNORECASE,
)
# Start of a numbered AC item inside a single-line blob: optional "AC-" prefix,
# a number, a separator (. ) :), then whitespace. Anchored to start-of-text or a
# preceding whitespace/`;`/`(` so a mid-token number (Python 3.11, SHA-256,
# v1.4, "returns 0)") cannot start a spurious item.
AC_ITEM_BOUNDARY_RE = re.compile(
    r"(?:^|(?<=[\s;(]))(?:AC[-\s]*)?(\d+)\s*[.):]\s",
    re.IGNORECASE,
)

# Producer-side registry. The parity test does NOT enumerate detectors itself —
# it reads the names `service_ac_evidence._evidence_lines_for_unit` actually
# applies (from its bytecode) and requires each to be declared in exactly one
# bucket here, then requires every PROSE member to match Cyrillic text. A new
# prose detector added English-only therefore fails the test instead of quietly
# widening the gap this module exists to close. (Session #134 warning: a test
# that enumerates the set it guards cannot notice the set growing.)
PROSE_DETECTORS: dict[str, re.Pattern[str]] = {
    "NEGATIVE_RE": NEGATIVE_RE,
    "MANUAL_RE": MANUAL_RE,
    "REVIEW_RE": REVIEW_RE,
    "DOMAIN_RE": DOMAIN_RE,
}
STRUCTURAL_DETECTORS: dict[str, re.Pattern[str]] = {
    "CHECK_MARK_RE": CHECK_MARK_RE,
    "TEST_REF_RE": TEST_REF_RE,
    "AC_NUMBER_PREFIX_RE": AC_NUMBER_PREFIX_RE,
    "AC_SECTION_HEADING_RE": AC_SECTION_HEADING_RE,
    "AC_ITEM_BOUNDARY_RE": AC_ITEM_BOUNDARY_RE,
    # Measurement forms — structural (read by number, language-independent).
    "VERIFICATION_RUN_RE": VERIFICATION_RUN_RE,
    "PYTEST_SUMMARY_RE": PYTEST_SUMMARY_RE,
}
