"""A rejected `task_update` must leave nothing behind.

The three budget fields were validated and written one after another: call_budget
checked and stored, THEN cost_budget_usd parsed — and a bad value raised there,
after the first write had already landed. The call reported failure, the row had
changed, and the function exited by exception without ever reaching the
projection, so `tausik/tasks/<slug>.md` kept the old value. The divergence was
silent until the next `state export --check`, which reports "drift" and not "an
update was rejected halfway".

This is the third leak of the same kind found in one review, and the only one that
is not about cascades: the projection was tied to a successful RETURN, and writes
happen without one.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import state_triggers  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_export import build_tree  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def root(monkeypatch, tmp_path):
    r = tmp_path / "tausik"
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
    monkeypatch.setattr(state_triggers, "_tree_root", lambda _v: str(r))
    return str(r)


@pytest.fixture
def svc(root, tmp_path):
    """Depends on `root` so the seed task is projected: a test that compares the
    file before and after needs the file to exist before."""
    s = ProjectService(SQLiteBackend(str(tmp_path / "proj.db")))
    s.task_add(None, "t1", "Task one", goal="do it")
    yield s
    s.be.close()


def _file(root: str, slug: str) -> str:
    with open(os.path.join(root, "tasks", f"{slug}.md"), encoding="utf-8", newline="") as fh:
        return fh.read()


class TestARejectedUpdateWritesNothing:
    def test_a_bad_second_budget_does_not_keep_the_first(self, svc):
        with pytest.raises(ServiceError):
            svc.task_update("t1", call_budget=5, cost_budget_usd="not-a-number")
        assert svc.be.task_get("t1")["call_budget"] is None, (
            "call_budget was written before the next field failed validation -- "
            "a rejected call must not half-apply"
        )

    def test_a_bad_third_budget_does_not_keep_the_first_two(self, svc):
        with pytest.raises(ServiceError):
            svc.task_update("t1", call_budget=5, cost_budget_usd=1.5, token_budget="nope")
        row = svc.be.task_get("t1")
        assert row["call_budget"] is None and row["cost_budget_usd"] is None

    def test_a_negative_budget_is_rejected_whole(self, svc):
        with pytest.raises(ServiceError):
            svc.task_update("t1", call_budget=5, token_budget=-1)
        assert svc.be.task_get("t1")["call_budget"] is None

    def test_the_tree_still_matches_the_db_after_a_rejected_update(self, svc, root):
        before = _file(root, "t1")
        with pytest.raises(ServiceError):
            svc.task_update("t1", call_budget=5, cost_budget_usd="not-a-number")
        assert _file(root, "t1") == before
        assert _file(root, "t1") == build_tree(svc)[0]["tasks/t1.md"], (
            "the projection and the DB disagree after a rejected update"
        )


class TestTheAcceptedPathsAreUnchanged:
    """The fix reorders validation; it must not move a single successful outcome."""

    def test_all_three_budgets_together(self, svc):
        svc.task_update("t1", call_budget=5, cost_budget_usd=1.5, token_budget=1000)
        row = svc.be.task_get("t1")
        assert (row["call_budget"], row["cost_budget_usd"], row["token_budget"]) == (
            5,
            1.5,
            1000,
        )

    @pytest.mark.parametrize(
        ("field", "value", "column"),
        [
            ("call_budget", 7, "call_budget"),
            ("cost_budget_usd", 2.5, "cost_budget_usd"),
            ("token_budget", 900, "token_budget"),
        ],
    )
    def test_each_budget_alone(self, svc, field, value, column):
        """The cost-only and token-only early returns had no test at all."""
        svc.task_update("t1", **{field: value})
        assert svc.be.task_get("t1")[column] == value

    def test_a_budget_next_to_an_ordinary_field(self, svc, root):
        svc.task_update("t1", call_budget=9, title="Renamed")
        row = svc.be.task_get("t1")
        assert row["call_budget"] == 9 and row["title"] == "Renamed"
        assert "Renamed" in _file(root, "t1")

    def test_call_budget_overrides_tier_and_says_so(self, svc):
        msg = svc.task_update("t1", call_budget=9, tier="deep")
        assert "overridden by call_budget" in msg

    def test_ordinary_fields_alone_still_update(self, svc, root):
        svc.task_update("t1", title="Only a title")
        assert svc.be.task_get("t1")["title"] == "Only a title"
        assert "Only a title" in _file(root, "t1")


class TestTheRejectionIsWholeForEveryRefusalPoint:
    """Batching the budgets against each other narrowed the defect, not closed it.

    Every one of these pairs a VALID budget with something that is refused
    LATER in the method. Each was a live partial write: the budget (and the tier
    derived from it) landed, the call reported failure, and the exception left
    past the projection. The first case reproduced verbatim in review; the third
    is reachable only through the transaction, because `_update` raises after
    the budget setters have already auto-committed.
    """

    @pytest.mark.parametrize(
        "bad,label",
        [
            ({"scope_paths": "{not-json"}, "acl-not-json"),
            ({"scope_tools": "{also-not-json"}, "acl-other-field"),
            ({"nosuchcolumn": 1}, "unknown-column-rejected-by-the-backend"),
            ({"complexity": "gigantic"}, "invalid-enum"),
        ],
    )
    def test_a_valid_budget_next_to_a_later_refusal_writes_nothing(self, svc, bad, label):
        with pytest.raises((ServiceError, ValueError)):
            svc.task_update("t1", call_budget=40, **bad)
        row = svc.be.task_get("t1")
        assert row["call_budget"] is None, f"{label}: the budget survived a rejected call"
        assert row["tier"] is None, f"{label}: a tier was derived and kept by a rejected call"

    def test_the_tree_matches_the_db_after_a_late_refusal(self, svc, root):
        """The half the `state export --check` drift report could never explain."""
        with pytest.raises(ServiceError):
            svc.task_update("t1", call_budget=40, scope_paths="{not-json")
        expected, _ = build_tree(svc)
        with open(os.path.join(root, "tasks", "t1.md"), encoding="utf-8", newline="") as fh:
            assert fh.read() == expected["tasks/t1.md"]

    def test_the_mixed_call_still_works_when_nothing_is_refused(self, svc, root):
        """NEGATIVE: atomicity is not achieved by refusing mixed calls."""
        svc.task_update("t1", call_budget=12, scope_paths='["a.py"]')
        row = svc.be.task_get("t1")
        assert row["call_budget"] == 12
        assert row["tier"] == "light"  # still derived on the success path
        assert "a.py" in row["scope_paths"]
        expected, _ = build_tree(svc)
        with open(os.path.join(root, "tasks", "t1.md"), encoding="utf-8", newline="") as fh:
            assert fh.read() == expected["tasks/t1.md"]
