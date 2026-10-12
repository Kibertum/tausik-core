"""An owner's prohibition is read where the action happens, or it does not exist.

THE MEASUREMENT. The owner said CI was not wanted until the release approached. Twenty-three
commits followed, each with a push and therefore a pipeline — 23 to nothing in favour of the
ritual. The cause is structural: the framework's rules are GATED (verify blocks a close, the
changelog blocks a close, push-ok is built into the commit ritual) while an owner's instruction
blocks nothing and is read by nothing. When the two diverge, the one that stops things wins.

WHY THE MARKER IS EXACT. Over 399 decisions, a keyword search for a prohibition returns five, of
which three are about a hard gate, a scanner and a story being added. Forty percent precision is
a coin, and a detector that cries wolf teaches the reader to switch the signal off — which is the
same death the instruction already died.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from owner_constraints import Ban, active_bans, advisory, parse  # noqa: E402


@pytest.mark.parametrize(
    "text,expected,why",
    [
        (
            "ЗАПРЕТ ВЛАДЕЛЬЦА [ci]: CI не трогаем до релиза",
            (("ci",), "CI не трогаем до релиза"),
            "the declared form, in Russian",
        ),
        (
            "OWNER BAN [network, push]: no pushes to the public remote",
            (("network", "push"), "no pushes to the public remote"),
            "the declared form, in English, with two tags",
        ),
        (
            "CI НЕ трогаем до подхода к релизу — указание владельца",
            None,
            "AC-6: prose is not a declaration. On this corpus that reading was right two "
            "times out of five, and a detector at 40% teaches the reader to ignore it",
        ),
        (
            "ЗАПРЕТ ВЛАДЕЛЬЦА: без тегов",
            None,
            "a ban with no tag matches no action point, so it is not a usable declaration",
        ),
        ("", None, "nothing is not a prohibition"),
    ],
)
def test_only_the_declared_form_counts(text, expected, why):
    assert parse(text) == expected, why


@pytest.fixture
def db(tmp_path):
    # The CANONICAL DDL, not a copy of it. A hand-written schema in a test drifts from the real
    # one silently, and then the test passes against a table the product does not have — which is
    # the whole reason `canonical_ddl` exists.
    from conftest import canonical_ddl

    conn = sqlite3.connect(":memory:")
    conn.executescript(canonical_ddl("decisions"))
    conn.executescript(canonical_ddl("memory_edges"))
    rows = [
        (1, "ЗАПРЕТ ВЛАДЕЛЬЦА [ci]: no pipelines before the release", "2026-01-01"),
        (2, "Обычное решение про архитектуру, где есть слово не", "2026-01-02"),
        (3, "OWNER BAN [network]: nothing leaves the machine", "2026-01-03"),
        (4, "ЗАПРЕТ ВЛАДЕЛЬЦА [ci]: an older ban that was later lifted", "2026-01-04"),
    ]
    conn.executemany("INSERT INTO decisions (id, decision, created_at) VALUES (?,?,?)", rows)
    conn.execute(
        "INSERT INTO memory_edges (id, relation, source_type, source_id, target_type, "
        "target_id, valid_from, valid_to, created_at) "
        "VALUES (1,'supersedes','decision',1,'decision',4,'2026-01-05',NULL,'2026-01-05')"
    )
    yield conn
    conn.close()


def test_a_prohibition_in_force_is_found(db):
    assert {b.id for b in active_bans(db)} == {1, 3}


#: What must NOT be reported, with the reason each exclusion exists. A table rather than a test
#: apiece: both read the same set and assert an absence, which is one shape twice — the dedupe
#: ratchet counts that, and it is right to.
_EXCLUDED = (
    (
        4,
        "AC-7: a constraint the owner withdrew must go silent. A signal that keeps firing after "
        "its reason is gone is noise, and noise is switched off — exactly how the instruction "
        "died the first time",
    ),
    (
        2,
        "AC-6 at the corpus level rather than the parser's: an ordinary decision that happens to "
        "contain a negation is not a prohibition",
    ),
)


@pytest.mark.parametrize("decision_id,why", _EXCLUDED)
def test_what_must_not_be_reported(db, decision_id, why):
    assert decision_id not in {b.id for b in active_bans(db)}, why


def test_the_tag_selects_without_reading_prose(db):
    """AC-3: an action point asks for its own tag and gets only what covers it."""
    assert [b.id for b in active_bans(db, "ci")] == [1]
    assert [b.id for b in active_bans(db, "network")] == [3]
    assert active_bans(db, "deployment") == []


def test_the_query_filters_in_sql_rather_than_in_python(db):
    """AC-3's other half: the cost must not scale with the corpus.

    399 decisions parsed on every commit would be a price paid per action, and a check that
    costs something every time is a check somebody eventually removes.
    """
    from owner_constraints import _SQL

    assert "LIKE" in _SQL and "decisions" in _SQL
    fetched = db.execute(_SQL).fetchall()
    assert len(fetched) == 2, "SQL already excludes the ordinary decision and the lifted ban"


def test_the_advisory_says_it_is_a_signal(db):
    """AC-5: a block here would be argued with and then switched off."""
    text = advisory(active_bans(db))
    assert "СИГНАЛ, не ворота" in text
    assert "#1" in text and "#3" in text, (
        "each line names its decision, so lifting it has an address"
    )


def test_nothing_in_force_prints_nothing():
    """Silence is the normal state; a line earns its place only when something is in force."""
    assert advisory([]) == ""


def test_covers_is_case_insensitive():
    assert Ban(1, ("ci",), "x").covers("CI")
    assert not Ban(1, ("ci",), "x").covers("network")
