"""Tests for l26-verify-git-diff-wire — the receipt must be honest about its scope.

The divergence between declared `relevant_files` and what git says actually
changed was detected since v1.3.4 but discarded: it gated the verify cache and
nothing else, so `record_run` still signed a receipt for the narrow declared
scope. These tests pin the three properties that fix requires:

  AC #2 — divergence is persisted on the run row AND inside the signed receipt.
  AC #3 — an honest closure that edits docs/CHANGELOG beyond relevant_files is
          NOT blocked (this is ~100% of real closures — Decision #138/#139).
  AC #4 — a dishonest closure is readable from the receipt itself.
  AC #5 — no git / empty relevant_files / no task_created_at / git failure all
          degrade to "unknown", never to "complete".
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import types

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
from backend_schema_gate_runs import GATE_RUNS_SQL  # noqa: E402
import crypto_sign  # noqa: E402
import gate_runner  # noqa: E402
import service_verification as sv  # noqa: E402
import verify_cached_run as vcr  # noqa: E402
import verify_scope_honesty as vsh  # noqa: E402
from conftest import VERIFICATION_RUNS_DDL  # noqa: E402
from verify_own_export import own_export_display, parent_story_abspath  # noqa: E402

# The verification_runs baseline cut straight out of backend_schema.SCHEMA_SQL
# by conftest.canonical_ddl — no longer hand-rolled, so it cannot drift away
# from production behind a green test (`test-ddl-drift-verification-runs`).
_DDL = VERIFICATION_RUNS_DDL + ";"

_GATES = [{"name": "pytest", "passed": True, "severity": "block"}]

# The actual undeclared set from both closures of session #112. Both were
# honest: CHANGELOG/README/docs/generated-constants/IDE-mirror edits made
# beyond the declared relevant_files. Any rule that blocks on this set is a
# rule that would be disabled on first contact.
SESSION_112_UNDECLARED = [
    "CHANGELOG.md",
    "CHANGELOG.ru.md",
    "README.md",
    "README.ru.md",
    "docs/_generated/constants.json",
    "docs/en/config-trust-tiers.md",
    "docs/ru/config-trust-tiers.md",
    ".claude/scripts/session_metrics.py",
    ".cursor/scripts/session_metrics.py",
    "scripts/hooks/session_metrics.py",
    "scripts/hooks/token_metrics.py",
    "scripts/hooks/token_rows.py",
]


def _git_root(tmp_path):
    (tmp_path / ".git").mkdir()
    return str(tmp_path)


TS = "2026-01-01T00:00:00Z"

# The task under test and a source file it honestly declared. `FOREIGN_SLUG` is
# somebody else's export: the subtraction must not reach it (Decision #283).
OWN_SLUG = "scope-honesty-counts-a-tasks-own-export-as-undeclared"
FOREIGN_SLUG = "nine-open-tasks-are-invisible-to-release-scope"
SOURCE = "scripts/verify_scope_honesty.py"


def _runner(log_files=(), diff_files=(), returncode=0):
    """Fake `subprocess.run` for git: first call is `log`, second is `diff`."""

    def run(cmd, **_kw):
        payload = log_files if "log" in cmd else diff_files
        return types.SimpleNamespace(returncode=returncode, stdout="\n".join(payload))

    return run


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_DDL)
    c.executescript(GATE_RUNS_SQL)  # canonical DDL — record_run also writes gate_runs
    yield c
    c.close()


class TestTriState:
    """`unknown` and `complete` are different claims and must never collapse."""

    def test_missing_task_created_at_is_unknown(self, tmp_path):
        d = vsh.describe_declared_scope(["a.py"], None, root=_git_root(tmp_path))
        assert d["status"] == vsh.STATUS_UNKNOWN
        assert d["undeclared"] == []

    def test_empty_declared_files_is_unknown(self, tmp_path):
        d = vsh.describe_declared_scope([], "2026-01-01T00:00:00Z", root=_git_root(tmp_path))
        assert d["status"] == vsh.STATUS_UNKNOWN

    def test_declared_list_of_blanks_is_unknown(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["", "  "], "2026-01-01T00:00:00Z", root=_git_root(tmp_path)
        )
        assert d["status"] == vsh.STATUS_UNKNOWN

    def test_not_a_git_repo_is_unknown(self, tmp_path):
        # No .git directory — changed_files_since returns None.
        d = vsh.describe_declared_scope(["a.py"], "2026-01-01T00:00:00Z", root=str(tmp_path))
        assert d["status"] == vsh.STATUS_UNKNOWN
        assert d["reason"] == "git unavailable"

    def test_git_failure_is_unknown_not_complete(self, tmp_path):
        """A failing git call must not be read as 'declared scope was fine'."""
        d = vsh.describe_declared_scope(
            ["a.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["b.py"], ["c.py"], returncode=1),
        )
        assert d["status"] == vsh.STATUS_UNKNOWN

    def test_exact_match_is_complete(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["a.py", "b.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["a.py"], ["b.py"]),
        )
        assert d["status"] == vsh.STATUS_COMPLETE
        assert d["undeclared_count"] == 0

    def test_over_declaration_is_complete(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["a.py", "b.py", "extra.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["a.py"], ["b.py"]),
        )
        assert d["status"] == vsh.STATUS_COMPLETE

    def test_no_git_visible_changes_is_complete(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["a.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner([], []),
        )
        assert d["status"] == vsh.STATUS_COMPLETE

    def test_under_declaration_lists_missing_files_sorted(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["a.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["z.py", "m.py"], ["a.py"]),
        )
        assert d["status"] == vsh.STATUS_UNDER_DECLARED
        assert d["undeclared"] == ["m.py", "z.py"]
        assert d["undeclared_count"] == 2

    def test_backslash_declared_paths_normalize(self, tmp_path):
        """Windows-style declared paths must match git's forward slashes."""
        d = vsh.describe_declared_scope(
            [r"scripts\a.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["scripts/a.py"], []),
        )
        assert d["status"] == vsh.STATUS_COMPLETE

    def test_listing_is_capped_but_count_is_not(self, tmp_path):
        many = [f"f{i:03d}.py" for i in range(vsh.MAX_LISTED_UNDECLARED + 25)]
        d = vsh.describe_declared_scope(
            ["declared.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(many, []),
        )
        assert len(d["undeclared"]) == vsh.MAX_LISTED_UNDECLARED
        assert d["undeclared_count"] == len(many)


class TestSecurityBlock:
    """Divergence never blocks; undeclared security-sensitive files do."""

    def test_complete_scope_does_not_block(self):
        assert vsh.security_block_reason({"status": "complete", "security_undeclared": []}) is None

    def test_none_description_does_not_block(self):
        assert vsh.security_block_reason(None) is None

    def test_session_112_honest_closure_does_not_block(self, tmp_path):
        """AC #3 — the measured real-world case. This must stay non-blocking."""
        d = vsh.describe_declared_scope(
            ["scripts/config_trust.py", "tests/test_config_trust.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(SESSION_112_UNDECLARED, []),
        )
        assert d["status"] == vsh.STATUS_UNDER_DECLARED  # divergence IS detected
        assert d["security_undeclared"] == []  # ...and does NOT block
        assert vsh.security_block_reason(d) is None

    def test_undeclared_auth_file_blocks(self, tmp_path):
        """AC #4/(в) — the one case where the scoped gates would verify nothing."""
        d = vsh.describe_declared_scope(
            ["README.md"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["src/auth.py", "README.md"], []),
        )
        reason = vsh.security_block_reason(d)
        assert reason is not None
        assert "src/auth.py" in reason
        assert "relevant_files" in reason

    def test_undeclared_credential_extension_blocks(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["README.md"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner([".env"], []),
        )
        assert vsh.security_block_reason(d) is not None

    def test_declared_security_file_does_not_block(self, tmp_path):
        """Declaring the auth file is the whole point — that must pass."""
        d = vsh.describe_declared_scope(
            ["src/auth.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["src/auth.py"], []),
        )
        assert vsh.security_block_reason(d) is None


class TestRecordRunPersistsScope:
    """AC #2 — the divergence stops being transient."""

    def _record(self, conn, project_dir, desc):
        return sv.record_run(
            conn,
            task_slug="task-a",
            scope="standard",
            command="trigger=verify|sig=x|files=README.md",
            exit_code=0,
            summary="ok",
            files_hash="h" * 64,
            gate_results=_GATES,
            project_dir=project_dir,
            scope_description=desc,
        )

    def test_status_and_undeclared_persisted_on_row(self, conn, tmp_path):
        desc = {
            "status": vsh.STATUS_UNDER_DECLARED,
            "undeclared": ["scripts/x.py"],
            "undeclared_count": 1,
        }
        rid = self._record(conn, str(tmp_path), desc)
        row = conn.execute(
            "SELECT declared_scope_status, undeclared_files FROM verification_runs WHERE id=?",
            (rid,),
        ).fetchone()
        assert row["declared_scope_status"] == vsh.STATUS_UNDER_DECLARED
        assert json.loads(row["undeclared_files"]) == ["scripts/x.py"]

    def test_omitted_description_records_unknown_not_complete(self, conn, tmp_path):
        """AC #5 — saying nothing must not buy a clean bill of health."""
        rid = self._record(conn, str(tmp_path), None)
        row = conn.execute(
            "SELECT declared_scope_status FROM verification_runs WHERE id=?", (rid,)
        ).fetchone()
        assert row["declared_scope_status"] == vsh.STATUS_UNKNOWN

    def test_receipt_carries_divergence_and_stays_verifiable(self, conn, tmp_path):
        """AC #2 + AC #4 — read the divergence back out of the SIGNED receipt."""
        crypto_keys.init_keys(str(tmp_path))
        desc = {
            "status": vsh.STATUS_UNDER_DECLARED,
            "undeclared": ["scripts/service_gates.py"],
            "undeclared_count": 1,
        }
        rid = self._record(conn, str(tmp_path), desc)
        raw = conn.execute(
            "SELECT receipt_json FROM verification_runs WHERE id=?", (rid,)
        ).fetchone()["receipt_json"]
        envelope = json.loads(raw)
        receipt = envelope["receipt"]

        # The proof itself now says its coverage was narrower than the change.
        assert receipt["declared_scope_status"] == vsh.STATUS_UNDER_DECLARED
        assert receipt["undeclared_files"] == ["scripts/service_gates.py"]
        assert receipt["undeclared_count"] == 1
        # ...and adding those fields did not break the signature.
        assert crypto_sign.verify_receipt(envelope, project_dir=str(tmp_path)) is True

    def test_receipt_states_unknown_when_not_measured(self, conn, tmp_path):
        crypto_keys.init_keys(str(tmp_path))
        rid = self._record(conn, str(tmp_path), None)
        raw = conn.execute(
            "SELECT receipt_json FROM verification_runs WHERE id=?", (rid,)
        ).fetchone()["receipt_json"]
        receipt = json.loads(raw)["receipt"]
        assert receipt["declared_scope_status"] == vsh.STATUS_UNKNOWN
        assert receipt["undeclared_files"] == []


class TestRunGatesWithCacheIntegration:
    """End-to-end through the path `task done` actually takes."""

    @pytest.fixture(autouse=True)
    def _stub_gates(self, monkeypatch):
        monkeypatch.setattr(
            gate_runner,
            "run_gates",
            lambda *a, **k: (True, [{"name": "pytest", "passed": True, "skipped": False}]),
        )

    def test_honest_under_declaration_is_not_blocked(self, conn, monkeypatch):
        """AC #3 — reproduces both session #112 closures end-to-end."""
        monkeypatch.setattr(
            # Патчить надо модуль, который ЗОВЁТ функцию, а не фасад, который
            # её только реэкспортирует: `from X import Y` связывает имя при
            # импорте. До извлечения verify_cached_run обе точки совпадали.
            vcr,
            "describe_declared_scope",
            lambda files, created_at, **kw: {
                "status": vsh.STATUS_UNDER_DECLARED,
                "reason": "test",
                "undeclared": SESSION_112_UNDECLARED,
                "undeclared_count": len(SESSION_112_UNDECLARED),
                "security_undeclared": [],
            },
        )
        notes: list[str] = []
        passed, results, status = sv.run_gates_with_cache(
            conn,
            "task-a",
            ["scripts/config_trust.py"],
            append_notes_fn=lambda _s, m: notes.append(m),
            task_created_at="2026-01-01T00:00:00Z",
        )
        assert passed is True
        assert status == "git-mismatch"  # detected...
        assert any("WARN" in n for n in notes)  # ...reported...
        # ...and the recorded row tells the truth about its own coverage.
        row = conn.execute(
            "SELECT declared_scope_status, undeclared_files FROM verification_runs "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row["declared_scope_status"] == vsh.STATUS_UNDER_DECLARED
        assert "CHANGELOG.md" in json.loads(row["undeclared_files"])

    def test_undeclared_security_file_blocks_before_gates_run(self, conn, monkeypatch):
        """AC #4 — the half of the v1.3.4 hole that refusing the cache left open."""
        monkeypatch.setattr(
            # Патчить надо модуль, который ЗОВЁТ функцию, а не фасад, который
            # её только реэкспортирует: `from X import Y` связывает имя при
            # импорте. До извлечения verify_cached_run обе точки совпадали.
            vcr,
            "describe_declared_scope",
            lambda files, created_at, **kw: {
                "status": vsh.STATUS_UNDER_DECLARED,
                "reason": "test",
                "undeclared": ["src/auth.py"],
                "undeclared_count": 1,
                "security_undeclared": ["src/auth.py"],
            },
        )
        ran: list[bool] = []
        monkeypatch.setattr(
            gate_runner, "run_gates", lambda *a, **k: (ran.append(True), (True, []))[1]
        )
        notes: list[str] = []
        passed, results, status = sv.run_gates_with_cache(
            conn,
            "task-a",
            ["README.md"],
            append_notes_fn=lambda _s, m: notes.append(m),
            task_created_at="2026-01-01T00:00:00Z",
        )
        assert passed is False
        assert status == "scope-security-mismatch"
        assert results[0]["name"] == "scope-declaration"
        assert results[0]["severity"] == "block"
        assert ran == []  # fail fast: no point running gates on a scope we reject
        assert any("src/auth.py" in n for n in notes)

    def test_recording_names_whose_export_to_subtract(self, conn, monkeypatch):
        """Decision #283 — the recording half of the wiring.

        `run_gates_with_cache` already subtracts this task's own export from
        the coverage it HASHES (`coverage_files(files, slug)`); the scope
        description sitting three lines below it used to be asked without the
        slug, so the row and the receipt called under-declared the very file the
        hash had agreed to ignore. Only the argument is pinned here — the
        subtraction is `verify_scope_honesty`'s and is tested against a real
        projection above.
        """
        seen: dict = {}

        def _record(files, created_at, **kw):
            seen.update(kw)
            return {
                "status": vsh.STATUS_COMPLETE,
                "reason": "test",
                "undeclared": [],
                "undeclared_count": 0,
                "security_undeclared": [],
            }

        monkeypatch.setattr(vcr, "describe_declared_scope", _record)
        passed, _results, _status = sv.run_gates_with_cache(
            conn, "task-a", ["a.py"], task_created_at="2026-01-01T00:00:00Z"
        )
        assert passed is True
        assert seen.get("task_slug") == "task-a"

    def test_unknown_scope_still_records_a_row(self, conn, monkeypatch):
        """AC #5 — degradation is explicit, not a missing row or a silent 'complete'."""
        monkeypatch.setattr(
            # Патчить надо модуль, который ЗОВЁТ функцию, а не фасад, который
            # её только реэкспортирует: `from X import Y` связывает имя при
            # импорте. До извлечения verify_cached_run обе точки совпадали.
            vcr,
            "describe_declared_scope",
            lambda files, created_at, **kw: {
                "status": vsh.STATUS_UNKNOWN,
                "reason": "git unavailable",
                "undeclared": [],
                "undeclared_count": 0,
                "security_undeclared": [],
            },
        )
        passed, _results, status = sv.run_gates_with_cache(
            conn, "task-a", ["a.py"], task_created_at="2026-01-01T00:00:00Z"
        )
        assert passed is True
        assert status in {"miss", "hit"}
        row = conn.execute(
            "SELECT declared_scope_status FROM verification_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row["declared_scope_status"] == vsh.STATUS_UNKNOWN


class TestOwnExportIsNotUndeclared:
    """Decision #283 — a task's own export is bookkeeping, not the agent's work.

    MEASURED, session #195: the verify of `#1892` printed "NOTE: 1 file(s)
    changed since task start but not declared in relevant_files", and that one
    file was `tausik/tasks/<slug>.md` — written by the exporter, from
    `task start` and from every `task log`. So `under-declared` was the verdict
    on essentially every honest close and `complete` was unreachable by
    construction: the ~100%-firing rule Decision #138 already refuses to ship,
    this time with the verdict signed into the receipt.

    The address is never spelled here either: the tests ask `own_export_display`
    where the file goes, so a moved projection moves the test with the code
    instead of leaving a green test about a path that no longer exists (#249).
    """

    @pytest.fixture
    def project(self, tmp_path, monkeypatch):
        """A git root that is ALSO a project, so the export address resolves.

        Both halves are real rather than stubbed: `changed_files_since` refuses
        a directory without `.git`, and `own_export_abspath` walks up from the
        cwd to a real `.tausik/`. A monkeypatched resolver on either side would
        test the test.
        """
        (tmp_path / ".git").mkdir()
        (tmp_path / ".tausik").mkdir()
        monkeypatch.chdir(tmp_path)
        return str(tmp_path)

    @staticmethod
    def _export(project, slug):
        rel = own_export_display(slug, root=project)
        assert rel and not rel.startswith(".."), "projection root must resolve"
        return rel

    def test_before_and_after_on_one_input(self, project):
        """AC3 — the two numbers side by side, same input, same runner."""
        own = self._export(project, OWN_SLUG)
        args = ([SOURCE], TS)
        kwargs = dict(root=project, runner=_runner([SOURCE], [own]))

        before = vsh.describe_declared_scope(*args, **kwargs)
        after = vsh.describe_declared_scope(*args, task_slug=OWN_SLUG, **kwargs)

        assert before["status"] == vsh.STATUS_UNDER_DECLARED
        assert before["undeclared"] == [own]
        assert before["undeclared_count"] == 1
        assert after["status"] == vsh.STATUS_COMPLETE
        assert after["undeclared"] == []
        assert after["undeclared_count"] == 0

    def test_foreign_export_stays_undeclared(self, project):
        """AC2 — the over-subtraction guard.

        `nine-open-tasks-are-invisible-to-release-scope` closed by declaring
        nine FOREIGN exports: they are a real product of a planning task, and
        this run did not touch them. Subtracting all of `tausik/tasks/` would
        pass this file's other tests and lie about that closure's coverage.
        """
        own = self._export(project, OWN_SLUG)
        foreign = self._export(project, FOREIGN_SLUG)
        d = vsh.describe_declared_scope(
            [SOURCE],
            TS,
            root=project,
            runner=_runner([SOURCE], [own, foreign]),
            task_slug=OWN_SLUG,
        )
        assert d["status"] == vsh.STATUS_UNDER_DECLARED
        assert d["undeclared"] == [foreign]

    def test_undeclared_source_still_under_declared(self, project):
        """AC6 — the negative. A check nobody can fail is the original defect."""
        own = self._export(project, OWN_SLUG)
        d = vsh.describe_declared_scope(
            [SOURCE],
            TS,
            root=project,
            runner=_runner(["scripts/service_gates.py"], [own]),
            task_slug=OWN_SLUG,
        )
        assert d["status"] == vsh.STATUS_UNDER_DECLARED
        assert d["undeclared"] == ["scripts/service_gates.py"]

    def test_security_undeclared_is_not_weakened(self, project):
        """AC5 — the block reaches exactly as far as it did before."""
        own = self._export(project, OWN_SLUG)
        d = vsh.describe_declared_scope(
            [SOURCE],
            TS,
            root=project,
            runner=_runner(["src/auth.py"], [own]),
            task_slug=OWN_SLUG,
        )
        assert d["security_undeclared"] == ["src/auth.py"]
        assert own not in d["undeclared"]
        assert vsh.security_block_reason(d) is not None

    def test_emptied_coverage_says_what_emptied_it(self, project):
        """AC4 / memory #454 — the mirror of the defect being fixed.

        Subtraction can empty the set, and the sentence already sitting on that
        branch claims something else: "nothing the agent did is visible to git"
        and "everything visible to git was the framework's own writing" are
        different facts. Both are `complete`, and a reader must still be able to
        tell which one happened — otherwise the fix is silent in exactly the
        place it fired.
        """
        own = self._export(project, OWN_SLUG)
        d = vsh.describe_declared_scope(
            [SOURCE], TS, root=project, runner=_runner([], [own]), task_slug=OWN_SLUG
        )
        assert d["status"] == vsh.STATUS_COMPLETE
        assert own in d["reason"]
        assert d["reason"] != "no git-visible changes since task start"

    def test_genuinely_empty_diff_keeps_its_own_sentence(self, project):
        """The other side of AC4: the old fact must keep the old words."""
        d = vsh.describe_declared_scope(
            [SOURCE], TS, root=project, runner=_runner([], []), task_slug=OWN_SLUG
        )
        assert d["status"] == vsh.STATUS_COMPLETE
        assert d["reason"] == "no git-visible changes since task start"

    def test_no_slug_subtracts_nothing(self, project):
        """Degraded, not broken: a caller with no slug gets the pre-#283 answer."""
        own = self._export(project, OWN_SLUG)
        d = vsh.describe_declared_scope([SOURCE], TS, root=project, runner=_runner([SOURCE], [own]))
        assert d["undeclared"] == [own]

    def test_declaring_the_own_export_is_still_complete(self, project):
        """The close `verify-handle-dies-on-a-tasks-own-export-file` made legal."""
        own = self._export(project, OWN_SLUG)
        d = vsh.describe_declared_scope(
            [SOURCE, own],
            TS,
            root=project,
            runner=_runner([SOURCE], [own]),
            task_slug=OWN_SLUG,
        )
        assert d["status"] == vsh.STATUS_COMPLETE


class TestParentStoryIsNotUndeclared:
    """Decision #286 — `task start` writes the parent story too.

    MEASURED, session #196: verify #1898 reported exactly one undeclared file,
    `tausik/stories/knowledge-records-what-failed-19.md`, and `git diff` showed
    exactly one changed line in it — `status: open -> active`, written by
    `task start` when it activated a task inside that story. The agent never
    touched the file.

    This is the fifth site of the class Decision #283 opened and the first
    OUTSIDE its stated boundary: #283 subtracts the task's own export and
    explicitly refuses to subtract anybody else's, because a foreign export is
    the real product of a task that produces records. A parent story is neither
    foreign nor a product — it changed because this task was activated, and it
    would have changed identically had the agent done nothing at all.
    """

    STORY = "evidence-primitives"
    OTHER_STORY = "knowledge-records-what-failed-19"

    @pytest.fixture
    def project(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".tausik").mkdir()
        monkeypatch.chdir(tmp_path)
        return str(tmp_path)

    def _export(self, project, slug, story):
        """Write the task's export where the exporter would, naming its story.

        The address is asked of the module, never spelled here: a projection
        that moved would move this fixture with it instead of leaving a green
        test about a path that no longer exists (#249).
        """
        rel = own_export_display(slug, root=project)
        assert rel and not rel.startswith(".."), "projection root must resolve"
        path = os.path.join(project, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        lines = ["---", f"slug: {slug}", 'title: "a task"', "status: active"]
        if story:
            lines.append(f"story: {story}")
        lines += ["---", "", "body", ""]
        # `newline=""` matches the exporter. `state_parse.split_file` demands a
        # bare `---` fence followed by a single LF, and Python's default
        # translation writes CRLF on Windows — a fixture that renders
        # unparsable frontmatter would prove the subtraction never fires
        # instead of proving that it works.
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(lines))
        return rel

    @staticmethod
    def _story_rel(project, slug):
        path = parent_story_abspath(slug)
        assert path, "the story address must resolve"
        return os.path.relpath(path, os.path.normcase(os.path.abspath(project))).replace(
            os.sep, "/"
        )

    def test_before_and_after_on_one_input(self, project):
        """AC6 — the two verdicts side by side, same input, same runner."""
        own = self._export(project, OWN_SLUG, self.STORY)
        story = self._story_rel(project, OWN_SLUG)
        args = ([SOURCE], TS)
        kwargs = dict(root=project, runner=_runner([SOURCE], [own, story]))

        before = vsh.describe_declared_scope(*args, **kwargs)
        after = vsh.describe_declared_scope(*args, task_slug=OWN_SLUG, **kwargs)

        assert before["status"] == vsh.STATUS_UNDER_DECLARED
        assert story in before["undeclared"]
        assert after["status"] == vsh.STATUS_COMPLETE
        assert after["undeclared"] == []

    def test_someone_elses_story_stays_undeclared(self, project):
        """AC3 — the boundary of #283 is narrowed by ONE file, not dissolved.

        A task that really did edit another story's projection is reporting on
        its own work, and subtracting all of `tausik/stories/` would zero that.
        """
        own = self._export(project, OWN_SLUG, self.STORY)
        mine = self._story_rel(project, OWN_SLUG)
        foreign = mine.replace(self.STORY, self.OTHER_STORY)
        assert foreign != mine
        d = vsh.describe_declared_scope(
            [SOURCE],
            TS,
            root=project,
            runner=_runner([SOURCE], [own, mine, foreign]),
            task_slug=OWN_SLUG,
        )
        assert d["status"] == vsh.STATUS_UNDER_DECLARED
        assert d["undeclared"] == [foreign]

    def test_a_task_with_no_parent_subtracts_only_its_export(self, project):
        """The ordinary case: no `story:` key, and nothing extra is removed."""
        own = self._export(project, OWN_SLUG, None)
        assert parent_story_abspath(OWN_SLUG) is None
        d = vsh.describe_declared_scope(
            [SOURCE],
            TS,
            root=project,
            runner=_runner([SOURCE], [own, "tausik/stories/some-story.md"]),
            task_slug=OWN_SLUG,
        )
        assert d["status"] == vsh.STATUS_UNDER_DECLARED
        assert d["undeclared"] == ["tausik/stories/some-story.md"]

    def test_a_missing_export_subtracts_no_story(self, project):
        """Degraded, not broken: with no projection on disk there is no slug to
        read, so the story is not subtracted — and with the projection off
        nothing rewrote that file either."""
        own = self._export(project, OWN_SLUG, self.STORY)
        story = self._story_rel(project, OWN_SLUG)
        os.remove(os.path.join(project, own.replace("/", os.sep)))
        d = vsh.describe_declared_scope(
            [SOURCE], TS, root=project, runner=_runner([SOURCE], [story]), task_slug=OWN_SLUG
        )
        assert d["undeclared"] == [story]

    def test_emptied_coverage_names_both_files(self, project):
        """AC4 / memory #454 — the message must say what emptied the set."""
        own = self._export(project, OWN_SLUG, self.STORY)
        story = self._story_rel(project, OWN_SLUG)
        d = vsh.describe_declared_scope(
            [SOURCE], TS, root=project, runner=_runner([], [own, story]), task_slug=OWN_SLUG
        )
        assert d["status"] == vsh.STATUS_COMPLETE
        assert own in d["reason"] and story in d["reason"]
        assert d["reason"] != "no git-visible changes since task start"

    def test_security_undeclared_is_not_weakened(self, project):
        """AC5 — the block reaches exactly as far as it did before."""
        own = self._export(project, OWN_SLUG, self.STORY)
        story = self._story_rel(project, OWN_SLUG)
        d = vsh.describe_declared_scope(
            [SOURCE],
            TS,
            root=project,
            runner=_runner(["src/auth.py"], [own, story]),
            task_slug=OWN_SLUG,
        )
        assert d["security_undeclared"] == ["src/auth.py"]
        assert vsh.security_block_reason(d) is not None

    def test_an_undeclared_source_still_reddens(self, project):
        """AC5 negative — a check nobody can fail is the defect being fixed."""
        own = self._export(project, OWN_SLUG, self.STORY)
        story = self._story_rel(project, OWN_SLUG)
        d = vsh.describe_declared_scope(
            [SOURCE],
            TS,
            root=project,
            runner=_runner(["scripts/service_gates.py"], [own, story]),
            task_slug=OWN_SLUG,
        )
        assert d["status"] == vsh.STATUS_UNDER_DECLARED
        assert d["undeclared"] == ["scripts/service_gates.py"]
