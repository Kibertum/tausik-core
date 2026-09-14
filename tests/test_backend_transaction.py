"""Transaction ownership: whose rows a failure is allowed to take with it.

`begin_tx` no-ops inside an open transaction while `commit_tx`/`rollback_tx`
act unconditionally, so a function that opened and closed a transaction
unconditionally would, when called inside someone else's, end THEIR
transaction. Measured live in session #211: an outer `begin_tx` + `epic_add`
lost its epic to a nested refusal, with no exception raised.

Nine call sites open a transaction; the rule was applied by hand at three.
`SQLiteBackend.transaction()` is that rule written once, and these tests hold
the two halves apart:

  * the OUTER case must keep behaving exactly as `begin_tx`/`commit_tx` did --
    this is the "fix it without opening a hole" half, and it is asserted
    separately on purpose;
  * the NESTED case gains something the backend could not do before. It used
    to be able only to DELEGATE cleanup ("your transaction, your rollback"),
    which left the guarantee conditional on the caller. A SAVEPOINT lets the
    nested block undo its own part and nothing else.

The open-transaction flag is asserted directly in several places because the
damage it describes is invisible in the rows: everything looks normal right up
until something else rolls back.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402


@pytest.fixture
def be(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "tx.db"))
    yield backend
    backend.close()


class TestOuterCaseIsUnchanged:
    """The half that must NOT move. A regression here is the hole reopened."""

    def test_success_commits_and_closes_the_transaction(self, be):
        with be.transaction():
            be.epic_add("e1", "Epic one", None)
            # PREMISE: the write is inside an open transaction, which is what
            # makes the commit below meaningful rather than incidental.
            assert be._in_tx is True

        assert be._in_tx is False
        assert be.epic_get("e1") is not None

    def test_failure_rolls_back_and_closes_the_transaction(self, be):
        with pytest.raises(RuntimeError, match="boom"):
            with be.transaction():
                be.epic_add("e2", "Epic two", None)
                raise RuntimeError("boom")

        assert be._in_tx is False
        assert be.epic_get("e2") is None
        # The connection is still usable, which is the point of asserting the
        # flag rather than only the rows.
        be.epic_add("e3", "Epic three", None)
        assert be.epic_get("e3") is not None

    def test_it_matches_hand_written_begin_commit(self, be):
        """Same observable result as the primitive it replaces, side by side."""
        be.begin_tx()
        be.epic_add("by-hand", "By hand", None)
        be.commit_tx()

        with be.transaction():
            be.epic_add("by-cm", "By context manager", None)

        assert be.epic_get("by-hand") is not None
        assert be.epic_get("by-cm") is not None
        assert be._in_tx is False


class TestNestedFailureTakesOnlyItsOwnPart:
    """The half that is new: a nested refusal stops being the caller's problem."""

    def test_the_callers_rows_and_transaction_both_survive(self, be):
        be.begin_tx()
        be.epic_add("outer-epic", "Outer epic", None)

        with pytest.raises(RuntimeError, match="nested boom"):
            with be.transaction():
                be.epic_add("inner-epic", "Inner epic", None)
                raise RuntimeError("nested boom")

        # THE GUARANTEE, all three parts, because any one alone would pass for
        # the wrong reason: the caller still owns an open transaction, its rows
        # are still there, and the nested block took its own write with it.
        assert be._in_tx is True, "a nested failure must not close the caller's transaction"
        assert be.epic_get("outer-epic") is not None, "the caller's write must survive"
        assert be.epic_get("inner-epic") is None, "the nested write must be gone"

        be.commit_tx()
        assert be.epic_get("outer-epic") is not None
        assert be.epic_get("inner-epic") is None

    def test_this_is_what_changed_the_delegated_guarantee_is_now_real(self, be):
        """Contrast with the OLD shape, spelled out so the diff has a witness.

        Under the hand-written `owns_tx` guard the nested write STAYED (the
        guard could skip its own rollback but could not undo its part), so the
        duty passed to the caller. Here the caller does nothing at all and the
        nested row is already gone.
        """
        be.begin_tx()
        be.epic_add("kept", "Kept by the caller", None)

        with pytest.raises(ValueError):
            with be.transaction():
                be.epic_add("undone", "Undone by itself", None)
                raise ValueError("refused")

        assert be.epic_get("undone") is None, "no caller rollback was needed to remove it"
        be.rollback_tx()
        assert be.epic_get("kept") is None

    def test_nested_success_lands_with_the_callers_commit(self, be):
        be.begin_tx()
        be.epic_add("outer-ok", "Outer ok", None)
        with be.transaction():
            be.epic_add("inner-ok", "Inner ok", None)

        # RELEASE is not a commit: the nested rows are the caller's to keep or
        # discard, and here the caller discards them.
        assert be._in_tx is True
        be.rollback_tx()
        assert be.epic_get("outer-ok") is None
        assert be.epic_get("inner-ok") is None

    def test_two_nested_blocks_do_not_collide_on_a_savepoint_name(self, be):
        """A reused SAVEPOINT name would RELEASE the outer one of that name."""
        be.begin_tx()
        with be.transaction():
            be.epic_add("first-nested", "First", None)
            with be.transaction():
                be.epic_add("second-nested", "Second", None)
                with pytest.raises(RuntimeError):
                    with be.transaction():
                        be.epic_add("third-nested", "Third", None)
                        raise RuntimeError("innermost")

        assert be._in_tx is True
        assert be.epic_get("first-nested") is not None
        assert be.epic_get("second-nested") is not None
        assert be.epic_get("third-nested") is None
        be.commit_tx()
        assert be.epic_get("third-nested") is None


class TestTheProjectionQueueIsNotSomebodyElsesToClear:
    """`rollback_tx` clears the WHOLE queue; a nested rollback must not.

    `_pending_projection` holds (table, slug) pairs written inside the open
    transaction, flushed to the git-native tree when it commits. A nested
    failure that cleared it entirely would drop the projections of rows that
    are still in the database -- the tree falling behind the DB, which is the
    exact divergence the queue exists to prevent, with the sign flipped.
    """

    def test_a_nested_failure_truncates_to_its_own_mark(self, be):
        be.begin_tx()
        be.epic_add("q-outer", "Queued by the caller", None)
        be.epic_update("q-outer", title="Renamed by the caller")
        queued_by_caller = list(be._pending_projection)
        # PREMISE: without something queued the truncation below would pass on
        # an empty list and prove nothing.
        assert queued_by_caller, "the caller's write must have queued a projection"

        with pytest.raises(RuntimeError):
            with be.transaction():
                be.epic_add("q-inner", "Queued by the nested block", None)
                be.epic_update("q-inner", title="Renamed by the nested block")
                assert len(be._pending_projection) > len(queued_by_caller)
                raise RuntimeError("nested boom")

        assert be._pending_projection == queued_by_caller

    def test_the_outer_case_still_clears_the_whole_queue_on_rollback(self, be):
        """The unchanged half of the same behaviour, asserted separately."""
        with pytest.raises(RuntimeError):
            with be.transaction():
                be.epic_add("q-solo", "Queued and discarded", None)
                be.epic_update("q-solo", title="Renamed")
                assert be._pending_projection
                raise RuntimeError("boom")

        assert be._pending_projection == []
