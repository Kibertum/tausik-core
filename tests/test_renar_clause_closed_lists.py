"""§13.3.4 / §13.3.7 closed lists — measured, with a red branch per sub-check.

Each violating state below is one the task's measurement table proved the old
literal `True` could not see. The fixtures rebuild a table with a different
CHECK (SQLite cannot alter a constraint in place), so the DDL the parser reads
is the one a migration would have written.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from renar_clause_closed_lists import (  # noqa: E402
    assess_closed_lists,
    assess_spec_types,
    check_domain,
)
from service_adapts import ADAPT_STATUSES, FINDING_CATEGORIES  # noqa: E402
from service_specs import SPEC_TYPES  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "cl.db")))
    yield s
    s.be.close()


def _rebuild(conn, table: str, old: str, new: str) -> None:
    """Recreate `table` with its stored DDL edited — the only way to change a CHECK."""
    ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (table,)).fetchone()[0]
    assert old in ddl, f"fixture anchor {old!r} not in the DDL of {table}"
    conn.execute(f"DROP TABLE {table}")
    conn.execute(ddl.replace(old, new))
    conn.commit()


def _failed(verdict) -> list[str]:
    return [s["check"] for s in verdict["subchecks"] if not s["ok"]]


# --- the parser --------------------------------------------------------------


def test_check_domain_reads_the_three_closed_lists_off_a_fresh_schema(svc):
    conn = svc.be._conn
    assert check_domain(conn, "specs", "type") == SPEC_TYPES
    assert check_domain(conn, "adapt_findings", "category") == FINDING_CATEGORIES
    assert check_domain(conn, "adapts", "status") == ADAPT_STATUSES


def test_a_value_containing_a_parenthesis_is_read_whole(svc):
    """NEGATIVE SCENARIO, found by review: `[^)]*` stopped at the `)` INSIDE a
    value, truncated the list, and returned an EMPTY tuple — "the CHECK admits
    nothing", a fact, where the truth was "this could not be read"."""
    conn = svc.be._conn
    conn.execute("CREATE TABLE p (type TEXT NOT NULL CHECK(type IN ('FOO(BAR)', 'BAZ')))")
    assert check_domain(conn, "p", "type") == ("FOO(BAR)", "BAZ")


def test_a_doubled_quote_is_one_escaped_quote_not_two_values(svc):
    """NEGATIVE SCENARIO, found by review: `'isn''t'` came back as ('isn', 't')."""
    conn = svc.be._conn
    conn.execute("CREATE TABLE q (type TEXT NOT NULL CHECK(type IN ('isn''t', 'baz')))")
    assert check_domain(conn, "q", "type") == ("isn't", "baz")


def test_a_parenthesis_outside_a_string_does_not_end_the_list_early(svc):
    """The paren-depth branch, reached by the ONLY input that reaches it.

    Written because a declared mutation SURVIVED. Removing the depth counter
    was supposed to be caught by the `'FOO(BAR)'` case above — it is not: that
    parenthesis sits INSIDE a string, so the scanner is in its string branch
    and never consults the depth at all. Depth matters only for a parenthesis
    OUTSIDE a string, which SQL allows in a value list: `(('A'), 'B')`. Without
    the counter the first `)` closes the list and 'B' is silently lost — a
    shorter closed list reported as fact.
    """
    from renar_clause_closed_lists import _values_until_close

    assert _values_until_close("(('A'), 'B')", 1) == ("A", "B")
    conn = svc.be._conn
    conn.execute("CREATE TABLE n (type TEXT NOT NULL CHECK(type IN (('A'), 'B')))")
    assert check_domain(conn, "n", "type") == ("A", "B")


def test_an_unterminated_or_valueless_list_is_unreadable_not_empty(svc):
    """The three-state discipline: nothing parsable is None, never ()."""
    from renar_clause_closed_lists import _values_until_close

    assert _values_until_close("('a', 'b')", 1) == ("a", "b")
    assert _values_until_close("('a', 'b'", 1) is None, "never closed"
    assert _values_until_close("('a", 1) is None, "unterminated string"
    assert _values_until_close("()", 1) is None, "no value is not an empty closed list"


def test_check_domain_is_none_where_there_is_no_check_or_no_table(svc):
    """NEGATIVE: absence is None, never an empty tuple mistaken for a closed empty list."""
    conn = svc.be._conn
    conn.execute("CREATE TABLE open_list (kind TEXT NOT NULL)")
    assert check_domain(conn, "open_list", "kind") is None
    assert check_domain(conn, "no_such_table", "kind") is None
    assert check_domain(conn, "specs", "title") is None, "a column without a CHECK"


# --- §13.3.4 -----------------------------------------------------------------


def test_spec_types_hold_on_a_fresh_schema(svc):
    verdict = assess_spec_types(svc.be._conn)
    assert verdict["confirmed"] is True, verdict
    assert _failed(verdict) == []


def test_a_local_spec_type_admitted_by_the_check_reds_the_substrate_half(svc):
    """NEGATIVE SCENARIO from the measurement table: CHECK admits FOO."""
    conn = svc.be._conn
    _rebuild(conn, "specs", "'DOC'", "'DOC', 'FOO'")
    verdict = assess_spec_types(conn)
    assert verdict["confirmed"] is False
    assert _failed(verdict) == ["spec-types-substrate-closed"]
    assert "FOO" in verdict["subchecks"][0]["evidence"]


def test_a_check_short_of_the_declared_list_reds(svc):
    """NEGATIVE SCENARIO: a CHECK that never learned about DOC."""
    conn = svc.be._conn
    _rebuild(conn, "specs", "'TEST', 'DOC'", "'TEST'")
    verdict = assess_spec_types(conn)
    assert verdict["confirmed"] is False
    assert _failed(verdict) == ["spec-types-substrate-closed"]
    assert "DOC" in verdict["subchecks"][0]["evidence"]


def test_a_row_outside_the_list_reds_the_rows_half(svc):
    """NEGATIVE SCENARIO: data written under an open column."""
    conn = svc.be._conn
    ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name='specs'").fetchone()[0]
    start = ddl.index("CHECK(type IN")
    end = ddl.index("))", start) + 2
    _rebuild(conn, "specs", ddl[start:end], "")
    conn.execute(
        "INSERT INTO specs (slug, type, title, version, status, created_at, updated_at) "
        "VALUES ('x', 'FOO', 'local', '1', 'draft', '2026-01-01', '2026-01-01')"
    )
    conn.commit()
    verdict = assess_spec_types(conn)
    assert verdict["confirmed"] is False
    assert _failed(verdict) == ["spec-types-substrate-closed", "spec-types-rows-inside"]
    assert "1 specs row(s)" in verdict["subchecks"][1]["evidence"]


def test_a_missing_specs_table_is_red_not_a_crash(svc):
    conn = svc.be._conn
    conn.execute("DROP TABLE specs")
    conn.commit()
    verdict = assess_spec_types(conn)
    assert verdict["confirmed"] is False
    assert "cannot be read" in verdict["subchecks"][1]["evidence"]


# --- §13.3.7 -----------------------------------------------------------------


def test_closed_lists_hold_on_a_fresh_schema(svc):
    verdict = assess_closed_lists(svc.be._conn)
    assert verdict["confirmed"] is True, verdict
    assert [s["check"] for s in verdict["subchecks"]] == [
        "backward-findings-substrate-closed",
        "backward-findings-rows-inside",
        "adapt-statuses-substrate-closed",
        "adapt-statuses-rows-inside",
    ]


def test_an_eighth_finding_category_reds(svc):
    """NEGATIVE SCENARIO from the measurement table: CHECK admits `vibes`, and a finding uses it."""
    conn = svc.be._conn
    _rebuild(conn, "adapt_findings", "'scope'", "'scope', 'vibes'")
    svc.adapt_create("ad1", "A", "TZ-1")
    conn.execute(
        "INSERT INTO adapt_findings (adapt_slug, category, description, created_at) "
        "VALUES ('ad1', 'vibes', 'eighth', '2026-01-01')"
    )
    conn.commit()
    verdict = assess_closed_lists(conn)
    assert verdict["confirmed"] is False
    assert _failed(verdict) == [
        "backward-findings-substrate-closed",
        "backward-findings-rows-inside",
    ]


def test_a_local_adapt_status_reds(svc):
    """NEGATIVE SCENARIO from the measurement table: the pre-v50 `signed` re-admitted."""
    conn = svc.be._conn
    _rebuild(conn, "adapts", "'superseded'", "'superseded', 'signed'")
    verdict = assess_closed_lists(conn)
    assert verdict["confirmed"] is False
    assert _failed(verdict) == ["adapt-statuses-substrate-closed"]
    assert "signed" in verdict["subchecks"][2]["evidence"]


def test_the_reactive_adapt_status_domain_reads_through_the_same_parser(svc):
    """One CHECK parser: the private cut in renar_clause_reactive_adapt delegates."""
    from renar_clause_reactive_adapt import _status_domain

    conn = svc.be._conn
    assert _status_domain(conn) == ADAPT_STATUSES
    _rebuild(conn, "adapts", "'superseded'", "'superseded', 'signed'")
    assert _status_domain(conn) == (*ADAPT_STATUSES, "signed")
