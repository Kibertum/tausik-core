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


def _only_dirs_exist(*dirs: str):
    """Resolver where the given directories exist but no file does — the shape
    the stale_file detector now requires (a real dir with a missing file)."""
    dset = set(dirs)
    return lambda p: p in dset


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
        # A real deletion inside a live directory: scripts/ exists, gone.py does not.
        rows = [_mem(1, content="see scripts/gone.py for details")]
        out = find_lint_candidates(rows, [], _only_dirs_exist("scripts"))
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
        out = find_lint_candidates(rows, [], _only_dirs_exist(".github/workflows"))
        assert len(out) == 1 and out[0]["kind"] == "stale_file"
        assert ".github/workflows/ci.yml" in out[0]["reason"]


class TestStaleFilePrecision:
    """memory-lint-stale-file-mostly-false-positives: a report that is 90% noise
    is a report people stop reading. These pin each false-positive class the
    real memory set produced, and the real-deletion case that must survive."""

    def test_slash_as_alternation_separator_not_flagged(self):
        # `lru_cache/functools.cache`, `release/1.8`, `HEAD/v1.6.1` — slashes are
        # separators of alternatives in prose; none has an existing parent dir.
        rows = [
            _mem(1, content="use lru_cache/functools.cache for memoisation"),
            _mem(2, content="branch release/1.8 was cut from HEAD/v1.6.1"),
        ]
        # Nothing exists (no such dirs) -> no flags.
        assert find_lint_candidates(rows, [], _NONE_EXIST) == []

    def test_path_fragment_without_anchor_not_flagged(self):
        # `ru/senar.md` is a fragment of `docs/{ru,en}/senar.md`; `ru/` is not a
        # real dir, so it must not be reported as a missing file.
        rows = [_mem(1, content="mirrors ru/senar.md and en/senar.md")]
        assert find_lint_candidates(rows, [], _NONE_EXIST) == []

    def test_placeholder_basenames_not_flagged_even_in_real_dir(self):
        # Placeholders appear in prose describing a format; `tests/` DOES exist,
        # so only the placeholder denylist keeps these out.
        rows = [
            _mem(1, content="cite it like tests/test_x.py::test_y or tests/test_file.py"),
            _mem(2, content="the bootstrap example writes scripts/x.py"),
        ]
        out = find_lint_candidates(rows, [], _only_dirs_exist("tests", "scripts"))
        assert [f for f in out if f["kind"] == "stale_file"] == []

    def test_real_deletion_in_live_dir_is_still_flagged(self):
        """AC4 anti-gutting: a genuinely missing file inside an EXISTING dir must
        still be reported — the fix must not silence real staleness."""
        rows = [_mem(1, content="the old scripts/deleted_module.py was removed")]
        out = find_lint_candidates(rows, [], _only_dirs_exist("scripts"))
        assert len(out) == 1
        assert out[0]["kind"] == "stale_file"
        assert "scripts/deleted_module.py" in out[0]["reason"]

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


# --- a git-ignored path is absent by design, not stale --------------------
# Measured session #209: three of seven stale_file findings named
# `.claude/settings.local.json`, `.qwen/QWEN.md` and `.kilo/AGENTS.md` —
# machine-local or generated files that a fresh checkout does not have and the
# next bootstrap restores. Reporting them teaches the reader to skim the list
# that also holds the real ones.


def test_a_git_ignored_path_is_not_reported_as_stale():
    rows = [_mem(1, content="see .claude/settings.local.json for the local overrides")]
    findings = find_lint_candidates(
        rows,
        [],
        _only_dirs_exist(".claude"),
        path_is_ignored=lambda p: p == ".claude/settings.local.json",
    )
    assert findings == []


def test_a_tracked_path_that_is_gone_is_still_reported():
    """The other end. Silencing every missing path would 'fix' the noise by
    switching the detector off."""
    rows = [_mem(1, content="see docs/skills.md for the cascade")]
    findings = find_lint_candidates(
        rows,
        [],
        _only_dirs_exist("docs"),
        path_is_ignored=lambda _p: False,
    )
    assert [f["kind"] for f in findings] == ["stale_file"]
    assert "docs/skills.md" in findings[0]["reason"]


def test_without_an_ignore_probe_nothing_is_silenced():
    """`path_is_ignored=None` means 'ask nothing', so the pure detector keeps
    behaving exactly as it did before the probe existed."""
    rows = [_mem(1, content="see .claude/settings.local.json for the local overrides")]
    findings = find_lint_candidates(rows, [], _only_dirs_exist(".claude"))
    assert [f["kind"] for f in findings] == ["stale_file"]


def test_an_example_name_in_prose_is_not_a_stale_reference():
    rows = [_mem(1, content="cite it as tests/test_x.py::test_y in the receipt")]
    assert find_lint_candidates(rows, [], _only_dirs_exist("tests")) == []


def test_a_path_relative_to_a_working_directory_is_not_a_repo_claim():
    """Measured: memory #531 quotes `subprocess.run(['bash', './probe.sh'])`,
    a command's argument, not a file this repository is expected to hold."""
    rows = [_mem(1, content="five tests called subprocess.run(['bash', './probe.sh'])")]
    assert find_lint_candidates(rows, [], _only_dirs_exist(".")) == []


# --- the service layer: the probe has to be WIRED, and it has to fail open ---
# Both of these were mutation survivors: turning the probe off in the service,
# and making it answer "ignored" when git cannot answer, left every test green
# while silencing the whole stale_file detector.


class _Backend:
    """The three methods `lint_memory` actually calls."""

    def __init__(self, rows, edges=()):
        self._rows, self._edges = rows, list(edges)
        self.archived: list[int] = []

    def memory_list(self, n=500, include_archived=False):
        return self._rows

    def edge_list(self, relation=None, n=500):
        return [e for e in self._edges if e["relation"] == relation]

    def memory_archive_ids(self, ids):
        self.archived.extend(ids)
        return len(ids)


def test_the_service_consults_git_and_drops_the_ignored_path(monkeypatch):
    import service_knowledge_hygiene as hygiene

    asked: list[str] = []

    def _probe_factory(_root):
        def _probe(path):
            asked.append(path)
            return path == ".claude/settings.local.json"

        return _probe

    monkeypatch.setattr(hygiene, "git_ignore_probe", _probe_factory)
    rows = [_mem(1, content="see .claude/settings.local.json and docs/skills.md")]
    out = hygiene.lint_memory(_Backend(rows))
    reported = {f["reason"] for f in out["findings"]}
    assert asked, "the service never asked git anything"
    assert not any("settings.local.json" in r for r in reported)
    assert any("docs/skills.md" in r for r in reported)


def test_an_injected_filesystem_is_not_this_repository(monkeypatch):
    """`file_exists` supplied means the caller is describing some other tree, so
    asking THIS repository's git about those paths would be nonsense."""
    import service_knowledge_hygiene as hygiene

    def _fail(_root):  # pragma: no cover - must never be reached
        raise AssertionError("git was consulted about an injected filesystem")

    monkeypatch.setattr(hygiene, "git_ignore_probe", _fail)
    rows = [_mem(1, content="see docs/skills.md")]
    out = hygiene.lint_memory(_Backend(rows), file_exists=_only_dirs_exist("docs"))
    assert [f["kind"] for f in out["findings"]] == ["stale_file"]


def test_the_probe_answers_truthfully_for_this_repository():
    from service_knowledge_hygiene import git_ignore_probe

    probe = git_ignore_probe(os.path.abspath(os.path.join(_SCRIPTS, "..")))
    assert probe(".tausik/tausik.db") is True
    assert probe("scripts/project.py") is False


def test_the_probe_fails_open_where_git_cannot_answer(tmp_path):
    """Fail CLOSED would let a broken git switch the detector off in silence —
    every path would read as 'ignored, so not stale'."""
    from service_knowledge_hygiene import git_ignore_probe

    probe = git_ignore_probe(str(tmp_path))
    assert probe("anything/at/all.py") is False
