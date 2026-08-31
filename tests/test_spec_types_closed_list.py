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
# Scoped to SPEC on purpose. The same pattern fires on the ADAPT backward-finding
# categories ("CLOSED list of 7" in service_adapts.py / tools_adapt.py) — the
# identical defect, currently with a correct number. That is filed as
# adapt-finding-categories-count-is-written-not-derived, which GENERALISES this
# detector rather than copying it. Fixing it here would widen this task silently.
COUNT_RE = re.compile(r"(?i)closed list of\s+(\d+)\s+(?:RENAR\s+)?(?:SPEC|types?)")


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
        if rel == "tests/test_spec_types_closed_list.py":
            continue
        for m in COUNT_RE.finditer(src):
            offenders.append(f"{rel}: {m.group(0)!r}")
    assert not offenders, (
        "the count of SPEC types must be formatted from len(SPEC_TYPES), never "
        f"written beside the list: {offenders}"
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
