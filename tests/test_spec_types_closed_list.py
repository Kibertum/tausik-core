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

import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from conftest import canonical_schema_db  # noqa: E402

from closed_list_counts import SPEC_TYPE_LIST, scan_tree  # noqa: E402
from closed_list_counts import sources as _sources  # noqa: E402
from closed_list_counts import written_counts as _written_counts  # noqa: E402
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
# THE MATCHER NOW LIVES IN tests/closed_list_counts.py, parameterised by subject.
# It moved there when the ADAPT backward-finding categories turned out to need
# exactly the same guard: a second matcher written for them would have been the
# defect THIS FILE EXISTS TO CATCH, one level up — a second literal copy, free
# to drift from the first. What stays here is the SPEC list's own declared
# exceptions and its fixtures.
#
# What stood here before matched the literal phrase "closed list of N", so it
# read a FORMULATION and not a property, and five sentences saying the same
# thing in other words walked straight past it (memory #488).
#
# LIST_RE above is STILL SPEC-only, and deliberately so. The ADAPT categories
# carry that defect too — their list is in three literal copies — but that is
# adapt-category-list-lives-in-three-literal-copies, a task of its own size.
# Generalising LIST_RE here would drag that work into this change silently,
# which is exactly what splitting the count matcher out was meant to avoid.

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
    "tests/closed_list_counts.py": "the matcher's own explanation of the forms",
    "tests/test_adapts.py": (
        "the ADAPT guard's fixtures — counts of the OTHER closed list, held "
        "there on purpose. Symmetric: this file is likewise declared in that "
        "guard's ALLOWED_ADAPT_COUNTS. Neither is a live claim about SPEC types."
    ),
}


def written_counts(text: str) -> list[str]:
    """The shared matcher, bound to this file's subject."""
    return _written_counts(text, SPEC_TYPE_LIST)


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
    offenders = scan_tree(SPEC_TYPE_LIST, ALLOWED_WRITTEN_COUNTS)
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

    WHAT THIS TEST USED TO DO, AND WHY IT WAS CHANGED. It looked for a table
    named `test_cases` or prefixed `tc_`, and claimed that reddened "the moment
    either subject appears". A mutation showed otherwise: a table `spec_tests`
    carrying `assertion_ref`, `polarity` and `environment_ref`, with a row in it,
    left this test GREEN. The cut was a guess at two names; the promise was about
    a subject. Convention #495 — an announced boundary is measured, not reasoned.

    The premise now has ONE measurer (scripts/renar_tc_premise), read by this
    test and by the manifest clause that rests on the same premise. A third
    consumer imports it rather than cutting again.
    """
    # WHERE THE DECLARATION IS READ FROM, AND WHY IT MOVED. This used to open
    # `.tausik/tausik.db` and skip when it was absent — which is every checkout,
    # CI included, since `bootstrap.py` does not create it. The manifest names
    # this test as the reason its `tc-pos-neg-pairing` true is safe, so the
    # evidence behind a published claim ran only on a developer's machine.
    #
    # `init_schema` is the canonical answer to "which classes does this project
    # declare": it is what a real `tausik init` runs, it comes from git, and it
    # carries no residue. Measured before the swap, not assumed — the live
    # database and the canonical schema yielded the SAME 30 artifact classes,
    # with nothing extra on either side. See `conftest.canonical_schema_db`.
    from renar_tc_premise import classes_appeared, tc_evidence

    conn = canonical_schema_db()
    try:
        evidence = tc_evidence(conn)
        appeared = classes_appeared(conn)
    finally:
        conn.close()

    # The class ratchet has exactly one consumer, and this is it. The manifest
    # clause cannot carry it: it is generated from whatever database it is given,
    # and the declaration is about THIS one.
    assert not appeared, (
        f"artifact class(es) absent when TC was declared absent have appeared: "
        f"{', '.join(appeared)}. Is any of them a TC? If so, §13.3.5 pos/neg pairing "
        "and ADR-013's TC.environment-ref duty are both live and neither has an "
        "executor. If not, say so and add the name to CLASSES_AT_DECLARATION in "
        "scripts/renar_tc_premise.py. See "
        "adr-013-conditional-obligations-expire-when-subject-appears."
    )
    assert not evidence, (
        "ADR-013's conditional obligations are no longer vacuous:\n  - "
        + "\n  - ".join(evidence)
        + "\nTwo declarations expire together here — this one and the manifest's "
        "tc-pos-neg-pairing, which is derived from the same measurer and has "
        "just started publishing `false`. See "
        "adr-013-conditional-obligations-expire-when-subject-appears."
    )
