"""Search finds a record whatever the case and number of the word (github#124).

Measured before: «задача» 565, «задачи» 665, «задачам» 27 — each form found only
itself. After: 900 for all three. A trailing `*` is kept; every other operator
use is still neutralised.
"""

from __future__ import annotations

import pytest

from backend_queries import _sanitize_fts5
from fts_morphology import expand, stem
from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.mark.parametrize(
    "word, base",
    [
        ("гейтами", "гейт"),
        ("задачам", "задач"),
        ("калибровкой", "калибровк"),
        ("сессиями", "сесси"),
    ],
)
def test_stem_drops_the_ending_and_keeps_four_letters(word, base):
    assert stem(word) == base


def test_short_and_latin_tokens_are_left_alone():
    assert expand("гейт") == "гейт" and expand("verify") == "verify"


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "m.db")))
    s.memory_add("gotcha", "калибровка окна", "Калибровка по десяти задачам дрожит.")
    yield s
    s.be.close()


@pytest.mark.parametrize("query", ["калибровкой", "калибровки", "задача", "калибр*"])
def test_another_word_form_finds_the_record(svc, query):
    assert svc.be.memory_search(query), query


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("гейт*", "гейт*", id="trailing-star-kept"),
        pytest.param("a*b", "a AND b", id="star-in-the-middle"),
        pytest.param("*", "", id="lone-star"),
        pytest.param('"unpaired', "unpaired", id="unpaired-quote"),
        pytest.param("foo AND bar", "foo AND bar", id="operator"),
    ],
)
def test_only_a_trailing_star_survives_the_sanitizer(query, expected):
    """NEGATIVE: keeping a trailing star opens no path to syntax errors.

    The `operator` case reads oddly and is correct: the user's `AND` is stripped
    as an operator, then the sanitizer conjoins the two remaining terms with its
    own. Same string, different author -- and the user can no longer choose `OR`.
    """
    assert _sanitize_fts5(query) == expected


def test_a_hostile_query_does_not_crash_the_search(svc):
    for q in ["a*b", "*", '"x', "NEAR(", "калибровк* OR"]:
        svc.be.memory_search(q)
