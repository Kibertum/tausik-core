"""One process, possibly several projects — and the isolation between them is a property here.

WHY THE SEAM EXISTS BEFORE IT IS NEEDED. The spike counted live processes: seven `claude.exe`
hosts, six `tausik-project` servers, six DISTINCT parents. The host starts one stdio server per
window and pins it with `--project`, so a cache keyed by project is a cache of size one today.
What changes that is a transport where the process is not tied to a window, and the 2026-07-28
spec removed the handshake and the session header precisely so any request may land in any
instance. Building the seam now costs a module; building it during the migration costs the
migration.

THE NEGATIVES CARRY THIS FILE. An unresolvable project, a resolved path that has no `.tausik/`,
and two projects that must not see each other's data. The second is the dangerous one:
`SQLiteBackend` CREATES the file it is pointed at, so a dead directory would not raise — it
would succeed at serving an empty project.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_MCP = _REPO / "harness" / "claude" / "mcp" / "project"
for _p in (str(_MCP), str(_REPO / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tenancy import (  # noqa: E402
    NO_PROJECT_MESSAGE,
    ProjectUnresolved,
    ServiceRegistry,
)


class _FakeBackend:
    def __init__(self, path: str) -> None:
        self.path = path
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeService:
    """Stands in for ProjectService: the registry only ever holds and returns it."""

    made = 0

    def __init__(self, project_dir: str) -> None:
        type(self).made += 1
        self.project_dir = project_dir
        self.be = _FakeBackend(os.path.join(project_dir, ".tausik", "tausik.db"))


def _factory(project_dir: str) -> _FakeService:
    return _FakeService(project_dir)


@pytest.fixture(autouse=True)
def _reset_counter():
    _FakeService.made = 0
    yield


@pytest.fixture
def two_projects(tmp_path):
    for name in ("alpha", "beta"):
        (tmp_path / name / ".tausik").mkdir(parents=True)
    (tmp_path / "plain").mkdir()
    return tmp_path


def _answer(project_dir, notes=()):
    from gmcp_project_resolver import Resolution

    return Resolution(project_dir, "primary" if project_dir else "none", tuple(notes))


class TestPinnedModeIsUnchanged:
    """AC-6: `--project` still wins, still pins, and costs nothing extra."""

    def test_the_pinned_project_is_returned_whatever_the_cwd(self, two_projects, monkeypatch):
        reg = ServiceRegistry(str(two_projects / "alpha"), _factory)
        monkeypatch.chdir(two_projects / "beta")
        assert reg.resolve() == str(two_projects / "alpha")
        assert reg.multi_tenant is False

    def test_the_resolver_is_never_consulted_when_pinned(self, two_projects):
        def explode(*_a, **_k):
            raise AssertionError("a pinned server must not resolve anything")

        reg = ServiceRegistry(str(two_projects / "alpha"), _factory, resolver=explode)
        assert reg.for_call().project_dir == str(two_projects / "alpha")

    def test_pinned_mode_takes_no_lock_around_a_call(self, two_projects):
        """The common path must not serialise for a capability it is not using."""
        reg = ServiceRegistry(str(two_projects / "alpha"), _factory)
        before = os.getcwd()
        with reg.call_context(str(two_projects / "beta")):
            assert os.getcwd() == before, "pinned mode leaves the working directory alone"
            assert reg._lock.acquire(blocking=False), "and holds no lock"
            reg._lock.release()


class TestPerRequestResolution:
    def test_the_project_comes_from_the_resolver(self, two_projects):
        reg = ServiceRegistry(
            None, _factory, resolver=lambda *_a: _answer(str(two_projects / "beta"))
        )
        assert reg.resolve() == str(two_projects / "beta")
        assert reg.multi_tenant is True

    def test_the_primary_signal_is_passed_through_untouched(self, two_projects):
        """It is the spike's answer, not this module's: a roots URI or a host path arrives the
        same way, and neither gets a branch of its own here."""
        seen = {}

        def spy(primary, env, cwd):
            seen["primary"], seen["cwd"] = primary, cwd
            return _answer(str(two_projects / "alpha"))

        reg = ServiceRegistry(None, _factory, resolver=spy)
        reg.resolve(cwd=str(two_projects), primary_signal="file:///somewhere")
        assert seen == {"primary": "file:///somewhere", "cwd": str(two_projects)}


class TestTheCacheIsKeyedByProject:
    def test_the_same_project_reuses_one_service(self, two_projects):
        reg = ServiceRegistry(None, _factory, resolver=lambda *_a: _answer(None))
        a1 = reg.service(str(two_projects / "alpha"))
        a2 = reg.service(str(two_projects / "alpha"))
        assert a1 is a2 and _FakeService.made == 1

    def test_a_different_project_gets_its_own(self, two_projects):
        reg = ServiceRegistry(None, _factory, resolver=lambda *_a: _answer(None))
        a = reg.service(str(two_projects / "alpha"))
        b = reg.service(str(two_projects / "beta"))
        assert a is not b and _FakeService.made == 2
        assert reg.known_projects() == (
            str(two_projects / "alpha"),
            str(two_projects / "beta"),
        )

    def test_the_key_is_the_absolute_path_not_its_spelling(self, two_projects, monkeypatch):
        reg = ServiceRegistry(None, _factory, resolver=lambda *_a: _answer(None))
        monkeypatch.chdir(two_projects)
        assert reg.service(str(two_projects / "alpha")) is reg.service("alpha")
        assert _FakeService.made == 1

    def test_closing_drops_everything_even_if_one_close_fails(self, two_projects):
        reg = ServiceRegistry(None, _factory, resolver=lambda *_a: _answer(None))
        a = reg.service(str(two_projects / "alpha"))
        b = reg.service(str(two_projects / "beta"))

        def boom():
            raise RuntimeError("this one refuses")

        a.be.close = boom
        reg.close()
        assert b.be.closed is True and reg.known_projects() == ()


class TestNoProjectIsAnAnswerNotACrash:
    def test_an_unresolved_project_raises_a_message_the_agent_can_act_on(self, two_projects):
        reg = ServiceRegistry(
            None, _factory, resolver=lambda *_a: _answer(None, ("nothing at the pointer",))
        )
        with pytest.raises(ProjectUnresolved) as e:
            reg.for_call()
        text = str(e.value)
        assert "tausik init" in text and "--project" in text
        assert "nothing at the pointer" in text, "the chain's notes say what was tried"

    def test_the_message_names_both_ways_out(self):
        """Two different causes need two different actions: a directory that is not a project
        yet, and a host that started the server somewhere unrelated."""
        assert "tausik init" in NO_PROJECT_MESSAGE
        assert "open it in the editor" in NO_PROJECT_MESSAGE

    def test_a_resolved_path_without_dot_tausik_is_refused(self, two_projects):
        """AC-4, and the reason it is dangerous: the backend CREATES the database file it is
        given, so a dead directory would not raise — it would serve an empty project."""
        reg = ServiceRegistry(
            None, _factory, resolver=lambda *_a: _answer(str(two_projects / "plain"))
        )
        with pytest.raises(ProjectUnresolved, match="no .tausik"):
            reg.for_call()
        assert _FakeService.made == 0, "nothing was constructed against the dead path"

    def test_a_vanished_directory_is_refused_too(self, two_projects):
        reg = ServiceRegistry(None, _factory, resolver=lambda *_a: _answer(None))
        with pytest.raises(ProjectUnresolved):
            reg.service(str(two_projects / "was-here"))


class TestTwoProjectsInOneProcessDoNotSeeEachOther:
    """AC-5 with REAL backends and two real databases — the cache is a property, not a claim."""

    @pytest.fixture
    def real(self, tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        for name in ("alpha", "beta"):
            (tmp_path / name / ".tausik").mkdir(parents=True)

        def factory(project_dir: str):
            return ProjectService(SQLiteBackend(os.path.join(project_dir, ".tausik", "tausik.db")))

        reg = ServiceRegistry(None, factory, resolver=lambda *_a: _answer(None))
        yield reg, tmp_path
        reg.close()

    def test_a_task_added_to_one_is_invisible_in_the_other(self, real):
        reg, root = real
        a = reg.service(str(root / "alpha"))
        b = reg.service(str(root / "beta"))
        a.task_add(None, "only-in-alpha", "Alpha's task")
        assert [t["slug"] for t in a.task_list()] == ["only-in-alpha"]
        assert [t["slug"] for t in b.task_list()] == []

    def test_they_are_two_files_on_disk(self, real):
        reg, root = real
        reg.service(str(root / "alpha"))
        reg.service(str(root / "beta"))
        for name in ("alpha", "beta"):
            assert (root / name / ".tausik" / "tausik.db").is_file()

    def test_the_second_project_does_not_inherit_the_first_one_s_rows(self, real):
        """Read through sqlite3 directly: if the cache ever handed back one service for two
        directories, both files would be the same file and this would fail on the count."""
        reg, root = real
        reg.service(str(root / "alpha")).task_add(None, "a1", "one")
        reg.service(str(root / "beta")).task_add(None, "b1", "two")
        counts = []
        for name in ("alpha", "beta"):
            conn = sqlite3.connect(str(root / name / ".tausik" / "tausik.db"))
            try:
                counts.append(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])
            finally:
                conn.close()
        assert counts == [1, 1]


class TestTheWorkingDirectoryIsHeldForTheCall:
    def test_per_request_mode_moves_the_cwd_and_puts_it_back(self, two_projects, monkeypatch):
        monkeypatch.chdir(two_projects)
        reg = ServiceRegistry(None, _factory, resolver=lambda *_a: _answer(None))
        before = os.getcwd()
        with reg.call_context(str(two_projects / "alpha")):
            assert os.path.realpath(os.getcwd()) == os.path.realpath(two_projects / "alpha")
        assert os.getcwd() == before

    def test_it_is_put_back_even_when_the_call_raises(self, two_projects, monkeypatch):
        monkeypatch.chdir(two_projects)
        reg = ServiceRegistry(None, _factory, resolver=lambda *_a: _answer(None))
        before = os.getcwd()
        with pytest.raises(ValueError):
            with reg.call_context(str(two_projects / "alpha")):
                raise ValueError("tool failed")
        assert os.getcwd() == before

    def test_overlapping_calls_serialise_because_the_cwd_is_process_wide(self, two_projects):
        """The cost of tenancy on a process-global, stated as a test rather than left as a
        race: while one call holds the directory, another cannot take it."""
        reg = ServiceRegistry(None, _factory, resolver=lambda *_a: _answer(None))
        entered = threading.Event()
        blocked = threading.Event()

        def second():
            with reg.call_context(str(two_projects / "beta")):
                blocked.set()

        with reg.call_context(str(two_projects / "alpha")):
            entered.set()
            t = threading.Thread(target=second, daemon=True)
            t.start()
            assert not blocked.wait(0.3), "the second call must wait for the first"
        t.join(timeout=5)
        assert blocked.is_set(), "and proceed once the first has finished"

    def test_a_failed_chdir_releases_the_lock(self, two_projects):
        """Otherwise one bad request would hang every request after it."""
        reg = ServiceRegistry(None, _factory, resolver=lambda *_a: _answer(None))
        with pytest.raises(OSError):
            with reg.call_context(str(two_projects / "not-there")):
                pass
        assert reg._lock.acquire(blocking=False)
        reg._lock.release()


class TestTheServerStillLaunchesBothWays:
    def test_project_is_optional_in_the_parser(self):
        source = (_MCP / "server.py").read_text(encoding="utf-8")
        assert '"--project",' in source and "default=None" in source
        assert "required=True" not in source

    def test_the_startup_chdir_only_happens_when_pinned(self):
        source = (_MCP / "server.py").read_text(encoding="utf-8")
        head = source.index("if args.project is not None:")
        assert "os.chdir(args.project)" in source[head : head + 600]

    def test_the_dispatcher_answers_an_unresolved_project_instead_of_raising(self):
        source = (_MCP / "server.py").read_text(encoding="utf-8")
        assert "except ProjectUnresolved" in source
        assert "registry.call_context(project_dir)" in source
