"""Tests for scripts/eval_memory_retrieval.py (km-retrieval-baseline-eval).

AC coverage:
  1/2. the harness produces a single reproducible accuracy number.
  3.  the score depends on CONTENT, not record ids (survives an id shift).
  4.  fail-safe: empty/broken store → 0.0, never a crash; a query with no
      matching content is a miss, not an error.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import eval_memory_retrieval as emr  # noqa: E402
from eval_memory_retrieval import QUESTIONS, _hit, evaluate  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402

# A tiny question set with a distinctive latin marker so FTS retrieval is
# language-independent and deterministic in the test.
_Q = [
    ("what is the fail-open rule?", "fail-open scoping", ["fail-open"]),
    ("what about widget-xyz?", "widget-xyz missing", ["widget-xyz"]),  # never inserted → miss
]


def _seed(be, *, decoys=0):
    for i in range(decoys):
        be.memory_add("context", f"decoy {i}", f"unrelated filler number {i}")
    be.memory_add("pattern", "Scoping is fail-open", "The MCP surface is fail-open by design.")


def test_single_accuracy_number(tmp_path):
    be = SQLiteBackend(str(tmp_path / "m.db"))
    _seed(be)
    report = evaluate(be, questions=_Q)
    assert report["total"] == 2
    assert report["hits"] == 1  # fail-open present, widget-xyz absent
    assert report["accuracy"] == 0.5


def test_deterministic(tmp_path):
    be = SQLiteBackend(str(tmp_path / "m.db"))
    _seed(be)
    assert evaluate(be, questions=_Q) == evaluate(be, questions=_Q)


def test_id_independent(tmp_path):
    """Same content, different ids (decoys inserted first) → same accuracy."""
    be1 = SQLiteBackend(str(tmp_path / "a.db"))
    _seed(be1, decoys=0)
    be2 = SQLiteBackend(str(tmp_path / "b.db"))
    _seed(be2, decoys=5)  # the fail-open entry now has a higher id
    assert evaluate(be1, questions=_Q)["accuracy"] == evaluate(be2, questions=_Q)["accuracy"]


def test_empty_store_is_zero_not_crash(tmp_path):
    be = SQLiteBackend(str(tmp_path / "empty.db"))
    report = evaluate(be, questions=_Q)
    assert report["accuracy"] == 0.0
    assert report["hits"] == 0


def test_committed_set_runs_without_error_on_empty_store(tmp_path):
    """The real 49-question set must execute end-to-end (no crash) even when
    nothing matches — proves query robustness against the FTS sanitizer."""
    be = SQLiteBackend(str(tmp_path / "empty.db"))
    report = evaluate(be, questions=QUESTIONS)
    assert report["total"] == len(QUESTIONS) >= 45
    assert report["accuracy"] == 0.0  # empty store → every question misses


def test_marker_matching_is_case_insensitive(tmp_path):
    be = SQLiteBackend(str(tmp_path / "m.db"))
    be.memory_add("pattern", "FAIL-OPEN policy", "Everything is FAIL-OPEN here.")
    report = evaluate(be, questions=[("q", "fail-open policy", ["fail-open"])])
    assert report["accuracy"] == 1.0


def test_marker_boundary_rejects_substring_in_number():
    """Review fix: '400' must NOT match inside '24000' (token-start anchor)."""
    assert (
        _hit([{"title": "x", "content": "counter jumped to 24000 after retries"}], ["400"], 5)
        is False
    )
    assert _hit([{"title": "filesize gate", "content": "files over 400 lines"}], ["400"], 5) is True


def test_marker_prefix_still_matches_inflected_word():
    """Prefix markers (Russian stems) must still match a longer inflected word."""
    assert (
        _hit([{"title": "t", "content": "тест-пин на ЗАКРЕПЛЕНИЕ дыры"}], ["закреплен"], 5) is True
    )


def test_missing_db_is_failsafe(tmp_path, capsys):
    """Review fix: a typo'd --db is reported, not silently created as a fresh store."""
    missing = str(tmp_path / "nope" / "x.db")
    rc = emr.main(["--db", missing])
    assert rc == 0
    assert "DB unavailable" in capsys.readouterr().out
    assert not os.path.exists(missing)  # not auto-created
