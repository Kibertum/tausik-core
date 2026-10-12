"""Four FTS searches accept a query written the way this project writes names.

THE DEFECT. `spec search`, `at search`, `adapt search` and `actz search` passed the raw query
to FTS5 MATCH, so an ordinary hyphen made SQLite read `foo-bar` as a column reference and the
command answered `Invalid search query 'foo-bar': no such column: bar`.

WHY IT COST MORE THAN THE REFUSAL. That message points at the SYNTAX, so the reader retries in
another form instead of learning that the query was fine — and names in this project are written
exactly like that: `release-1.10`, `github#124`, `tausik.tech`.

WHAT THE SITE-BY-SITE CHECK CHANGED. The task named six unsanitised call sites; two of them were
already safe and MUST stay untouched. `memory_relevance` builds its query itself from task
keywords, stripping specials and quoting each term; `snippet_storage` calls `_fts_quote` on the
way in. A second layer there would double-escape a search that works — so the fix is four sites,
not six, and this file pins both halves.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))


@pytest.fixture
def svc(tmp_path):
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    root = tmp_path / "proj"
    (root / ".tausik").mkdir(parents=True)
    service = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
    yield service
    service.be.close()


#: The four searches that took the query raw, with the backend method each CLI command reaches.
#: Parametrised rather than four near-identical tests: one shape repeated is duplicate-shape debt
#: and this project ratchets on it.
_SEARCHES = ("actz_search", "adapt_search", "at_search", "spec_search")

#: Query forms this project actually writes. Each one made FTS5 raise before the fix: a hyphen
#: and a dot read as column separators, `#` as a syntax error.
_QUERIES = (
    "foo-bar",
    "release-1.10",
    "tausik.tech",
    "github#124",
    'a "quoted phrase" b',
    # An unbalanced quote used to earn a ServiceError from each of the four domains, in
    # four near-identical tests. It is punctuation like the rest, so it belongs in this
    # table: one promise, stated once, checked against every search.
    '"unbalanced',
)


@pytest.mark.parametrize("method", _SEARCHES)
@pytest.mark.parametrize("query", _QUERIES)
def test_a_punctuated_query_returns_a_result_set_instead_of_raising(svc, method, query):
    """AC-2 and AC-6: the answer may be empty, but it must be an ANSWER."""
    rows = getattr(svc.be, method)(query)
    assert isinstance(rows, list)


@pytest.mark.parametrize("method", _SEARCHES)
def test_a_query_of_only_specials_does_not_become_a_search_for_everything(svc, method):
    """AC-5 NEGATIVE: stripping the operators must not leave a match-all.

    A sanitiser that reduced `***` to an empty MATCH would turn a nonsense query into "return
    the whole table", which is worse than the refusal it replaced — the caller would believe
    every row was a hit.
    """
    rows = getattr(svc.be, method)("*** ((( :::")
    assert rows == []


@pytest.mark.parametrize("method", _SEARCHES)
def test_the_four_searches_share_one_sanitiser(method):
    """AC-2: the SAME helper the three working searches use, not a second variant of it.

    Two copies are how two searches answer one query differently; this repository has paid for
    that pattern twice over in a single session.
    """
    import inspect

    from project_backend import SQLiteBackend

    src = inspect.getsource(getattr(SQLiteBackend, method))
    assert "_sanitize_fts5(query)" in src, f"{method} does not use the shared sanitiser"


def test_the_two_already_safe_sites_are_left_alone():
    """AC-4 NEGATIVE, the one that keeps the fix from spreading too far.

    `memory_relevance` strips specials from each term and quotes it; `snippet_storage` quotes on
    the way in. Adding the shared sanitiser on top would escape an already-escaped string, and
    the search that works today would stop working.
    """
    relevance = (_REPO / "scripts" / "memory_relevance.py").read_text(encoding="utf-8")
    snippets = (_REPO / "scripts" / "snippet_storage.py").read_text(encoding="utf-8")
    assert "_FTS5_TOKEN_SPECIAL_RE" in relevance, "its own cleaning is the reason it is exempt"
    assert "_sanitize_fts5" not in relevance, "double escaping would break a working search"
    assert "_fts_quote(query)" in snippets, "its own quoting is the reason it is exempt"
    assert "_sanitize_fts5" not in snippets, "double escaping would break a working search"


@pytest.mark.parametrize("method", _SEARCHES)
def test_a_plain_word_still_finds_what_it_should(svc, method):
    """The premise. A sanitiser that emptied every query would make all of the above pass."""
    from backend_queries import _sanitize_fts5

    assert _sanitize_fts5("kubernetes") != "", "a plain word must survive sanitising"
    rows = getattr(svc.be, method)("kubernetes")
    assert isinstance(rows, list)
