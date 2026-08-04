"""Cross-cutting test resolution (scoped-pytest-blind-to-crosscutting-tests).

The basename heuristic maps `scripts/foo.py` -> `tests/test_foo.py`. A whole
class of tests is built the opposite way: they iterate a TREE (every hook, every
doc, every profile) and are therefore relevant to ANY change inside that tree,
without being tied to one basename. A task that changed `scripts/hooks/x.py`,
scoped its pytest, and went green could still have broken three such tests that
the scope could not, in principle, find.

The fix is opt-in and path-based: a cross-cutting test declares a module-level
`CROSSCUTTING_SCOPE` (path prefixes it guards), and the resolver adds it to a
scoped run when any changed file falls under one of those prefixes.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import gate_test_resolver as gtr  # noqa: E402


def _mk(tmp_path, rel, body=""):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


class TestReadCrosscuttingScope:
    def test_reads_declared_list(self, tmp_path):
        f = _mk(
            tmp_path, "tests/test_x.py", "CROSSCUTTING_SCOPE = ['scripts/hooks/', 'bootstrap/']\n"
        )
        assert gtr.read_crosscutting_scope(str(f)) == ["scripts/hooks/", "bootstrap/"]

    def test_absent_declaration_is_none(self, tmp_path):
        f = _mk(tmp_path, "tests/test_x.py", "x = 1\n")
        assert gtr.read_crosscutting_scope(str(f)) is None

    def test_empty_optout_is_empty_list_not_none(self, tmp_path):
        """`CROSSCUTTING_SCOPE = []` is the visible opt-out: 'reviewed, not
        cross-cutting'. It must read as a declared-empty, distinct from absent."""
        f = _mk(tmp_path, "tests/test_x.py", "CROSSCUTTING_SCOPE = []\n")
        assert gtr.read_crosscutting_scope(str(f)) == []

    def test_syntax_error_is_none_not_crash(self, tmp_path):
        f = _mk(tmp_path, "tests/test_x.py", "def (:\n")
        assert gtr.read_crosscutting_scope(str(f)) is None

    def test_non_literal_value_is_none(self, tmp_path):
        f = _mk(tmp_path, "tests/test_x.py", "CROSSCUTTING_SCOPE = some_call()\n")
        assert gtr.read_crosscutting_scope(str(f)) is None


class TestResolverIncludesCrosscutting:
    def _tree(self, tmp_path):
        # a cross-cutting test guarding scripts/hooks/, and an ordinary one
        _mk(
            tmp_path,
            "tests/test_hooks_tree.py",
            "CROSSCUTTING_SCOPE = ['scripts/hooks/']\n",
        )
        _mk(tmp_path, "tests/test_unrelated.py", "CROSSCUTTING_SCOPE = ['docs/']\n")
        _mk(tmp_path, "tests/test_foo.py", "x = 1\n")  # basename target for scripts/foo.py

    def test_change_in_tree_pulls_the_crosscutting_test(self, tmp_path):
        self._tree(tmp_path)
        got = gtr.resolve_test_files_for_relevant(
            ["scripts/hooks/bash_firewall.py"], root=str(tmp_path)
        )
        assert "tests/test_hooks_tree.py" in got, "path-matched cross-cutting test not included"
        assert "tests/test_unrelated.py" not in got, "non-matching cross-cutting test leaked in"

    def test_basename_and_crosscutting_combine(self, tmp_path):
        self._tree(tmp_path)
        got = gtr.resolve_test_files_for_relevant(
            ["scripts/foo.py", "scripts/hooks/x.py"], root=str(tmp_path)
        )
        assert "tests/test_foo.py" in got  # basename mapping still works
        assert "tests/test_hooks_tree.py" in got  # plus the tree guard

    def test_no_match_pulls_no_crosscutting(self, tmp_path):
        """AC2: no fallback to the full suite. A change matching no tree adds
        nothing — the scoped-skip promise (empty -> SKIP) is preserved."""
        self._tree(tmp_path)
        got = gtr.resolve_test_files_for_relevant(["scripts/nope.py"], root=str(tmp_path))
        assert got == [], "an unmatched change dragged in cross-cutting or full-suite tests"

    def test_prefix_respects_directory_boundary(self, tmp_path):
        """`scripts/hooks/` must not match `scripts/hooks_helpers/x.py`."""
        _mk(tmp_path, "tests/test_hooks_tree.py", "CROSSCUTTING_SCOPE = ['scripts/hooks/']\n")
        got = gtr.resolve_test_files_for_relevant(
            ["scripts/hooks_helpers/x.py"], root=str(tmp_path)
        )
        assert got == []

    def test_prefix_without_trailing_slash_matches_dir(self, tmp_path):
        _mk(tmp_path, "tests/test_h.py", "CROSSCUTTING_SCOPE = ['harness']\n")
        got = gtr.resolve_test_files_for_relevant(
            ["harness/claude/mcp/server.py"], root=str(tmp_path)
        )
        assert "tests/test_h.py" in got

    def test_empty_optout_never_matches(self, tmp_path):
        _mk(tmp_path, "tests/test_optout.py", "CROSSCUTTING_SCOPE = []\n")
        got = gtr.resolve_test_files_for_relevant(["scripts/hooks/x.py"], root=str(tmp_path))
        assert got == []


class TestDeclaredScopesResolveInRealRepo:
    def test_hooks_change_includes_named_crosscutting_tests(self):
        """AC5 end-to-end in the real repo: a scripts/hooks change now pulls the
        tree-guarding tests the basename heuristic could never map."""
        got = gtr.resolve_test_files_for_relevant(["scripts/hooks/bash_firewall.py"], root=_ROOT)
        got_names = {os.path.basename(p) for p in got}
        assert "test_hook_encoding.py" in got_names
