"""hook-fail-open-db-error-telemetry: a guard that SILENTLY fails open leaves
a countable trace, in its own category — never conflated with an intentional
bypass or a working detection.

task_gate/scope_write_gate fail OPEN when they cannot read the DB (locked or
schema-broken) unless TAUSIK_HOOK_FAIL_SECURE is set. Before this task that was
invisible: a transient DB fault dropped enforcement and nothing recorded it.
These tests pin (1) the emit helper, (2) the three-way metric split so a
degradation cannot masquerade as a detection, and (3) both hooks actually
emitting on a real fail-open.
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import redirect_stdout

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
_HOOKS = os.path.join(_SCRIPTS, "hooks")
for _p in (_SCRIPTS, _HOOKS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


def _make_project(tmp_path):
    tdir = tmp_path / ".tausik"
    tdir.mkdir()
    be = SQLiteBackend(str(tdir / "tausik.db"))
    return str(tmp_path), str(tdir), be


def _db_of(be: SQLiteBackend) -> str:
    return be._conn.execute("PRAGMA database_list").fetchone()[2]


def _supervision_rows(db: str) -> list[tuple[str, str, str]]:
    conn = sqlite3.connect(db)
    try:
        return conn.execute(
            "SELECT entity_id, action, details FROM events "
            "WHERE entity_type='supervision' ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


# --- The emit helper ---------------------------------------------------------


class TestEmitDegradation:
    def test_writes_one_fail_open_row(self, tmp_path):
        project_dir, _tdir, be = _make_project(tmp_path)
        from _common import emit_supervision_degradation

        emit_supervision_degradation(project_dir, "db_error", "task_gate", "locked")
        assert _supervision_rows(_db_of(be)) == [("task_gate", "fail_open_db_error", "locked")]

    def test_no_db_is_silent(self, tmp_path):
        from _common import emit_supervision_degradation

        emit_supervision_degradation(str(tmp_path), "db_error", "task_gate")

    def test_broken_db_never_raises(self, tmp_path):
        from _common import emit_supervision_degradation

        tdir = tmp_path / ".tausik"
        tdir.mkdir()
        (tdir / "tausik.db").write_bytes(b"not a sqlite database")
        emit_supervision_degradation(str(tmp_path), "db_error", "task_gate")

    def test_shares_writer_with_bypass(self, tmp_path):
        """Both helpers route through _emit_supervision — one machinery, two
        namespaced actions. A bypass and a degradation coexist as distinct rows."""
        project_dir, _tdir, be = _make_project(tmp_path)
        from _common import emit_supervision_bypass, emit_supervision_degradation

        emit_supervision_bypass(project_dir, "skip_hooks", "task_gate")
        emit_supervision_degradation(project_dir, "db_error", "task_gate")
        actions = [r[1] for r in _supervision_rows(_db_of(be))]
        assert actions == ["bypass_skip_hooks", "fail_open_db_error"]


# --- Three-way metric split --------------------------------------------------


class TestThreeWayCategory:
    def _seed(self, be):
        from _common import emit_supervision_bypass, emit_supervision_degradation

        root = os.path.dirname(os.path.dirname(_db_of(be)))
        emit_supervision_bypass(root, "skip_hooks", "task_gate")
        emit_supervision_degradation(root, "db_error", "scope_write_gate")
        # A DETECTION: supervision that WORKED (not bypass_, not fail_open_).
        be.event_add("supervision", "some-task", "complexity_understated", "3sp->8sp")

    def test_each_bucket_isolated(self, tmp_path):
        _project_dir, _tdir, be = _make_project(tmp_path)
        self._seed(be)

        byp = be.supervision_bypasses_summary()
        deg = be.supervision_degradations_summary()
        det = be.supervision_detections_summary()

        assert byp == {"total": 1, "by_action": {"bypass_skip_hooks": 1}}
        assert deg == {"total": 1, "by_action": {"fail_open_db_error": 1}}
        assert det == {"total": 1, "by_action": {"complexity_understated": 1}}

    def test_degradation_does_not_leak_into_detection(self, tmp_path):
        """The exact regression this task guards: fail_open_% is NOT 'everything
        else', so it must not inflate the detections (supervision-worked) count."""
        _project_dir, _tdir, be = _make_project(tmp_path)
        from _common import emit_supervision_degradation

        emit_supervision_degradation(os.path.dirname(_tdir), "db_error", "scope_write_gate")
        det = be.supervision_detections_summary()
        assert det == {"total": 0, "by_action": {}}
        assert "fail_open_db_error" not in det["by_action"]

    def test_like_underscore_is_literal_not_wildcard(self, tmp_path):
        """s128 review MEDIUM-2: the '_' in 'bypass_%' must be a LITERAL
        underscore, not a LIKE single-char wildcard. An action like
        'bypassXverify' (X where the underscore belongs) must NOT land in the
        bypass bucket — otherwise the 3-way partition is looser than its
        MUTUALLY-EXCLUSIVE contract."""
        _project_dir, _tdir, be = _make_project(tmp_path)
        be.event_add("supervision", "e", "bypassXverify", None)  # X, not '_'
        be.event_add("supervision", "e", "fail_openXdb", None)  # X, not '_'

        assert be.supervision_bypasses_summary()["total"] == 0
        assert be.supervision_degradations_summary()["total"] == 0
        # Neither matches the literal prefixes, so both fall to detection.
        det = be.supervision_detections_summary()
        assert det["by_action"].get("bypassXverify") == 1
        assert det["by_action"].get("fail_openXdb") == 1

    def test_metrics_dict_has_degradations_key(self, tmp_path):
        _project_dir, _tdir, be = _make_project(tmp_path)
        m = ProjectService(be).get_metrics()
        assert m["supervision_degradations"] == {"total": 0, "by_action": {}}

    def test_unknown_category_raises(self, tmp_path):
        import pytest

        _project_dir, _tdir, be = _make_project(tmp_path)
        with pytest.raises(ValueError, match="unknown supervision category"):
            be._supervision_by_action(category="nonsense")


# --- Render ------------------------------------------------------------------


class TestRender:
    def test_degradation_section_rendered_when_nonzero(self):
        from project_cli_metrics import render_extended_metrics

        buf = io.StringIO()
        with redirect_stdout(buf):
            render_extended_metrics(
                {"supervision_degradations": {"total": 2, "by_action": {"fail_open_db_error": 2}}}
            )
        out = buf.getvalue()
        assert "Supervision degradations" in out
        assert "fail_open_db_error" in out
        assert "Total: 2" in out

    def test_degradation_section_silent_when_zero(self):
        from project_cli_metrics import render_extended_metrics

        buf = io.StringIO()
        with redirect_stdout(buf):
            render_extended_metrics({"supervision_degradations": {"total": 0, "by_action": {}}})
        assert "Supervision degradations" not in buf.getvalue()


# --- Hooks actually emit on a real fail-open ---------------------------------


def _break_tasks_read(db_path: str) -> None:
    """Make the gates' `... FROM tasks WHERE status=...` raise sqlite.Error
    while leaving the real `events` table writable — a faithful 'DB read failed
    but the sink still works' fail-open, on the real schema (the oracle)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("ALTER TABLE tasks RENAME COLUMN status TO status_broken")
        conn.commit()
    finally:
        conn.close()


def _run_hook(hook: str, project_dir, file_path, extra_env=None):
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    env.pop("TAUSIK_SKIP_HOOKS", None)
    env.pop("TAUSIK_HOOK_FAIL_SECURE", None)
    if extra_env:
        env.update(extra_env)
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(file_path)},
        "transcript_path": "",
    }
    return subprocess.run(
        [sys.executable, os.path.join(_HOOKS, hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env=env,
    )


class TestHookFailOpenEmits:
    def _setup(self, tmp_path):
        project_dir, _tdir, be = _make_project(tmp_path)
        db = _db_of(be)
        be.close()
        _break_tasks_read(db)
        target = tmp_path / "src" / "mod.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        return project_dir, db, str(target)

    def test_task_gate_fail_open_emits(self, tmp_path):
        project_dir, db, target = self._setup(tmp_path)
        result = _run_hook("task_gate.py", project_dir, target)
        assert result.returncode == 0, result.stderr
        rows = _supervision_rows(db)
        assert [(r[0], r[1]) for r in rows] == [("task_gate", "fail_open_db_error")]
        assert rows[0][2]  # details carries the sqlite error text

    def test_scope_write_gate_fail_open_emits(self, tmp_path):
        project_dir, db, target = self._setup(tmp_path)
        result = _run_hook("scope_write_gate.py", project_dir, target)
        assert result.returncode == 0, result.stderr
        rows = _supervision_rows(db)
        assert [(r[0], r[1]) for r in rows] == [("scope_write_gate", "fail_open_db_error")]

    def test_fail_secure_blocks_and_does_not_emit_degradation(self, tmp_path):
        """FAIL_SECURE flips fail-open to fail-closed: it BLOCKS. That is the
        guard working, not a degradation — no fail_open_ row."""
        project_dir, db, target = self._setup(tmp_path)
        result = _run_hook(
            "task_gate.py", project_dir, target, extra_env={"TAUSIK_HOOK_FAIL_SECURE": "1"}
        )
        assert result.returncode == 2, result.stderr
        assert _supervision_rows(db) == []
