"""Three sources of a closing task's scope, in falling order of authority.

verify-warn-names-a-flag-verify-does-not-have split this out of
`service_task_done` at the filesize gate. The behaviour was already covered
end-to-end (test_verify_scope_pointer, test_verify_first_contract); what these
tests add is the boundary of each source in isolation — including the two that
are easy to get subtly wrong: an unparseable stored scope, and a recovered
scope whose paths are security-sensitive.

Named for the module so the scoped pytest gate maps `scripts/task_done_scope.py`
to this file by basename.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from task_done_scope import (  # noqa: E402
    persist_declared_scope,
    scope_from_recent_verify,
    scope_from_task_row,
)


class _Backend:
    def __init__(self):
        self.updates: list[tuple[str, dict]] = []

    def task_update(self, slug, **fields):
        self.updates.append((slug, fields))


class TestPersistDeclaredScope:
    def test_a_declared_scope_is_written_immediately(self):
        be = _Backend()
        assert persist_declared_scope(be, "t", ["a.py", "b.py"]) is True
        slug, fields = be.updates[0]
        assert slug == "t"
        assert json.loads(fields["relevant_files"]) == ["a.py", "b.py"]

    def test_nothing_declared_writes_nothing(self):
        """None means "did not say", which must not overwrite what was said."""
        be = _Backend()
        assert persist_declared_scope(be, "t", None) is False
        assert be.updates == []

    def test_an_empty_declaration_writes_nothing(self):
        """An empty list is almost always a glob that matched nothing.

        Treating it as "the scope is nothing" would silently unscope the task —
        the exact state the caller was trying to leave.
        """
        be = _Backend()
        assert persist_declared_scope(be, "t", []) is False
        assert be.updates == []


class TestScopeFromTaskRow:
    def test_it_reads_a_stored_list(self):
        assert scope_from_task_row({"relevant_files": '["a.py"]'}) == ["a.py"]

    def test_absent_is_none(self):
        assert scope_from_task_row({}) is None
        assert scope_from_task_row({"relevant_files": ""}) is None
        assert scope_from_task_row({"relevant_files": None}) is None

    def test_unparseable_is_absence_not_a_crash(self):
        """This runs on the close path; a scope that cannot be read is no scope."""
        assert scope_from_task_row({"relevant_files": "{not json"}) is None

    def test_a_non_list_payload_is_absence(self):
        """A dict or a bare string would break every consumer downstream."""
        assert scope_from_task_row({"relevant_files": '{"a": 1}'}) is None
        assert scope_from_task_row({"relevant_files": '"a.py"'}) is None


class TestScopeFromRecentVerify:
    def _patch(self, monkeypatch, recovered, sensitive):
        import service_verification
        import verify_recent_lookup

        monkeypatch.setattr(
            verify_recent_lookup,
            "lookup_relevant_files_from_recent_verify",
            lambda _c, _s: recovered,
        )
        monkeypatch.setattr(service_verification, "is_security_sensitive", lambda _f: sensitive)

    def test_an_ordinary_recovery_is_adopted(self, monkeypatch):
        self._patch(monkeypatch, ["scripts/x.py"], False)
        adoptable, for_count = scope_from_recent_verify(None, "t")
        assert adoptable == ["scripts/x.py"]
        assert for_count == ["scripts/x.py"]

    def test_a_security_sensitive_recovery_counts_but_is_not_adopted(self, monkeypatch):
        """The count leaks only a number; adopting the paths would not.

        Dropping it entirely would blind the complexity detector to exactly the
        category where an understated closure costs most.
        """
        self._patch(monkeypatch, ["scripts/hooks/auth.py"], True)
        adoptable, for_count = scope_from_recent_verify(None, "t")
        assert adoptable is None
        assert for_count == ["scripts/hooks/auth.py"]

    def test_nothing_recovered_is_two_nones(self, monkeypatch):
        self._patch(monkeypatch, [], False)
        assert scope_from_recent_verify(None, "t") == (None, None)
