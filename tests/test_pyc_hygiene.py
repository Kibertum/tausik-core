"""Stale bytecode is detected by the directory it remembers, and purged by list.

`tracebacks-name-a-repository-path-that-does-not-exist`. All on synthetic
trees under tmp_path: a source is compiled where it lives, then the cache is
carried to a tree that never had it — the move the repository itself made.
"""

from __future__ import annotations

import os
import py_compile
import shutil
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import pyc_hygiene as H  # noqa: E402


def _compile_at(root, rel: str, body: str = "x = 1\n") -> str:
    """Write `rel` under `root` and compile it into its own __pycache__.
    Returns the .pyc path."""
    src = root.joinpath(*rel.split("/"))
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(body, encoding="utf-8")
    cache = src.parent / "__pycache__" / (src.stem + ".cpython-test.pyc")
    py_compile.compile(str(src), cfile=str(cache), dfile=str(src), doraise=True)
    return str(cache)


def _moved_tree(tmp_path):
    """The repository's own history in miniature: compiled at old/, carried to new/."""
    old, new = tmp_path / "old", tmp_path / "new"
    _compile_at(old, "tests/test_a.py")
    _compile_at(old, "scripts/mod.py")
    shutil.copytree(old, new)
    shutil.rmtree(old)  # the old address no longer exists — as measured in #187
    return new


class TestDetection:
    def test_a_fresh_cache_next_to_its_source_is_honest(self, tmp_path):
        _compile_at(tmp_path, "pkg/mod.py")
        assert H.stale_bytecode(str(tmp_path)) == []

    def test_a_cache_carried_to_another_tree_names_the_old_path(self, tmp_path):
        new = _moved_tree(tmp_path)
        stale = H.stale_bytecode(str(new))
        assert len(stale) == 2
        for pyc, recorded in stale:
            assert pyc.startswith(str(new))
            assert str(tmp_path / "old") in recorded
            assert not os.path.exists(recorded)

    def test_the_directory_is_compared_normalised_not_spelt(self, tmp_path):
        """`tests\\..\\scripts` and `scripts` are the same place. Measured in
        #207: 275 caches carried the former spelling and are NOT stale."""
        src = tmp_path / "scripts" / "mod.py"
        src.parent.mkdir()
        src.write_text("x = 1\n", encoding="utf-8")
        cache = src.parent / "__pycache__" / "mod.cpython-test.pyc"
        spelt = os.path.join(str(tmp_path), "tests", "..", "scripts", "mod.py")
        py_compile.compile(str(src), cfile=str(cache), dfile=spelt, doraise=True)
        assert H.recorded_source(str(cache)) == spelt
        assert H.stale_bytecode(str(tmp_path)) == []

    def test_a_relative_recorded_path_is_not_a_lie_about_location(self, tmp_path):
        src = tmp_path / "scripts" / "hooks" / "h.py"
        src.parent.mkdir(parents=True)
        src.write_text("x = 1\n", encoding="utf-8")
        cache = src.parent / "__pycache__" / "h.cpython-test.pyc"
        py_compile.compile(str(src), cfile=str(cache), dfile="scripts/hooks/h.py", doraise=True)
        assert H.stale_bytecode(str(tmp_path)) == []

    def test_an_unreadable_pyc_is_not_evidence(self, tmp_path):
        cache = tmp_path / "pkg" / "__pycache__" / "junk.cpython-test.pyc"
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b"\x00" * 10)
        assert H.recorded_source(str(cache)) is None
        assert H.stale_bytecode(str(tmp_path)) == []

    @pytest.mark.parametrize("skipped", sorted(H.SKIP_DIRS - {".git", "node_modules"}))
    def test_read_only_trees_are_never_walked(self, tmp_path, skipped):
        new = _moved_tree(tmp_path / "inner")
        target = tmp_path / skipped
        shutil.copytree(new, target)
        shutil.rmtree(tmp_path / "inner")
        assert H.stale_bytecode(str(tmp_path)) == []


class TestPurge:
    def test_purge_removes_exactly_the_listed_files(self, tmp_path):
        new = _moved_tree(tmp_path)
        honest = _compile_at(new, "scripts/fresh.py")  # compiled here, stays
        stale = H.stale_bytecode(str(new))
        assert H.purge(stale) == 2
        assert all(not os.path.exists(p) for p, _r in stale)
        assert os.path.exists(honest)
        assert H.stale_bytecode(str(new)) == []

    def test_purge_of_an_already_missing_file_is_not_an_error(self, tmp_path):
        new = _moved_tree(tmp_path)
        stale = H.stale_bytecode(str(new))
        os.remove(stale[0][0])
        assert H.purge(stale) == 1


class TestDoctorRow:
    def _collect(self):
        rows: list[tuple[str, str, str]] = []
        return (
            rows,
            (lambda label, d: rows.append(("ok", label, d))),
            (lambda label, d: rows.append(("warn", label, d))),
        )

    def test_green_when_nothing_is_stale(self, tmp_path):
        _compile_at(tmp_path, "pkg/mod.py")
        rows, ok, warn = self._collect()
        assert H.doctor_section(str(tmp_path), False, ok, warn) == 0
        assert rows[0][0] == "ok"

    def test_warns_names_the_old_tree_and_the_remedy(self, tmp_path):
        new = _moved_tree(tmp_path)
        rows, ok, warn = self._collect()
        assert H.doctor_section(str(new), False, ok, warn) == 1
        kind, _label, detail = rows[0]
        assert kind == "warn"
        assert "2 .pyc" in detail
        assert str(tmp_path / "old") in detail
        assert "--fix-bytecode" in detail
        assert H.stale_bytecode(str(new)), "reporting must not purge"

    def test_fix_purges_and_says_so(self, tmp_path):
        new = _moved_tree(tmp_path)
        rows, ok, warn = self._collect()
        H.doctor_section(str(new), True, ok, warn)
        assert rows[0][0] == "warn" and "purged 2 of 2" in rows[0][2]
        assert H.stale_bytecode(str(new)) == []


def test_the_doctor_parser_carries_the_flag_and_the_doctor_calls_the_row():
    root = os.path.dirname(SCRIPTS)
    with open(os.path.join(root, "scripts", "project_parser.py"), encoding="utf-8") as fh:
        assert "--fix-bytecode" in fh.read()
    with open(os.path.join(root, "scripts", "project_cli_doctor.py"), encoding="utf-8") as fh:
        assert "doctor_section(" in fh.read()
