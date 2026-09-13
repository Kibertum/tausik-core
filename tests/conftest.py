"""TAUSIK test configuration."""

import hashlib
import os

import pytest
from unittest.mock import patch

from verify_first_compat_predicate import should_apply_verify_first_autouse_compat_shim


@pytest.fixture(autouse=True)
def _isolate_shared_knowledge_home(tmp_path_factory, monkeypatch):
    """Point TAUSIK_HOME at a per-test directory, for EVERY test.

    The shared knowledge store lives in the developer's home directory and is
    now read by `memory_search` and by both knowledge aggregates. Without this,
    any test asserting "the block is empty" or "search found N rows" quietly
    starts depending on what the person running it happens to have shared —
    green on a fresh checkout, red once they use `--global` even once, and the
    failure would point at the wrong code.

    Autouse and global rather than per-file: the read path can be reached from
    anywhere that renders memory, so opting individual files in would be a list
    someone has to remember to extend. This is the same reasoning that put the
    projection behind a proven address rather than a path shape.

    A directory is handed over rather than left unset, because an unset
    TAUSIK_HOME resolves to the REAL `~/.tausik`.
    """
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path_factory.mktemp("tausik_home")))


@pytest.fixture(autouse=True)
def _mock_run_gates():
    """Mock gate_runner.run_gates to prevent pytest-in-pytest recursion.

    Tests that need to test gate behavior should use their own
    patch.dict("sys.modules", ...) to override this.
    """
    with patch("gate_runner.run_gates", return_value=(True, [])):
        yield


@pytest.fixture(autouse=True)
def _verify_first_autouse_compat_shim(request, monkeypatch):
    """Bridge legacy tests into v1.4 Verify-First without rewriting the suite.

    **Product contract.** With ``task_done.auto_verify`` left at default
    ``false``, ``task_done`` requires a fresh green from ``tausik verify`` in
    ``verification_runs``. Most unit tests call ``task_done`` without seeding
    that cache.

    **Shim (this fixture).** When `should_apply_verify_first_autouse_compat_shim`
    is true for ``request.node``, patch ``GatesMixin._enforce_verify_first`` to
    a no-op so those tests keep passing.

    **Opt-in to real enforcement.** Declare ``@pytest.mark.verify_first`` on a
    test (or class). The shim is then skipped; see `verify_first_compat_predicate`
    and `docs/en/verify-glossary.md` (test shim).

    **Why patch the method, not config.** Tests legitimately tweak
    ``load_config()`` for unrelated keys (TTL, idle thresholds); mocking the
    whole config globally would regress them.
    """
    if not should_apply_verify_first_autouse_compat_shim(request.node):
        yield
        return

    try:
        from service_gates import GatesMixin

        def _noop(self, report, slug, relevant_files, **kwargs):
            # **kwargs so the shim tolerates keyword-only extensions of the real
            # signature (e.g. no_file_changes) without every unit test needing
            # the marker — qg2-cannot-close-fileless-task.
            return None

        monkeypatch.setattr(GatesMixin, "_enforce_verify_first", _noop)

        # changelog-continuous-gate: the continuous-CHANGELOG gate is the same
        # class of task-done-path enforcement as Verify-First — it reads the
        # live project config (now `changelog_gate.enabled=true`) and would
        # block every legacy `task_done` test that doesn't happen to leave both
        # changelog files dirty. Same shim, same opt-out marker.
        def _noop_changelog(self, report, slug, relevant_files=None, **kwargs):
            # relevant_files became positional when gate-registry-single-source
            # gave every post-scope gate one call shape; defaulted so direct
            # callers that predate it keep working.
            return None

        monkeypatch.setattr(GatesMixin, "_enforce_changelog", _noop_changelog)
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        pass
    yield


@pytest.fixture(autouse=True)
def _isolated_config_trust_tiers(tmp_path_factory, monkeypatch):
    """Point the user/managed config tiers at throwaway paths for every test.

    `load_config` merges ~/.tausik/config.json on top of the project config, so
    without this a dev who keeps a real user-tier file would get different
    results from CI — the suite would silently measure their machine.
    """
    tier_dir = tmp_path_factory.mktemp("config_tiers")
    monkeypatch.setenv("TAUSIK_USER_CONFIG", str(tier_dir / "user.json"))
    monkeypatch.delenv("TAUSIK_MANAGED_CONFIG", raising=False)
    yield


_LIVE_PROJECT_CONFIG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".tausik", "config.json")
)


def _live_project_config_fingerprint() -> str | None:
    """sha256 of the live project config, or ``None`` when it does not exist.

    Absence is not drift: a fresh clone and CI have no `.tausik/config.json` at
    all, and a guard that demands a file which need not exist gets disabled the
    first time it fires. Absence turning into presence IS drift — a test that
    creates the file created it in the wrong project.
    """
    try:
        with open(_LIVE_PROJECT_CONFIG, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


@pytest.fixture(autouse=True)
def _guard_live_project_config():
    """Fail any test that writes into the REAL project's `.tausik/config.json`.

    Found the hard way (`mcp-gate-toggle-mutates-real-project-config`): an MCP
    handler took a `ProjectService` built on `tmp_path`, ignored it, resolved
    the config from the cwd, and enabled a gate in the developer's own project.
    The test stayed green and `git status` stayed clean — `.tausik/` is
    gitignored — so the only visible symptom was a WinError 32 when two suites
    ran at once, which reads exactly like a flake.

    What makes that class worth a mechanical guard rather than a one-off fix
    (memory #236) is WHAT gets written: the set of enabled gates, i.e. the thing
    the project is checked WITH. The same code path that enables a gate can
    disable one, and then the project silently verifies less than it reports.
    A defect that rewrites the evidence of itself has to be caught by something
    that does not depend on anyone noticing.

    Scope is deliberately the config alone, not all of `.tausik/`: the database
    and caches have legitimate writers in this repo, and a guard that cries
    about those would be turned off within a week.
    """
    before = _live_project_config_fingerprint()
    yield
    after = _live_project_config_fingerprint()
    if after == before:
        return
    if before is None:
        detail = "the test CREATED it (it did not exist before the test)"
    elif after is None:
        detail = "the test DELETED it"
    else:
        detail = f"content changed ({before[:12]} -> {after[:12]})"
    pytest.fail(
        f"Test mutated the live project config {_LIVE_PROJECT_CONFIG}: {detail}.\n"
        "A test must write only into its own tmp_path. This usually means a "
        "code path took a project handle (ProjectService / TAUSIK_DIR) and "
        "resolved the path from the cwd instead -- see "
        "project_service.ProjectService.tausik_dir for the fix pattern. "
        "(ASCII only: this text is read in consoles that mangle non-ASCII.)",
        pytrace=False,
    )


def canonical_ddl(table: str) -> str:
    """Вырезать CREATE TABLE <table> из backend_schema.SCHEMA_SQL.

    Единственный источник DDL для тестовых фикстур. Рукописные копии схемы
    verification_runs уже дважды стоили дорого: сначала добавление двух колонок
    в v38 потребовало ручной правки девяти блоков (задача
    test-ddl-drift-verification-runs), затем в сессии #119 фикстура без
    CHECK(scope IN (...)) дала 20 зелёных тестов при фиче, которая падала
    IntegrityError на КАЖДОЙ записи в живую БД.

    Копия схемы в тесте доказывает соответствие копии, а не продакшену, и
    расходится молча — поэтому её здесь быть не должно.
    """
    import os
    import sys

    scripts = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from backend_schema import SCHEMA_SQL

    marker = f"CREATE TABLE IF NOT EXISTS {table}"
    start = SCHEMA_SQL.index(marker)
    end = SCHEMA_SQL.index("\n);", start) + len("\n);")
    return SCHEMA_SQL[start:end]


VERIFICATION_RUNS_DDL = canonical_ddl("verification_runs")


# --- the project's own state, from GIT rather than from a working copy --------
#
# Both helpers exist for one reason, measured in session #203: a control that
# reads `.tausik/tausik.db` does not run where the project is merely CHECKED
# OUT. CI clones and runs `bootstrap.py`, which does NOT create that database —
# verified by running the CI step in a clean `git worktree` — so eleven test
# instances across four files skipped, and every one of them skipped SILENTLY.
#
# Worse than "never runs": it was not even deterministic. Some test in the suite
# creates `.tausik/tausik.db` in the repo root as it goes, so a DB-gated control
# ran or skipped depending on whether it was scheduled before or after that
# test — under `-n auto` and random order, a coin toss. A ratchet that sometimes
# checks nothing and always reports green is worse than one that is switched
# off, because the green is believed.
#
# The cut is between two genuinely different questions. "What does THIS PROJECT
# declare?" is answered by git and must run everywhere. "What does THIS WORKING
# COPY currently hold?" needs a live database and is honestly dormant in a
# checkout — but it must say so out loud, which is what
# `tests/test_no_silent_db_gated_skips.py` enforces.


#: The public snapshot (decision #368) is the tracked tree MINUS the state
#: projection and three internal files. A control whose SUBJECT is one of the
#: excluded files — the GitLab pipeline, the release charter, a task's journal —
#: has nothing to measure on that tree and says so with THIS reason, rostered
#: like the DB-gated skips so the dormancy is declared, not silent. The
#: predicate is the projection's own directory: a checkout without
#: `tausik/tasks/` is a snapshot, a checkout with it is the development line.
IS_PUBLIC_SNAPSHOT = not os.path.isdir(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tausik", "tasks")
)
DORMANT_ON_PUBLIC_SNAPSHOT = (
    "this checkout is the PUBLIC SNAPSHOT (decision #368): the state projection, "
    "TODO.md, TAUSIK-plan-1.9.md and .gitlab-ci.yml stay on the development line, "
    "so this control — whose subject is one of them — is DORMANT here, not passing."
)

#: The ONE reason string every control allowed to need a live database must
#: give. A shared constant rather than a phrase each site retypes: the group in
#: `test_claudemd_state_gate.py` went unnoticed for exactly that reason — it
#: worded its skip differently from the others, so a grep for one phrase found
#: three sites and missed seven. `test_no_silent_db_gated_skips.py` checks that
#: this NAME is what the site cites, which no rewording can slip past.
DORMANT_WITHOUT_LIVE_DB = (
    "no .tausik/tausik.db in this checkout — this control is DORMANT here, not "
    "passing. Its subject is the LIVE working copy, so a bare checkout has "
    "nothing for it to measure. Rostered in tests/test_no_silent_db_gated_skips.py."
)


def canonical_schema_db():
    """An in-memory connection carrying the schema a fresh install gets.

    The same `init_schema` a real `tausik init` runs, so this IS the database
    our declarations are made about — and it is built from git, not inherited
    from whatever a developer's machine happens to hold. Measured equivalent to
    the live database when introduced: both yielded the same 30 artifact
    classes, zero difference either way.

    Preferable to the live database rather than merely equal to it: the live one
    carries residual state, and a control that reads residue tells you about the
    machine it ran on instead of about the project.
    """
    import sqlite3
    import sys

    scripts = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from backend_init import init_schema

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    return conn


def canonical_schema_db_file(path):
    """`canonical_schema_db`, but on disk — for a control that needs a DB PATH.

    Same `init_schema` from git, same argument: a gate that resolves
    `.tausik/tausik.db` and opens it by name cannot be handed an in-memory
    connection, and handing it the LIVE database makes the control report on the
    machine it ran on. A checkout without one is exactly where that showed:
    `gate_state_roundtrip` answers NOT_APPLICABLE / no_database before it ever
    reaches its detector, so tests that drop that detector to prove the runner
    records non-execution never reached it either, and went red in a bare
    checkout (four-tests-fail-in-a-bare-checkout).
    """
    import sqlite3
    import sys

    scripts = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from backend_init import init_schema

    conn = sqlite3.connect(str(path))
    try:
        init_schema(conn)
        conn.commit()
    finally:
        conn.close()
    return str(path)


def projected_task_status(slug: str) -> str | None:
    """A task's status from the git-tracked `tausik/` projection, or None.

    The projection is committed precisely so project state survives outside the
    gitignored database — `.gitignore` says as much — so a ratchet asking "is
    the task this caveat names still open?" has a source that exists in every
    checkout. Parsed with the emitter's own `state_parse.parse_frontmatter`
    rather than a second reader: a private copy of a format drifts from it
    silently, and this file already carries that lesson for DDL.

    None means the projection holds no such task — which is a real answer (the
    slug names nothing), not an excuse to skip.
    """
    import sys

    scripts = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from state_parse import parse_frontmatter

    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "tausik", "tasks", f"{slug}.md")
    )
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if not text.startswith("---"):
        return None
    status = parse_frontmatter(text.split("---", 2)[1]).get("status")
    return str(status) if status is not None else None


# --- hang guard: the threshold is checked against THIS run, not against a memory ---
#
# See tests/hang_guard_contract.py for why. In short: the promise beside
# faulthandler_timeout was calibrated on the fast lane, went false on the full
# lane, and stayed green for months because both sides of the comparison were
# frozen constants. These hooks feed the check the duration the running suite
# actually produced, so drift toward the threshold reddens the run BEFORE the
# guard starts killing healthy tests.

_slowest_by_nodeid: dict[str, float] = {}


class _NoRedHistory:
    """Заглушка на случай, когда модуля нет: наблюдение не смеет ронять прогон."""

    @staticmethod
    def pytest_runtest_logreport(report):
        pass

    @staticmethod
    def pytest_sessionfinish(session, exitstatus):
        pass


def _red_history_plugin():
    """Модуль записи красной истории, или заглушка.

    Импорт внутри функции и обёрнут: conftest грузится на каждый прогон, а
    наблюдение обязано быть тише самого прогона.
    """
    try:
        import red_history_plugin

        return red_history_plugin
    except Exception:  # noqa: BLE001 — наблюдение не смеет ронять прогон
        return _NoRedHistory


def pytest_runtest_logreport(report):
    """Accumulate setup+call+teardown per test.

    Summed, not maxed, because pytest's faulthandler arms its timer around the
    whole item protocol — so the window the guard watches is the sum, and
    comparing against the call phase alone would flatter us.

    Under xdist this fires on the CONTROLLER for every worker's report, so one
    process sees the whole tree; the per-worker duplicate is suppressed below.
    """
    _slowest_by_nodeid[report.nodeid] = _slowest_by_nodeid.get(report.nodeid, 0.0) + report.duration
    _red_history_plugin().pytest_runtest_logreport(report)


def _hang_guard_breach(config) -> str | None:
    """None, or the message explaining that the declared margin is gone."""
    if hasattr(config, "workerinput"):
        return None  # xdist worker: the controller has every report, it checks once
    if not _slowest_by_nodeid:
        return None  # --collect-only, or a run that executed nothing
    from hang_guard_contract import headroom_breach

    nodeid, seconds = max(_slowest_by_nodeid.items(), key=lambda kv: kv[1])
    try:
        timeout = float(config.getini("faulthandler_timeout") or 0.0)
    except ValueError:
        return None  # pytest too old to know the key; test_pytest_hang_guard says so
    return headroom_breach(timeout, nodeid, seconds)


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    breach = _hang_guard_breach(config)
    if breach is not None:
        terminalreporter.section("hang guard headroom", sep="=", red=True, bold=True)
        terminalreporter.write_line(breach)


def pytest_sessionfinish(session, exitstatus):
    """Turn the breach into a non-zero exit.

    `wrap_session` returns `session.exitstatus` AFTER this hook runs, so mutating
    it here is what makes the warning bite. A message alone would scroll past —
    that is how the previous version of this problem survived three sessions.
    """
    if session.exitstatus == 0 and _hang_guard_breach(session.config) is not None:
        session.exitstatus = 1
    _red_history_plugin().pytest_sessionfinish(session, exitstatus)


# --------------------------------------------------------------------------
# Finding a bash that can actually RUN a script.
#
# `subprocess.run(["bash", "./probe.sh"])` reads as "use bash". On
# `windows-latest` the first `bash` on PATH is `System32\bash.exe`, the WSL
# launcher — and with no distribution installed it exits 1 and prints, in
# UTF-16, that there are no distributions. Three Windows lanes went red on
# 2026-08-25 for that reason and stayed red for nine days while ubuntu, macos,
# lint and the full lane were all green. The tests were not wrong about the
# product; they were wrong about which program the name `bash` denotes.
#
# So the name is not trusted: each candidate is PROBED by running a real script
# file from a real working directory — the exact shape the callers use — and the
# first one that produces the expected output wins. The WSL launcher fails that
# probe by construction, which is why nothing here has to recognise it by name
# or by the text of its error message. A host with no usable bash yields None
# and the caller SKIPS, rather than going red about someone else's tooling.
# --------------------------------------------------------------------------

_BASH_PROBE_TOKEN = "tausik-posix-bash-ok"


def _bash_candidates():
    """Every plausible bash, Git's own first on Windows.

    Git Bash leads because these tests were written against it and because a
    WSL launcher WITH a distribution installed would pass the probe while
    running in a different filesystem namespace. Ordering states the preference;
    the probe still decides.
    """
    import shutil

    seen: list[str] = []

    def add(path):
        if path and path not in seen and os.path.exists(path):
            seen.append(path)

    git = shutil.which("git")
    if git:
        git_root = os.path.dirname(os.path.dirname(os.path.abspath(git)))
        for rel in (("bin", "bash.exe"), ("usr", "bin", "bash.exe"), ("bin", "bash")):
            add(os.path.join(git_root, *rel))

    for entry in (os.environ.get("PATH") or "").split(os.pathsep):
        if not entry:
            continue
        for name in ("bash.exe", "bash"):
            add(os.path.join(entry, name))
    return seen


def _bash_runs_a_script(candidate):
    """True when `candidate` executes a script file named relatively."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as work:
        probe = os.path.join(work, "_bash_probe.sh")
        with open(probe, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("printf '%s' " + _BASH_PROBE_TOKEN + "\n")
        try:
            out = subprocess.run(
                [candidate, "./_bash_probe.sh"],
                cwd=work,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return False
    return out.returncode == 0 and out.stdout.strip() == _BASH_PROBE_TOKEN


_POSIX_BASH_CACHE: list = []


def posix_bash():
    """A bash that runs script files, or None when the host has none.

    Cached: the probe spawns a process, and it is asked once per test.
    """
    if not _POSIX_BASH_CACHE:
        found = None
        for candidate in _bash_candidates():
            if _bash_runs_a_script(candidate):
                found = candidate
                break
        _POSIX_BASH_CACHE.append(found)
    return _POSIX_BASH_CACHE[0]


def require_posix_bash():
    """`posix_bash()`, or skip the test with a reason naming what was tried."""
    found = posix_bash()
    if found is None:
        pytest.skip(
            "no bash on this host runs a script file "
            "(tried: " + ", ".join(_bash_candidates() or ["<none on PATH>"]) + ")"
        )
    return found


# --- observed coverage: which test actually reached which file ---------------
#
# OFF unless TAUSIK_OBSERVE_COVERAGE is set, and the ordinary run must not pay
# for a graph it is not building. When on, the profiler is installed around the
# CALL phase of each test — not around setup and teardown, whose reach belongs
# to fixtures shared by many tests and would relate every artifact to
# everything.
#
# The import is inside the hook rather than at module scope: `conftest` is
# imported for every run, and a module the ordinary run never uses should not
# be loaded by it.


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    try:
        import observed_coverage
    except Exception:  # noqa: BLE001 — observation must never break a run
        yield
        return

    if not observed_coverage.is_enabled():
        yield
        return

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    observer = observed_coverage.Observer(root)
    observer.start()
    try:
        yield
    finally:
        touched = observer.stop()
        observed_coverage.record(observed_coverage.output_path(root), item.nodeid, touched)


# --- red history: which nodes have ever been observed FAILING ----------------
#
# RENAR 9.18.2. Author isolation proves the test was written before the code; it
# does not prove the test CHECKS anything. A node seen red at least once has
# demonstrated it can tell one state of the world from another.
#
# CALLED FROM THE EXISTING HOOKS, NOT IMPORTED AS NEW ONES. The first version
# did `from red_history_plugin import pytest_runtest_logreport,
# pytest_sessionfinish` — and both names ALREADY EXIST in this file, so the
# import silently replaced the hang-guard accumulator and the breach exit code.
# ruff caught it (F811); nothing else would have, and the loss would have been
# two working mechanisms in exchange for a new one. Delegation keeps all three.
