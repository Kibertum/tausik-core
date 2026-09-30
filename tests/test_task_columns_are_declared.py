"""Every `tasks` column is either carried by the tree or declared non-portable with a reason.

WHY THIS TEST HAD TO EXIST. `tests/test_state_roundtrip_gate.py` re-serialises the database and
compares the result with the committed tree byte for byte — but BOTH sides of that comparison
come from the same exporter, so a column it never selects cannot appear on either side. The gate
is green for any number of forgotten fields, and always will be. It is not a weak check; it is a
check that structurally cannot see this class of defect, which is the same shape as the rule
about an end-to-end corpus: comparing generated with generated proves only that the generator is
deterministic.

WHAT THE MEASUREMENT FOUND. 46 columns, of which 23 never reached the tree — three times what
the task statement estimated. A ticket link, the models that opened and closed a task (evidence
of separation of duties), a declaration that a close touched no files, and two of the three
budgets were all lost on a clone while the third budget travelled.

SO THE FIX IS NOT "ADD THE FIELDS". It is a partition that must cover the table: the next new
column fails this test until somebody decides which side it belongs on. Adding fields without
that would leave the next one to be forgotten just as quietly.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from state_export import NOT_PORTABLE  # noqa: E402


def _schema_columns() -> set[str]:
    """The columns of `tasks` in a FRESH database, not in this machine's copy.

    Reading the live database would make the test describe one developer's file rather than
    the schema every consumer gets.
    """
    from backend_init import init_schema

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    conn.close()
    return cols


def _exported_columns() -> set[str]:
    """What the DOCUMENT carries, read from the source.

    Carried by the tree means "written into the file", not "named in the SELECT": `id` and
    `story_id` are fetched as machinery — one joins the journal, the other resolves the story
    slug — and never reach a frontmatter key. Reading the query instead put both columns on
    two sides of the partition at once, which is how this distinction got noticed.

    From the SOURCE rather than a list kept beside it: a second copy of the answer is how the
    check and the code drift into two truths, which this repository has paid for twice.
    """
    src = (_REPO / "scripts" / "state_export.py").read_text(encoding="utf-8")
    m = re.search(r"def _task_doc\(.*?return render_file\(pairs, body\)", src, re.S)
    assert m, "the task document builder moved — this test reads it from the source on purpose"
    # The WHOLE builder, not just its frontmatter pairs: goal, acceptance criteria, plan and
    # rollback are carried in the BODY, and a reader that stopped at the pairs list called
    # four fields lost that the tree has always had.
    return set(re.findall(r'task(?:\.get\(|\[)"([\w_]+)"', m.group(0)))


def test_the_two_lists_cover_the_table():
    """AC-3: a new column fails here until its side is decided."""
    uncovered = _schema_columns() - _exported_columns() - set(NOT_PORTABLE)
    assert not uncovered, (
        "these `tasks` columns are neither exported nor declared non-portable: "
        + ", ".join(sorted(uncovered))
        + ". Add the field to the projection, or to NOT_PORTABLE with the reason it is "
        "telemetry or an internal key rather than intent."
    )


def test_nothing_is_declared_on_both_sides():
    """A column in both lists means the declaration no longer describes the code."""
    both = _exported_columns() & set(NOT_PORTABLE)
    assert not both, f"exported AND declared non-portable: {sorted(both)}"


def test_no_declaration_names_a_column_that_is_gone():
    """A reason for a column nobody has is a note about a table that no longer exists."""
    stale = set(NOT_PORTABLE) - _schema_columns()
    assert not stale, f"NOT_PORTABLE names columns the schema does not have: {sorted(stale)}"


@pytest.mark.parametrize("column,reason", sorted(NOT_PORTABLE.items()))
def test_every_reason_says_something(column, reason):
    """AC-2: the reason is the point. Without it the list is a way to silence this test.

    A short string would let the next column be waved through with "internal", which is the
    same silence in a tidier form.
    """
    assert len(reason) > 30, f"{column}: {reason!r} is too short to be a reason"


@pytest.mark.parametrize(
    "column",
    [
        "tracker_refs",
        "started_model_id",
        "done_model_id",
        "model_mismatch",
        "no_file_changes_declared",
        "token_budget",
        "cost_budget_usd",
    ],
)
def test_the_fields_that_carry_intent_travel(column):
    """AC-4: these were lost on a clone, and each one is intent rather than telemetry.

    The ticket link is the only address an outside reader has; the model pair is the evidence
    a reviewer needs for separation of duties; a no-file-changes close is a declaration the
    contract says is countable; and two budgets travelling while the third did not was the
    asymmetry that gave the defect away.
    """
    assert column in _exported_columns(), f"{column} still does not reach the tree"


def test_the_reader_of_the_select_can_still_fail():
    """The premise. If the regex stopped matching, every test above would pass vacuously
    while the exporter selected nothing at all."""
    exported = _exported_columns()
    assert "slug" in exported and "status" in exported
    assert len(exported) > 20, f"only {len(exported)} columns parsed — the reader broke"
