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


def test_plain_query_unchanged():
    assert _sanitize_fts5("hello world") == "hello world"


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


def test_fts5_boolean_operators_stripped():
    # The bare AND / OR / NOT keywords must not survive — they would
    # otherwise act as FTS5 operators on neighboring tokens.
    out = _sanitize_fts5("alpha AND beta OR gamma NOT delta NEAR epsilon")
    assert "AND" not in out
    assert "OR" not in out
    assert "NOT" not in out
    assert "NEAR" not in out
    for word in ("alpha", "beta", "gamma", "delta", "epsilon"):
        assert word in out


def test_paren_star_colon_caret_stripped():
    out = _sanitize_fts5("(foo) bar* baz:qux ^heading")
    assert "(" not in out
    assert ")" not in out
    assert "*" not in out
    assert ":" not in out
    assert "^" not in out
    for word in ("foo", "bar", "baz", "qux", "heading"):
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
