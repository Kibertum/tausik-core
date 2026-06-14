"""Tests for the delegated-worker scope hard-gate (v15-ow-scope-hardgate)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from project_backend import SQLiteBackend  # noqa: E402
from scope_write_gate import _delegated_slugs, delegated_missing_scope  # noqa: E402


class TestDelegatedMissingScope:
    def test_blocks_delegated_without_scope(self):
        acls = [("worker-task", None)]
        assert delegated_missing_scope(acls, {"worker-task"}) == "worker-task"

    def test_allows_delegated_with_scope(self):
        acls = [("worker-task", '["scripts/*"]')]
        assert delegated_missing_scope(acls, {"worker-task"}) is None

    def test_non_delegated_without_scope_unaffected(self):
        acls = [("normal-task", None)]
        assert delegated_missing_scope(acls, set()) is None

    def test_mixed_returns_offending_delegated(self):
        acls = [("normal", None), ("worker", None)]
        assert delegated_missing_scope(acls, {"worker"}) == "worker"


class TestDelegatedSlugs:
    def test_reads_delegated_from_meta(self, tmp_path):
        db = str(tmp_path / "t.db")
        be = SQLiteBackend(db)
        be.meta_set("delegation:feat-x", '{"model": "m"}')
        be.meta_set("delegation:feat-y", '{"model": "m"}')
        be.close()
        assert _delegated_slugs(db) == {"feat-x", "feat-y"}

    def test_cleared_delegation_excluded(self, tmp_path):
        db = str(tmp_path / "t.db")
        be = SQLiteBackend(db)
        be.meta_set("delegation:feat-x", '{"model": "m"}')
        be.meta_set("delegation:feat-y", "")  # cleared (empty value)
        be.close()
        assert _delegated_slugs(db) == {"feat-x"}

    def test_db_error_degrades_to_empty(self, tmp_path):
        # Non-existent DB → sqlite error → empty set (legacy policy), no crash.
        assert _delegated_slugs(str(tmp_path / "missing.db")) == set()
