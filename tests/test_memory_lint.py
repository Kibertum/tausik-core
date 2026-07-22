"""Tests for memory lint (v15p-memory-lint).

Pure detector (find_lint_candidates) on fixtures + the service orchestration
(lint_memory) dry-run vs --apply against an in-memory backend.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from memory_cleanup import find_lint_candidates  # noqa: E402


def _mem(mid, title="t", content="", mtype="pattern"):
    return {"id": mid, "type": mtype, "title": title, "content": content}


def _edge(source_id, target_id, relation):
    return {
        "source_type": "memory",
        "source_id": source_id,
        "target_type": "memory",
        "target_id": target_id,
        "relation": relation,
    }


_ALL_EXIST = lambda _p: True  # noqa: E731
_NONE_EXIST = lambda _p: False  # noqa: E731


class TestPureDetectors:
    def test_empty_memory_yields_nothing(self):
        assert find_lint_candidates([], [], _ALL_EXIST) == []

    def test_superseded_flags_active_target(self):
        rows = [_mem(1, "old"), _mem(2, "new")]
        edges = [_edge(2, 1, "supersedes")]  # #2 supersedes #1
        out = find_lint_candidates(rows, edges, _ALL_EXIST)
        assert len(out) == 1
        assert out[0]["id"] == 1
        assert out[0]["kind"] == "superseded"
        assert "#2" in out[0]["reason"]

    def test_superseded_skipped_when_target_archived(self):
        # Target #1 is not in the active rows (archived) -> no finding.
        rows = [_mem(2, "new")]
        edges = [_edge(2, 1, "supersedes")]
        assert find_lint_candidates(rows, edges, _ALL_EXIST) == []

    def test_contradicts_flags_both_active_endpoints(self):
        rows = [_mem(1), _mem(2)]
        edges = [_edge(1, 2, "contradicts")]
        out = find_lint_candidates(rows, edges, _ALL_EXIST)
        kinds = {f["kind"] for f in out}
        ids = sorted(f["id"] for f in out)
        assert kinds == {"contradicts"}
        assert ids == [1, 2]

    def test_stale_file_flagged_when_missing(self):
        rows = [_mem(1, content="see scripts/gone.py for details")]
        out = find_lint_candidates(rows, [], _NONE_EXIST)
        assert len(out) == 1
        assert out[0]["kind"] == "stale_file"
        assert "scripts/gone.py" in out[0]["reason"]

    def test_stale_file_not_flagged_when_present(self):
        rows = [_mem(1, content="see scripts/here.py for details")]
        assert find_lint_candidates(rows, [], _ALL_EXIST) == []

    def test_non_path_text_is_ignored(self):
        # No slash+ext token -> nothing to check, never flagged.
        rows = [_mem(1, content="this mentions ruff and mypy but no file path")]
        assert find_lint_candidates(rows, [], _NONE_EXIST) == []

    def test_url_and_hostname_are_not_flagged_as_stale_files(self):
        """l26-memory-dedupe-perf: a URL/hostname mentioned in prose is not a
        repo-relative path — flagging it as a missing file is noise. The FIRST
        segment being domain-like (example.com) is the tell."""
        rows = [
            _mem(1, content="see https://example.com/docs/page.html for the spec"),
            _mem(2, content="the api at example.com/v2/users.json returns json"),
            _mem(3, content="cdn.jsdelivr.net/npm/pkg/dist/index.min.js is the bundle"),
        ]
        assert find_lint_candidates(rows, [], _NONE_EXIST) == []

    def test_dotfile_dir_path_still_flagged(self):
        """A leading dotfile dir (.github/) is a real repo path, NOT a host — the
        refinement keys on an INTERNAL dot, so it must still be checked."""
        rows = [_mem(1, content="the workflow .github/workflows/ci.yml is gone")]
        out = find_lint_candidates(rows, [], _NONE_EXIST)
        assert len(out) == 1 and out[0]["kind"] == "stale_file"
        assert ".github/workflows/ci.yml" in out[0]["reason"]

    def test_broken_edge_does_not_crash(self):
        rows = [_mem(1)]
        bad = [{"source_type": "memory", "target_type": "memory", "relation": "supersedes"}]
        # Missing source_id/target_id -> skipped, no exception.
        assert find_lint_candidates(rows, bad, _ALL_EXIST) == []

    def test_non_memory_edge_skipped(self):
        rows = [_mem(1)]
        edge = {
            "source_type": "task",
            "source_id": 5,
            "target_type": "memory",
            "target_id": 1,
            "relation": "supersedes",
        }
        assert find_lint_candidates(rows, [edge], _ALL_EXIST) == []


class TestServiceLint:
    def _svc(self, tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        return ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))

    def test_dry_run_reports_without_archiving(self, tmp_path):
        svc = self._svc(tmp_path)
        try:
            a = svc.be.memory_add("pattern", "old way", "deprecated")
            b = svc.be.memory_add("pattern", "new way", "current")
            svc.be.edge_add("memory", b, "memory", a, "supersedes")
            result = svc.memory_lint(apply=False)
            assert result["applied"] is False
            assert result["archived"] == 0
            assert any(f["id"] == a and f["kind"] == "superseded" for f in result["findings"])
            # Dry-run leaves the row active.
            assert svc.be.memory_get(a)["archived_at"] is None
        finally:
            svc.be.close()

    def test_apply_archives_superseded_only(self, tmp_path):
        svc = self._svc(tmp_path)
        try:
            a = svc.be.memory_add("pattern", "old way", "deprecated")
            b = svc.be.memory_add("pattern", "new way", "current")
            c = svc.be.memory_add("gotcha", "c1", "x")
            d = svc.be.memory_add("gotcha", "c2", "y")
            svc.be.edge_add("memory", b, "memory", a, "supersedes")
            svc.be.edge_add("memory", c, "memory", d, "contradicts")
            result = svc.memory_lint(apply=True)
            assert result["applied"] is True
            assert result["archived"] == 1  # only the superseded #a
            assert svc.be.memory_get(a)["archived_at"] is not None
            # Contradiction endpoints stay active — advisory only.
            assert svc.be.memory_get(c)["archived_at"] is None
            assert svc.be.memory_get(d)["archived_at"] is None
        finally:
            svc.be.close()

    def test_empty_memory_lint(self, tmp_path):
        svc = self._svc(tmp_path)
        try:
            result = svc.memory_lint()
            assert result["findings"] == []
            assert result["count"] == 0
        finally:
            svc.be.close()
