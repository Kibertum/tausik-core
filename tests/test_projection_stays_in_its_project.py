"""The projection writes into the project that owns the DB, or it writes nowhere.

`auto_export_write` hung the projection off the write layer, which moved the
trigger BELOW `ProjectService` — down to a bare `SQLiteBackend`, which has a
db_path and nothing else. Two things the service used to supply came along as
assumptions instead of values. (What that move did and did not buy in coverage
is a separate matter, settled in `auto_export_write`'s own docstring; this file
is about where the projection lands, not what it reaches.)

THE ADDRESS. `_tree_root` is `dirname(tausik_dir) + "/tausik"`, and
`_BackendView.tausik_dir()` is `dirname(db_path)`. Composed, that is
`dirname(dirname(db_path))/tausik`, which lands on the project root ONLY when
the DB sits inside the project's `.tausik/`. For a bare backend at
`<tmp>/case0/tausik.db` it lands on `<tmp>/tausik` — a SIBLING of case0, a
directory the caller never named and does not own. At `:memory:` it lands beside
the repository. So the address must be derived from something PROVEN — a
directory that names itself `.tausik` — and when nothing proves it, the
projection must not happen at all. Fail-closed, like the brain publish guard:
a false negative costs one unprojected row, a false positive writes files into
somebody else's directory.

THE SWITCH. `_auto_export_enabled` read `load_config()` with no argument, i.e.
the ambient cwd — the very mcp-config-read-paths-ignore-project-handle defect
that `_tree_root`'s own docstring names three lines below. The path was fixed
and the policy was not. That is why this repository's `state.auto_export=true`
switched the projection on for every temp DB pytest built: no test opted in,
the repository opted them all in. Measured before the fix: 31 `.md` files in the
SHARED pytest basetemp root after 311 tests, with colliding universal slugs
(`e`, `s`, `mvp`, `setup`), never cleaned up.

Both halves have one root — a handle that answers `tausik_dir` is the only thing
allowed to decide where and whether — so both are tested here.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import state_triggers  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402

# Declared rather than opted out. This walks a tree — `tmp_path`, not a source
# tree — so the detector flags it either way, but the scoped-pytest gate maps
# changes to tests by BASENAME, and nothing about `test_projection_stays_in_its
# _project` matches the three modules it actually guards: the trigger that
# resolves the address, the loader that answers the switch, and the backend that
# fires the write. Opting out would leave exactly the blindness this file exists
# to close.
CROSSCUTTING_SCOPE = [
    "scripts/state_triggers.py",
    "scripts/project_config.py",
    "scripts/project_backend.py",
]


@pytest.fixture(autouse=True)
def _no_ambient_handle(monkeypatch):
    """No TAUSIK_DIR in the environment: these tests are about what resolves it."""
    monkeypatch.delenv("TAUSIK_DIR", raising=False)


def _md_files(root) -> list[str]:
    """Every `.md` anywhere under `root`, relative and slash-normalised."""
    return sorted(
        os.path.relpath(os.path.join(d, f), str(root)).replace(os.sep, "/")
        for d, _dirs, files in os.walk(str(root))
        for f in files
        if f.endswith(".md")
    )


def _project(root, *, auto_export: bool) -> SQLiteBackend:
    """A real project directory: `<root>/.tausik/{config.json,tausik.db}`."""
    tausik_dir = root / ".tausik"
    tausik_dir.mkdir(parents=True)
    (tausik_dir / "config.json").write_text(
        json.dumps({"state": {"auto_export": auto_export}}), encoding="utf-8"
    )
    return SQLiteBackend(str(tausik_dir / "tausik.db"))


def _mutate(be: SQLiteBackend) -> None:
    """The two-call sequence from the report: an insert, then a projected update."""
    be.epic_add("e", "E")
    be.epic_update("e", title="X")


class TestTheAddressIsProven:
    """Where the projection goes is derived from a project, not from a path shape."""

    def test_bare_backend_outside_a_project_writes_no_file_anywhere(self, tmp_path, monkeypatch):
        """The reported measurement, as a test: `<tmp>/case0/tausik.db` wrote `<tmp>/tausik`.

        The switch is forced ON here so that only the ADDRESS is on trial —
        otherwise a fix to the switch alone would turn this green while the
        write still had nowhere legitimate to go.
        """
        monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
        case = tmp_path / "case0"
        case.mkdir()
        be = SQLiteBackend(str(case / "tausik.db"))
        try:
            _mutate(be)
        finally:
            be.close()

        assert _md_files(tmp_path) == [], (
            "a backend whose DB is not inside a project's .tausik/ projected anyway"
        )

    def test_backend_inside_a_project_still_projects(self, tmp_path, monkeypatch):
        """The negative half: fail-closed must not mean fail-always."""
        monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
        be = _project(tmp_path / "proj", auto_export=True)
        try:
            _mutate(be)
        finally:
            be.close()

        assert _md_files(tmp_path) == ["proj/tausik/epics/e.md"]

    def test_in_memory_db_projects_nowhere(self, tmp_path, monkeypatch):
        """`:memory:` resolves against the cwd, so the old address left the repo entirely.

        The cwd is a SUBDIRECTORY of `tmp_path` on purpose. Standing directly in
        `tmp_path` made this test green against the unfixed code — not because
        nothing was written, but because the old address is the cwd's PARENT, so
        the file landed one level above where the assertion looked. A probe that
        the defect can walk out of proves nothing.
        """
        monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        monkeypatch.chdir(cwd)
        be = SQLiteBackend(":memory:")
        try:
            _mutate(be)
        finally:
            be.close()

        assert _md_files(tmp_path) == []


class TestTheSwitchIsReadFromTheSameHandleAsTheAddress:
    """`state.auto_export` answers for the project being written, not for the cwd."""

    def test_target_off_while_cwd_is_on_stays_off(self, tmp_path, monkeypatch):
        """This is the shape that switched the whole test suite on."""
        _project(tmp_path / "on", auto_export=True)  # the cwd's project
        monkeypatch.chdir(tmp_path / "on")
        be = _project(tmp_path / "off", auto_export=False)
        try:
            _mutate(be)
        finally:
            be.close()

        assert _md_files(tmp_path) == [], (
            "the cwd's config switched the projection on for another project's DB"
        )

    def test_target_on_while_cwd_is_off_still_projects(self, tmp_path, monkeypatch):
        """And the inverse: an opted-in project is not switched off by where we stand."""
        _project(tmp_path / "off", auto_export=False)  # the cwd's project
        monkeypatch.chdir(tmp_path / "off")
        be = _project(tmp_path / "on", auto_export=True)
        try:
            _mutate(be)
        finally:
            be.close()

        assert _md_files(tmp_path) == ["on/tausik/epics/e.md"]
