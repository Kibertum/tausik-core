"""Soft-delete is only soft if something can undo it, and for two releases nothing could.

THE MEASUREMENT THAT FILED THIS. `docs/{en,ru}/task-archive-spec.md` called task archival
a soft-delete and a task's Rollback line called it "reversible by command". A grep for a
path that clears `archived_at` across `scripts/`, `harness/` and `docs/` returned ZERO: 25
live mentions, every one of them a read (`WHERE archived_at IS NULL`) or the stamp itself.
Recovering the 877 candidate rows would have meant raw SQL, which this project forbids.

WHY A TEST AND NOT JUST THE COMMAND. The false comfort was a sentence nobody checked. The
last class below reads the spec's own reversal claim and requires the named command to
exist in the parser, so the sentence cannot outlive the code again.

THE NEGATIVE HALF IS THE CONTRACT: unarchiving must NOT move `status` or `completed_at`.
Archiving never changed them, so lifting the flag unhides a row rather than reviving work,
and a command that reopened the task would be editing history under the name of recovery.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_cli_hygiene import (  # noqa: E402
    _unarchive_apply,
    _unarchive_candidates,
    cmd_hygiene,
)
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
    (tmp_path / ".tausik").mkdir()
    be = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    s = ProjectService(be)
    yield s
    be.close()


def _seed(svc, slug: str, archived: str | None, completed: str = "2025-01-01T00:00:00Z") -> None:
    """A done task, optionally already archived at the given instant."""
    svc.task_add(None, slug, f"Title for {slug}")
    svc.be._conn.execute(
        "UPDATE tasks SET status='done', completed_at=?, archived_at=? WHERE slug=?",
        (completed, archived, slug),
    )
    svc.be._conn.commit()


def _row(svc, slug: str) -> dict:
    r = svc.be._conn.execute(
        "SELECT status, completed_at, archived_at FROM tasks WHERE slug=?", (slug,)
    ).fetchone()
    return {"status": r[0], "completed_at": r[1], "archived_at": r[2]}


def _run(svc, **kw) -> str:
    base = {"hygiene_cmd": "unarchive", "slug": None, "archived_within": None, "confirm": False}
    base.update(kw)
    out = io.StringIO()
    with redirect_stdout(out):
        cmd_hygiene(svc, argparse.Namespace(**base))
    return out.getvalue()


class TestTheSelectorsAreTheTwoWaysBackIn:
    def test_a_slug_unhides_exactly_that_task(self, svc):
        _seed(svc, "wanted", "2026-09-28T10:00:00Z")
        _seed(svc, "leave-me", "2026-09-28T10:00:00Z")
        assert _unarchive_apply(svc, slug="wanted") == 1
        assert _row(svc, "wanted")["archived_at"] is None
        assert _row(svc, "leave-me")["archived_at"] is not None

    def test_recency_undoes_the_batch_that_was_just_applied(self, svc):
        """`--archived-within`, not "older than", and the direction is the whole point.

        What needs undoing is the mass pass somebody ran minutes ago. Selecting the OLDEST
        archived rows would restore exactly the tasks meant to stay hidden and leave the
        fresh mistake in place.
        """
        for slug in ("fresh-1", "fresh-2", "old-one"):
            _seed(svc, slug, "placeholder")
        svc.be._conn.execute(
            "UPDATE tasks SET archived_at=datetime('now','-2 hours') "
            "WHERE slug IN ('fresh-1','fresh-2')"
        )
        svc.be._conn.execute(
            "UPDATE tasks SET archived_at=datetime('now','-400 days') WHERE slug='old-one'"
        )
        svc.be._conn.commit()
        assert _unarchive_apply(svc, within_days=1) == 2
        assert _row(svc, "old-one")["archived_at"] is not None, "the deliberate archive stays"

    def test_no_selector_is_refused_rather_than_defaulted(self, svc):
        """A bare `unarchive` would unhide the whole archive — a second mistake, not a fix."""
        _seed(svc, "archived", "2026-09-28T10:00:00Z")
        with pytest.raises(ServiceError, match="selector"):
            _run(svc, confirm=True)
        assert _row(svc, "archived")["archived_at"] is not None
        assert _unarchive_candidates(svc) == [], "and the query itself selects nothing"

    def test_an_unarchived_row_is_not_a_candidate(self, svc):
        _seed(svc, "visible", None)
        assert _unarchive_candidates(svc, slug="visible") == []
        assert _unarchive_apply(svc, slug="visible") == 0


class TestOnlyTheHidingFlagMoves:
    """THE NEGATIVE THAT MATTERS (AC-3): recovery must not become a revival."""

    def test_status_and_completed_at_survive_the_round_trip(self, svc):
        _seed(svc, "t", "2026-09-28T10:00:00Z", completed="2025-03-04T05:06:07Z")
        before = _row(svc, "t")
        _unarchive_apply(svc, slug="t")
        after = _row(svc, "t")
        assert after["archived_at"] is None
        assert after["status"] == before["status"] == "done"
        assert after["completed_at"] == before["completed_at"] == "2025-03-04T05:06:07Z"

    def test_the_row_returns_to_task_list(self, svc):
        """The point of the flag is the listing, so that is where the proof belongs."""
        _seed(svc, "hidden", "2026-09-28T10:00:00Z")
        assert "hidden" not in [t["slug"] for t in svc.task_list()]
        _unarchive_apply(svc, slug="hidden")
        assert "hidden" in [t["slug"] for t in svc.task_list()]


class TestTheDryRunIsTheDefault:
    def test_without_confirm_nothing_is_written(self, svc):
        _seed(svc, "t", "2026-09-28T10:00:00Z")
        out = _run(svc, slug="t")
        assert "dry-run" in out and "t" in out
        assert _row(svc, "t")["archived_at"] is not None

    def test_confirm_writes_and_says_what_it_did_not_touch(self, svc):
        _seed(svc, "t", "2026-09-28T10:00:00Z")
        out = _run(svc, slug="t", confirm=True)
        assert "1 task(s) unhidden" in out
        assert "completed_at" in out, "the output states the boundary, not only the action"
        assert _row(svc, "t")["archived_at"] is None

    def test_nothing_matching_is_reported_as_nothing(self, svc):
        """Absence reported as absence: no match is not an error and not a silent success."""
        out = _run(svc, slug="never-existed", confirm=True)
        assert "nothing archived matches" in out.lower()

    def test_the_usage_line_names_both_directions(self, svc):
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_hygiene(svc, argparse.Namespace(hygiene_cmd=None))
        assert "unarchive" in out.getvalue()


class TestTheConfigGatesHidingNotRecovery:
    def test_recovery_works_with_the_feature_switched_off(self, svc, tmp_path):
        """`task_archive.enabled` gates the operation that HIDES rows.

        A recovery path that switched off with it would be unavailable exactly when it is
        needed — after somebody archived a batch and turned the feature back off.
        """
        (tmp_path / ".tausik" / "config.json").write_text(
            '{"task_archive": {"enabled": false}}', encoding="utf-8"
        )
        _seed(svc, "t", "2026-09-28T10:00:00Z")
        assert "unhidden" in _run(svc, slug="t", confirm=True)
        assert _row(svc, "t")["archived_at"] is None


class TestThePromiseIsCheckedAndNotJustWritten:
    """The false comfort was a sentence nobody checked. These read the sentence.

    A reversal claim in a spec is worth exactly as much as the check behind it: the same
    spec claimed reversibility "by command" for two releases with no command in the tree.
    """

    @pytest.mark.parametrize("lang", ["en", "ru"])
    def test_the_spec_names_the_command_it_promises(self, lang):
        text = (_REPO / "docs" / lang / "task-archive-spec.md").read_text(encoding="utf-8")
        assert "hygiene unarchive" in text
        assert "--archived-within" in text

    def test_the_command_the_spec_names_is_registered(self):
        """Named in prose AND reachable from the parser — the pair is the whole check."""
        import project_parser_ops

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="cmd")
        project_parser_ops.add_hygiene(sub)
        args = parser.parse_args(["hygiene", "unarchive", "--archived-within", "3", "--confirm"])
        assert args.hygiene_cmd == "unarchive"
        assert args.archived_within == 3 and args.confirm is True

    def test_memory_has_no_reversal_and_the_spec_says_why(self):
        """The asymmetry is declared, so nobody reads it as an omission and adds one.

        Archiving a memory row stamps `valid_to` on its graph edges; clearing the flag
        would not bring them back, which is why only tasks get a way out.
        """
        for lang in ("en", "ru"):
            text = (_REPO / "docs" / lang / "task-archive-spec.md").read_text(encoding="utf-8")
            assert "edges_invalidate_to" in text
