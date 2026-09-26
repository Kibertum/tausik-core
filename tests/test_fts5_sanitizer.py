"""FTS5 query sanitizer — covers the dot / hyphen / slash regression
(bug-tausik-search-fts5-syntax-error-on-dot, v1.4.1).

The previous sanitizer stripped `(`, `)`, `*`, `:`, `^` but left `.`
through; FTS5 treats `.` as a column separator and raised
`syntax error near "."` for any query like `tausik.tech`. The fix
wraps such tokens in phrase quotes so FTS5 routes them through the
tokenizer instead of the syntax parser.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from backend_queries import _sanitize_fts5  # noqa: E402


# --- Unit tests on the sanitizer output -------------------------------------


def test_plain_query_keeps_both_words_and_joins_them_with_and():
    """Two bare words mean both words, and the conjunction is now spelled out.

    A space and an explicit `AND` are the same operator in FTS5 for two tokens.
    The spelling changed because a space is NOT an operator between a token and a
    parenthesised group, which is what the morphology expander produces.
    """
    assert _sanitize_fts5("hello world") == "hello AND world"


def test_empty_query():
    assert _sanitize_fts5("") == ""
    assert _sanitize_fts5("   ") == ""


def test_dot_in_token_is_quoted():
    # The regression: `tausik.tech site` must not produce a bare `tausik.tech`.
    out = _sanitize_fts5("tausik.tech site")
    assert '"tausik tech"' in out
    assert "site" in out


def test_hyphen_in_token_is_quoted():
    out = _sanitize_fts5("foo-bar baz")
    assert '"foo bar"' in out
    assert "baz" in out


def test_slash_in_token_is_quoted():
    out = _sanitize_fts5("a/b/c")
    assert '"a b c"' in out


def test_trailing_dot_is_trimmed():
    # `foo.` with nothing after the dot collapses to a single bare token.
    out = _sanitize_fts5("foo.")
    assert "foo" in out
    assert "." not in out


def test_quoted_phrase_passthrough():
    out = _sanitize_fts5('"exact phrase"')
    assert '"exact phrase"' in out


def test_fts5_boolean_operators_the_user_typed_do_not_survive_as_typed():
    """The user's own operators are stripped; the sanitizer's own AND is not.

    The point was never that the string lacks the letters A-N-D -- it is that the
    user cannot choose the operator. `OR`, `NOT` and `NEAR` disappear entirely,
    and every term is conjoined, so the query means "all of these words" whatever
    the user typed between them.
    """
    out = _sanitize_fts5("alpha AND beta OR gamma NOT delta NEAR epsilon")
    assert "OR" not in out
    assert "NOT" not in out
    assert "NEAR" not in out
    assert out == "alpha AND beta AND gamma AND delta AND epsilon"
    assert "NEAR" not in out
    for word in ("alpha", "beta", "gamma", "delta", "epsilon"):
        assert word in out


def test_paren_star_colon_caret_stripped():
    # A star INSIDE a token is stripped; a trailing one is a prefix query since
    # 1.10 (search-has-no-morphology-and-strips-the-wildcard), pinned below.
    out = _sanitize_fts5("(foo) b*ar baz:qux ^heading")
    assert "(" not in out
    assert ")" not in out
    assert "*" not in out
    assert ":" not in out
    assert "^" not in out
    for word in ("foo", "b", "ar", "baz", "qux", "heading"):
        assert word in out


def test_mixed_phrases_and_tokens():
    out = _sanitize_fts5('"keep this" a.b plain')
    assert '"keep this"' in out
    assert '"a b"' in out
    assert "plain" in out


def test_at_and_hash_are_quoted():
    out = _sanitize_fts5("user@example github#42")
    assert '"user example"' in out
    assert '"github 42"' in out


# --- End-to-end test: real FTS5 table must not raise on the sanitized query


@pytest.fixture()
def fts_conn():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE VIRTUAL TABLE fts USING fts5(body);
        INSERT INTO fts(body) VALUES
          ('tausik tech is a framework'),
          ('the foo bar baz example'),
          ('something else entirely');
        """
    )
    yield conn
    conn.close()


@pytest.mark.parametrize(
    "raw_query",
    [
        "tausik.tech",
        "foo-bar",
        "a.b.c",
        "tausik.tech site",
        "(complicated)",
        "alpha AND beta",
        "user@example",
        "foo.",
        ".",
        "   ",
    ],
)
def test_real_fts5_match_never_raises(fts_conn: sqlite3.Connection, raw_query: str):
    sanitized = _sanitize_fts5(raw_query)
    if not sanitized:
        # Empty sanitized output means caller short-circuits — nothing to run.
        return
    # Should not raise sqlite3.OperationalError("fts5: syntax error ...").
    fts_conn.execute("SELECT body FROM fts WHERE fts MATCH ?", (sanitized,)).fetchall()


def test_real_fts5_dot_query_returns_expected_row(fts_conn: sqlite3.Connection):
    sanitized = _sanitize_fts5("tausik.tech")
    rows = fts_conn.execute("SELECT body FROM fts WHERE fts MATCH ?", (sanitized,)).fetchall()
    bodies = [r[0] for r in rows]
    assert any("tausik" in b and "tech" in b for b in bodies)


# --- The corpus above is all-Latin or single-token, and that is what let the
# --- morphology feature ship a query FTS5 refuses to parse.


@pytest.fixture()
def cyr_conn():
    """A Cyrillic corpus, because the Latin one cannot reach the expander.

    `fts_morphology.expand` only touches Cyrillic tokens of five letters or more.
    Every query in `test_real_fts5_match_never_raises` above is Latin or a single
    word, so the shape the expander produces -- a parenthesised group standing
    beside another token -- was never executed against a real table.
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE VIRTUAL TABLE fts USING fts5(body);
        INSERT INTO fts(body) VALUES
          ('калибровка по десяти задачам дрожит'),
          ('редеплой профилей перед закрытием задачи'),
          ('bootstrap_drift сравнивает развёрнутые копии');
        """
    )
    yield conn
    conn.close()


@pytest.mark.parametrize(
    "raw_query",
    [
        pytest.param("bootstrap_drift редеплой", id="latin_token_then_group"),
        pytest.param("редеплой bootstrap_drift", id="group_then_latin_token"),
        pytest.param("калибровка задачам", id="group_beside_group"),
        pytest.param("калибровка задачам дрожит", id="three_groups"),
        pytest.param("калибровка гейт*", id="group_and_prefix"),
        pytest.param('калибровка "по десяти"', id="group_and_phrase"),
        pytest.param("калибровка tausik.tech", id="group_and_wrapped_token"),
        pytest.param("калибровка по", id="group_and_short_word"),
    ],
)
def test_a_two_word_query_is_parseable_by_fts5(cyr_conn: sqlite3.Connection, raw_query: str):
    """FTS5 has no implicit AND between a token and a parenthesised group.

    `a b` is a valid query and `(a OR b*)` is a valid query, but `a (b OR c*)` is
    a syntax error -- so joining the sanitizer's parts with a space produced an
    unparseable query the moment one word expanded and another token stood beside
    it. That is most Russian two-word queries, and it reached the user as a
    twelve-frame traceback out of `memory search`.
    """
    sanitized = _sanitize_fts5(raw_query)
    assert sanitized, raw_query
    cyr_conn.execute("SELECT body FROM fts WHERE fts MATCH ?", (sanitized,)).fetchall()


def test_a_two_word_query_still_finds_the_record(cyr_conn: sqlite3.Connection):
    """Parseable is not enough: the query has to mean AND, not OR.

    Joining with `OR` would also parse and would return every row for any word,
    which is worse than a crash -- a search that answers everything is a search
    nobody can use.
    """
    sanitized = _sanitize_fts5("калибровкой задачам")
    rows = cyr_conn.execute("SELECT body FROM fts WHERE fts MATCH ?", (sanitized,)).fetchall()
    assert [r[0] for r in rows] == ["калибровка по десяти задачам дрожит"]


def test_no_atom_pairing_reaches_a_syntax_error(cyr_conn: sqlite3.Connection):
    """Every pair of query atoms parses, which is the claim the eight cases sample.

    The parametrised cases above name the shapes a reader should recognise. This
    one asks the question exhaustively over pairs, because the bug being fixed was
    precisely a combination nobody thought to write down: the expander's output had
    a test, the neighbouring token had a test, the two together had none.

    Pairs, not longer tuples: a syntax error needs only two adjacent parts to show
    itself, and the full run over triples and quadruples (8676 combinations, zero
    failures) is recorded in the task journal rather than paid for on every suite.
    """
    atoms = [
        "калибровка",
        "задачам",
        "гейт*",
        "bootstrap_drift",
        "tausik.tech",
        "foo-bar",
        '"по десяти"',
        "AND",
        "OR",
        "NEAR",
        "(",
        "*",
        "#7",
        "по",
        "a*b",
        "github#124",
    ]
    failures = []
    for left in atoms:
        for right in atoms:
            sanitized = _sanitize_fts5(f"{left} {right}")
            if not sanitized:
                continue
            try:
                cyr_conn.execute("SELECT body FROM fts WHERE fts MATCH ?", (sanitized,)).fetchall()
            except sqlite3.OperationalError as exc:
                failures.append((left, right, sanitized, str(exc)))
    assert failures == [], failures[:5]
