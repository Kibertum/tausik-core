"""The SPEC type list lives in ONE place, and its length is never written beside it.

Two defects are pinned here, and they are different:

* COMPOSITION — the list was nine where §8.3 closes it at eleven. ADR-013 added
  SPEC-TEST and SPEC-DOC; ADR-023 then wrote "во всех ОДИННАДЦАТИ типах" into
  §8.4.1, so the shortfall stopped being cosmetic and became a norm we had no
  subject to execute for two of its types.
* ARITHMETIC — the count was written as a literal ("CLOSED list of 9") next to
  the list it counts. That is the mechanism by which the prose came to disagree
  with the code, and fixing the number alone would only reset the clock.

The second class is the one that recurs, so the test for it must red on a
literal count EVEN WHEN THE NUMBER IS CURRENTLY RIGHT: a hand-written "11" is
the same defect as a hand-written "9", merely not yet observable.
"""

from __future__ import annotations

import io
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from service_specs import SPEC_TYPES  # noqa: E402

# Transcribed from standard/08-specifications.md §8.3 — deliberately NOT derived
# from SPEC_TYPES. Comparing a value against the constant that produced it is a
# tautology (memory #474); the standard's literal is the only honest reference.
STANDARD_ELEVEN = (
    "ARCH",
    "API",
    "DATA",
    "INT",
    "PROC",
    "UI",
    "AI",
    "SEC",
    "OPS",
    "TEST",
    "DOC",
)

# Where a literal list of SPEC types is legitimate, and why.
ALLOWED_LITERAL_LISTS = {
    # The single source itself.
    "scripts/service_specs.py",
    # A HISTORICAL migration: it recorded the schema as it was in v35 and must
    # never be edited, or the migration chain stops describing what it built.
    "scripts/backend_migrations_v35.py",
    # v49 rebuilds the table, so it necessarily writes the new CHECK out in SQL.
    "scripts/backend_migrations_v49.py",
    # The baseline DDL for a fresh database — SQL, not Python, so it cannot
    # interpolate the tuple.
    "scripts/backend_schema_specs.py",
    # The standard's own eleven, kept independent on purpose as the denominator
    # the completeness report divides by.
    "scripts/spec_completeness.py",
    # This file: the transcription above.
    "tests/test_spec_types_closed_list.py",
}

SCAN_DIRS = ("scripts", "harness", "tests")

# This file walks the source tree looking for a second literal list and for a
# hand-written count, so no import edge selects it from the change that would
# reintroduce either. Declared rather than opted out of: the paths below are
# exactly the trees the scan covers, and a change anywhere in them must pull
# this test in (memory #478 — declare the scope, never baseline the gap).
CROSSCUTTING_SCOPE = ["scripts/", "harness/", "tests/"]
# Four consecutive quoted SPEC type names — enough to be a list, not a mention.
LIST_RE = re.compile(
    r"""(['"])(ARCH|API|DATA|INT|PROC|UI|AI|SEC|OPS|TEST|DOC)\1\s*,\s*"""
    r"""(['"])(ARCH|API|DATA|INT|PROC|UI|AI|SEC|OPS|TEST|DOC)\3\s*,\s*"""
    r"""(['"])(ARCH|API|DATA|INT|PROC|UI|AI|SEC|OPS|TEST|DOC)\5\s*,\s*"""
    r"""(['"])(ARCH|API|DATA|INT|PROC|UI|AI|SEC|OPS|TEST|DOC)\7"""
)
# --- the count, as a PROPERTY rather than a phrasing -------------------------
#
# What stood here matched the literal phrase "closed list of N". It was written
# against the one sentence that happened to be wrong the day it was written, so
# it read a PHRASING and not a property — and four other sentences saying the
# same thing in other words walked straight past it, including one in
# service_specs.py, the single source itself, and one spelled out as a word
# rather than a digit. A detector shaped to one formulation checks the
# formulation (memory #488).
#
# The property is: A COUNT OF THE CLOSED LIST, WRITTEN OUT. Its negation — the
# only acceptable form — is a count formatted from len(SPEC_TYPES), and that
# form by construction leaves no literal in the source at all. This is what
# makes the green branch expressible rather than merely hoped for: the derived
# form contains no number to find.
#
# Scoped to SPEC on purpose. The ADAPT backward-finding categories carry the
# identical defect with a currently-correct number ("CLOSED list of 7" in
# service_adapts.py / tools_adapt.py); that is filed as
# adapt-finding-categories-count-is-written-not-derived, which GENERALISES this
# matcher rather than copying it. Widening it here would widen that task
# silently, so _SPEC_SUBJECT below deliberately does not fire on ADAPT prose.

# A decimal that is a COUNT, and not something else that merely carries digits.
# Rejected by the lookarounds: v49 and v16r-spec-types (glued to an identifier),
# §8.3 and 1.5 (part of a dotted number), ADR-013 and QG-0 (a hyphenated
# designator). Each of those sets a digit beside the subject while asserting
# nothing whatever about how many types there are.
_DIGIT = r"(?<![0-9A-Za-z_.§-])[0-9]{1,3}(?![0-9A-Za-z_.-])"

# Counts spelled as words. "our closed list has nine" is the form the docstring
# of spec_completeness.py lied in, and `\d+` does not see it. Russian is here
# because half the prose in this tree is Russian and the defect does not care
# which language it is written in.
#
# THE FLOOR AT THREE IS DELIBERATE, AND IS A DECLARED LIMIT rather than an
# oversight: English "one" and "two" are pronouns far more often than counts
# ("one of the closed types"), so admitting them would buy two more catchable
# phrasings at the price of a matcher too noisy to keep. No closed list in this
# codebase is shorter than seven.
_NUMBER_WORDS = (
    r"three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen"
    r"|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
    r"|тр[её]х|четыр\w*|пят\w*|шест\w*|сем\w*|восьм\w*|восем\w*|девят\w*"
    r"|десят\w*|одиннадцат\w*|двенадцат\w*|тринадцат\w*|двадцат\w*"
)
_NUM = r"(?:" + _DIGIT + r"|(?:" + _NUMBER_WORDS + r"))"

# The orders this codebase has actually written the count in — number first and
# number last are the same claim, which is exactly what the old pattern missed.
_COUNT_FORMS = (
    # "9 closed SPEC types", "eleven RENAR types", "9 closed types"
    re.compile(_NUM + r"(?:\s+\w+){0,2}\s+types?\b", re.IGNORECASE),
    # "closed list of 9 RENAR types", "list of eleven"
    re.compile(r"list\s+of\s+" + _NUM + r"\b", re.IGNORECASE),
    # "our closed list has nine", "Ours now carries the same eleven"
    re.compile(
        r"\b(?:has|have|carries|carry|holds|hold|contains|contain|enumerated|numbers)\s+"
        r"(?:the\s+same\s+|only\s+|now\s+|just\s+)?" + _NUM + r"\b",
        re.IGNORECASE,
    ),
    # Russian: "доводится до одиннадцати", "в системе, знающей девять"
    re.compile(r"(?:до|из|в|на|знающ\w*)\s+(?:" + _NUMBER_WORDS + r")\b", re.IGNORECASE),
)

# A line is a claim about the SPEC type list only if it is talking about it.
_SPEC_SUBJECT = re.compile(r"SPEC|RENAR\s+type|перечн|тип", re.IGNORECASE)

# Where a written count is legitimate, and why. TWO CLASSES ONLY, and neither of
# them is "not got round to it yet": an entry admitted for a live present-tense
# claim would be baselining the very gap this test exists to close (memory #478).
ALLOWED_WRITTEN_COUNTS = {
    "scripts/backend_migrations.py": (
        "the registry's one-line note on what v49 does — a migration that stops "
        "describing what it built stops being a journal"
    ),
    "scripts/backend_migrations_v49.py": (
        "the v49 record itself: it widened the list TO eleven and must say so, "
        "on the same ground that freezes backend_migrations_v35.py above"
    ),
    "tests/test_migrations_v49_spec_types.py": (
        "past tense about the pre-migration state this test pins — 'ours "
        "enumerated nine' describes what WAS, and asserts nothing about what is"
    ),
    "tests/test_spec_types_closed_list.py": "this file: the fixtures below",
}


def written_counts(text: str) -> list[str]:
    """Every literal count of the SPEC type list in ``text``.

    Split out from the tree walk deliberately (memory #484). A detector that can
    only be run against the repository has no expressible green branch — the
    tree cannot be made to *not* contain a counting phrase — so a matcher that
    always reported a finding would be indistinguishable from one that works.
    Handed a string, it can be shown to stay silent on the derived form.
    """
    found = []
    for line in text.splitlines():
        if not _SPEC_SUBJECT.search(line):
            continue
        for rx in _COUNT_FORMS:
            m = rx.search(line)
            if m:
                found.append(m.group(0).strip())
                break
    return found


def _sources():
    for d in SCAN_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, d)):
            dirnames[:] = [x for x in dirnames if x != "__pycache__"]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
                with io.open(full, encoding="utf-8", newline="") as fh:
                    yield rel, fh.read()


# --- composition -------------------------------------------------------------


def test_closed_list_is_the_standards_eleven():
    assert SPEC_TYPES == STANDARD_ELEVEN
    assert len(SPEC_TYPES) == 11


def test_the_two_types_adr_013_added_are_present():
    """Named separately: an equality test above would also pass on a rewrite
    that swapped two unrelated names in and out."""
    assert "TEST" in SPEC_TYPES, "SPEC-TEST — test benches and data (ADR-013)"
    assert "DOC" in SPEC_TYPES, "SPEC-DOC — delivered documentation (ADR-013)"


def test_no_duplicate_type_names():
    assert len(set(SPEC_TYPES)) == len(SPEC_TYPES)


# --- one source --------------------------------------------------------------


def test_no_second_literal_list_of_spec_types():
    offenders = sorted(
        rel for rel, src in _sources() if rel not in ALLOWED_LITERAL_LISTS and LIST_RE.search(src)
    )
    assert not offenders, (
        "a second literal list of SPEC types is a future divergence, not a mirror; "
        f"found in: {offenders}. Import SPEC_TYPES, or add the path to "
        "ALLOWED_LITERAL_LISTS with the reason it must stay literal."
    )


def test_mcp_tool_enum_is_read_from_the_single_source():
    """The MCP schema used to keep its own nine — pinned by a test, but still a
    second literal somebody had to remember to edit."""
    import importlib.util

    path = os.path.join(ROOT, "harness", "claude", "mcp", "project", "tools_spec.py")
    spec = importlib.util.spec_from_file_location("_ts_under_test", path)
    if spec is None or spec.loader is None:
        pytest.skip("MCP harness not present in this checkout")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod._SPEC_TYPES == list(SPEC_TYPES)
    assert len(mod._SPEC_TYPES) == 11


# --- the count is derived, never written -------------------------------------


def test_no_hand_written_count_beside_the_list():
    """Reds on a literal count even when the number is currently correct.

    The number being right today is not the property under test — being DERIVED
    is. A correct literal is the same defect, deferred to the next amendment.
    """
    offenders = []
    for rel, src in _sources():
        if rel in ALLOWED_WRITTEN_COUNTS:
            continue
        for frag in written_counts(src):
            offenders.append(f"{rel}: {frag!r}")
    assert not offenders, (
        "the count of SPEC types must be formatted from len(SPEC_TYPES), never "
        f"written beside the list: {offenders}. If a count is genuinely "
        "historical — a migration recording what it built — add the path to "
        "ALLOWED_WRITTEN_COUNTS with that reason; never to silence a live claim."
    )


class TestTheCountMatcherReadsThePropertyNotThePhrasing:
    """The matcher above, exercised on strings rather than on the tree.

    Fixtures are STRINGS, and that is the point (memory #485): a degenerate
    measurer is repaired by changing the substrate a test hands it, never by
    relaxing the assertion — a diff that touches the `assert` is the tell that a
    fix was fitted to the test. Every red sample below is a line this repository
    actually carried.
    """

    @pytest.mark.parametrize(
        "sample",
        [
            # The one phrasing the predecessor of this matcher knew about.
            "help=f'Closed list of 9 RENAR types'",
            # The clause evidence it walked past — number FIRST, not last.
            '"evidence": "9 closed SPEC types enforced (service + DB CHECK)",',
            # Spelled as a word, in the single source's own reach() docstring.
            "SPEC types; our closed list has nine (`service_specs.SPEC_TYPES`), because",
            # In service_specs.py — the file the list was consolidated INTO.
            '"""Create a SPEC. ``type_`` must be one of the 9 closed RENAR types.',
            '"""v16r-spec-types: RENAR SPEC artifacts (9 closed types).',
        ],
    )
    def test_reds_on_a_written_count_whatever_the_word_order(self, sample):
        assert written_counts(sample), (
            "the count is written out here; a matcher that misses it is reading "
            f"one formulation and not the property: {sample!r}"
        )

    @pytest.mark.parametrize(
        "sample",
        [
            "Closed list of 11 RENAR types",
            '"evidence": "11 closed SPEC types enforced",',
            "# SPEC_TYPES. Ours now carries the same eleven (v49 / ADR-013), and that is",
        ],
    )
    def test_reds_even_when_the_written_number_is_right(self, sample):
        """A matcher that went green on agreement would measure nothing.

        These samples state the count CORRECTLY. A correct literal is the same
        defect as a wrong one, merely not yet observable, and a test satisfied by
        agreement cannot tell a derived number from a written one — which is the
        degenerate measurer of memory #484 facing the other way.
        """
        assert len(SPEC_TYPES) == 11, "the samples below agree with the list on purpose"
        assert written_counts(sample), f"a correct literal is still a literal: {sample!r}"

    @pytest.mark.parametrize(
        "sample",
        [
            # The only acceptable form: no literal exists to drift.
            'help=f"Closed list of {len(SPEC_TYPES)} RENAR types",',
            'f"SPEC type list closed at {len(SPEC_TYPES)} (service + DB CHECK)"',
            # Digits set beside the subject that count nothing at all.
            '"""TAUSIK MCP tool definitions — RENAR SPEC artifacts (v16r-spec-types).',
            "from backend_migrations_v49 import maybe_widen_spec_types_v49",
            "§8.3 closes the SPEC type list, and ADR-013 named the additions",
            "assert len(manifest['spec-types-supported']) == 11",
            # THE FOUR BELOW ISOLATE THE LOOKAROUNDS ON _DIGIT, and they are here
            # because a mutation proved the four above do not. Each of those is
            # rejected by some OTHER part of the matcher — no whitespace after
            # the digit, no `types` within reach — so stripping the lookarounds
            # left every one of them green and the mutation survived. These are
            # shaped so that the lookaround is the ONLY thing standing between
            # the sample and a match: delete it and each becomes "N <word>
            # types", which is form one exactly.
            "# v49 widened types (ADR-013)",
            "§8.3 lists types the standard closes over",
            "ADR-013 admitted types SPEC-TEST and SPEC-DOC",
            "schema version 1.5 types are unchanged by this migration",
        ],
    )
    def test_stays_green_on_derived_counts_and_on_digits_that_count_nothing(self, sample):
        """Without this branch a matcher returning a finding for every line would
        pass every red case above and be indistinguishable from a working one."""
        assert written_counts(sample) == [], (
            "nothing here writes a count of the closed list; a matcher that reds "
            f"on this is finding digits, not claims: {sample!r}"
        )


def test_parser_help_reports_the_derived_count():
    import argparse

    import project_parser_specs as pps

    assert pps.SPEC_TYPE_CHOICES == list(SPEC_TYPES)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    pps.build_spec_subparsers(sub)
    spec_sub = sub.choices["spec"]._subparsers._group_actions[0]
    help_text = spec_sub.choices["add"].format_help()
    # The live help string, not the source: this is what `tausik spec add --help`
    # actually prints, which is where the wrong number was visible to a user.
    assert f"Closed list of {len(SPEC_TYPES)} RENAR types" in help_text
    assert "list of 9" not in help_text


# --- ADR-013's conditional obligations, and when the declaration expires ------


def test_adr_013_conditional_obligations_are_still_vacuous():
    """Admitting SPEC-TEST and SPEC-DOC brought two CONDITIONAL duties with them.

    Neither is executable today, and neither is being skipped silently — the
    declaration is recorded in
    adr-013-conditional-obligations-expire-when-subject-appears. What that task
    cannot do is notice when it stops being true, so this test does:

    * TC.environment-ref on SPEC-TEST (§9 p.119) — TC does not exist here as an
      artifact class at all. Vacuously true, on the same grounds that make
      tc-pos-neg-pairing vacuous and SPEC provenance NOT vacuous: no subject.
    * a doc lint for SPEC-DOC — we hold zero SPEC-DOC artifacts, and
      scripts/docs_lint.py is warning-only and not bound to the type.

    This reds the moment either subject appears, which is exactly when the duty
    becomes live. It is deliberately NOT skipped when the project DB is absent
    in a way that hides the check — an absent DB means no subject either.
    """
    db = os.path.join(ROOT, ".tausik", "tausik.db")
    if not os.path.isfile(db):
        pytest.skip("project DB absent — no artifacts to hold an obligation")
    import sqlite3

    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        tc_tables = sorted(t for t in tables if t == "test_cases" or t.startswith("tc_"))
        spec_docs = conn.execute("SELECT COUNT(*) FROM specs WHERE type='DOC'").fetchone()[0]
    finally:
        conn.close()

    assert not tc_tables, (
        "TC now exists as an artifact class "
        f"({tc_tables}) — TC.environment-ref on SPEC-TEST stops being vacuous. "
        "See adr-013-conditional-obligations-expire-when-subject-appears."
    )
    assert spec_docs == 0, (
        f"{spec_docs} SPEC-DOC artifact(s) exist — the doc-lint obligation is now "
        "live and docs_lint.py is warning-only and unbound. See "
        "adr-013-conditional-obligations-expire-when-subject-appears."
    )
