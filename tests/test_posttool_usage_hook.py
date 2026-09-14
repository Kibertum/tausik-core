"""Tests for scripts/hooks/posttool_usage.py — PostToolUse usage_events writer.

Covers happy path + 5 negative scenarios (A-E from the v1.4 task spec):
  A. malformed stdin JSON
  B. no active task (task_slug NULL)
  C. unknown model_id (cost_usd=0 + stderr warn)
  D. locked DB retry behaviour (best-effort, no crash)
  E. missing .tausik/tausik.db (silent exit 0)

Hook is invoked as a subprocess to mirror the real harness contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import sqlite3

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402

_HOOK_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks", "posttool_usage.py")


def _seed_project(tmp_path, *, with_active_task: bool = True, end_session: bool = False):
    """Build a tausik-shaped tmp project. Returns (project_dir, db_path)."""
    project_dir = tmp_path / "proj"
    (project_dir / ".tausik").mkdir(parents=True)
    db_path = project_dir / ".tausik" / "tausik.db"
    be = SQLiteBackend(str(db_path))
    try:
        be._conn.execute(
            "INSERT INTO sessions(started_at, ended_at) VALUES ('2026-05-03T10:00:00Z', ?)",
            ("2026-05-03T11:00:00Z" if end_session else None,),
        )
        if with_active_task:
            be._conn.execute(
                "INSERT INTO tasks(slug,title,status,created_at,updated_at) "
                "VALUES('demo','Demo task','active',"
                "'2026-05-03T10:00:00Z','2026-05-03T10:00:00Z')"
            )
        be._conn.commit()
    finally:
        be.close()
    return str(project_dir), str(db_path)


def _run_hook(project_dir: str, payload: dict | str) -> subprocess.CompletedProcess:
    """Invoke the hook with the given payload. Payload `str` → raw stdin."""
    body = payload if isinstance(payload, str) else json.dumps(payload)
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = project_dir
    env.pop("TAUSIK_SKIP_HOOKS", None)
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input=body,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=15,
    )


def _read_events(db_path: str) -> list[dict]:
    with sqlite3.connect(db_path) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM usage_events ORDER BY id ASC").fetchall()
    return [dict(r) for r in rows]


# --- Happy path -----------------------------------------------------------


class TestHappyPath:
    def test_writes_row_with_active_task_and_tokens(self, tmp_path):
        project_dir, db = _seed_project(tmp_path)
        payload = {
            "tool_name": "Read",
            "tool_response": {
                "model": "claude-opus-4-7",
                "usage": {"input_tokens": 1000, "output_tokens": 200},
            },
        }
        result = _run_hook(project_dir, payload)
        assert result.returncode == 0, result.stderr
        events = _read_events(db)
        assert len(events) == 1
        row = events[0]
        assert row["task_slug"] == "demo"
        assert row["model_id"] == "claude-opus-4-7"
        assert row["tokens_input"] == 1000
        assert row["tokens_output"] == 200
        assert row["tokens_total"] == 1200
        assert row["tool_calls"] == 1
        assert row["source"] == "posttool"
        assert row["tool_name"] == "Read"
        # Opus 4.7 at the published $5/$25 tier (corrected in
        # cost-pricing-missing-opus-48 from a carried-over $15/$75):
        # 1000/1M*5 + 200/1M*25 = 0.005 + 0.005 = 0.01
        assert row["cost_usd"] == pytest.approx(0.01, rel=1e-3)

    def test_empty_payload_records_the_call_and_measures_nothing(self, tmp_path):
        """The call happened, so the row is written and `tool_calls` counts it.
        What the row must NOT do is claim a token count and a price: an empty
        payload measured nothing, and nothing is NULL, not 0 (decision #334).

        This test asserted 0 until session #231. That assertion is how 55,471
        rows came to state that work had cost exactly $0.00.
        """
        project_dir, db = _seed_project(tmp_path)
        result = _run_hook(project_dir, "")
        assert result.returncode == 0
        events = _read_events(db)
        assert len(events) == 1
        row = events[0]
        assert row["tokens_total"] is None
        assert row["tokens_input"] is None
        assert row["tokens_output"] is None
        assert row["cost_usd"] is None
        assert row["tool_calls"] == 1
        assert row["source"] == "posttool"
        assert row["tool_name"] is None


# --- Negative scenarios ---------------------------------------------------


class TestNegativeScenarios:
    """A through E from the v14b-usage-events-auto-write AC."""

    def test_a_malformed_json_does_not_raise(self, tmp_path):
        """A: malformed stdin → exit 0, the call is recorded, nothing measured."""
        project_dir, db = _seed_project(tmp_path)
        result = _run_hook(project_dir, "not-json{{{")
        assert result.returncode == 0
        events = _read_events(db)
        # The row still lands (the call happened) but claims no measurement:
        # an unparseable payload laundered into a 0 is a fabricated number.
        assert len(events) == 1
        assert events[0]["tokens_total"] is None
        assert events[0]["source"] == "posttool"

    def test_b_no_active_task_writes_null_slug(self, tmp_path):
        """B: no active task → task_slug NULL, no FK error."""
        project_dir, db = _seed_project(tmp_path, with_active_task=False)
        payload = {
            "tool_name": "Bash",
            "tool_response": {
                "model": "claude-haiku-4-5",
                "usage": {"input_tokens": 50, "output_tokens": 10},
            },
        }
        result = _run_hook(project_dir, payload)
        assert result.returncode == 0
        events = _read_events(db)
        assert len(events) == 1
        assert events[0]["task_slug"] is None
        assert events[0]["model_id"] == "claude-haiku-4-5"

    def test_c_unknown_model_yields_absent_cost_and_warn(self, tmp_path):
        """C: unknown model_id → cost ABSENT + stderr warning, no KeyError.

        The tokens WERE measured (100/50 arrived in the payload) and are kept.
        Only the price is unknown, and an unknown price is not a price of zero.
        """
        project_dir, db = _seed_project(tmp_path)
        payload = {
            "tool_name": "Read",
            "tool_response": {
                "model": "claude-mystery-9-9",
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        }
        result = _run_hook(project_dir, payload)
        assert result.returncode == 0
        events = _read_events(db)
        assert len(events) == 1
        assert events[0]["model_id"] == "claude-mystery-9-9"
        assert events[0]["cost_usd"] is None
        assert events[0]["tokens_input"] == 100
        assert events[0]["tokens_output"] == 50
        # The unpriced-model warning is now owned by cost_pricing.calculate_cost_usd
        # (once per id, override-aware) rather than an inline posttool check.
        assert "no price for model 'claude-mystery-9-9'" in result.stderr

    @pytest.mark.slow  # v14b-pytest-fast-lane: real lock contention via threading sleeps (~7s)
    def test_d_locked_db_retries_then_succeeds(self, tmp_path):
        """D: a brief external lock should not crash the hook.

        We hold a write transaction in another connection, briefly,
        then release. The hook's retry loop should win.
        """
        project_dir, db = _seed_project(tmp_path)
        blocker = sqlite3.connect(db, timeout=0.05, isolation_level=None)
        try:
            blocker.execute("BEGIN IMMEDIATE")
            # Schedule release in a thread so the hook can retry-and-win.
            import threading
            import time

            def release():
                time.sleep(0.15)
                try:
                    blocker.execute("COMMIT")
                except sqlite3.Error:
                    pass

            t = threading.Thread(target=release, daemon=True)
            t.start()
            payload = {"tool_name": "Read", "tool_response": {}}
            result = _run_hook(project_dir, payload)
            t.join(timeout=2)
        finally:
            try:
                blocker.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            blocker.close()
        assert result.returncode == 0
        # Either the row landed (most likely) or the hook silently warned —
        # never crashed the harness.
        events = _read_events(db)
        assert len(events) <= 1

    def test_e_no_tausik_db_silent_exit(self, tmp_path):
        """E: project without .tausik/tausik.db → exit 0 with no error spam."""
        project_dir = tmp_path / "bare"
        project_dir.mkdir()
        result = _run_hook(str(project_dir), {"tool_name": "Read", "tool_response": {}})
        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""


class TestEnvOverrides:
    def test_skip_hooks_env_short_circuits(self, tmp_path):
        project_dir, db = _seed_project(tmp_path)
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = project_dir
        env["TAUSIK_SKIP_HOOKS"] = "1"
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input=json.dumps({"tool_name": "Read", "tool_response": {}}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=10,
        )
        assert result.returncode == 0
        # Nothing inserted.
        assert _read_events(db) == []

    def test_no_open_session_still_records_the_task(self, tmp_path):
        """ПЕРЕВЁРНУТЫЙ ХРАПОВИК. Раньше звался test_no_open_session_skips_insert.

        ПРЕЖНИЙ КОНТРАКТ, который он закреплял: без открытой сессии хук не
        вставляет НИЧЕГО (`if session_id is None: return 0`). Это был не выбор,
        а следствие схемы — `usage_events.session_id` объявлялся NOT NULL, и
        событию, принадлежащему ЗАДАЧЕ, но не сессии, некуда было лечь. Цена:
        вся работа вне сессии записывала НОЛЬ вместо ошибки, а `task_slug` в
        момент дропа был уже известен строкой выше.

        Миграция v48 (usage-attribution-is-keyed-by-task-not-session) сняла
        NOT NULL и сделала задачу основной атрибуцией, поэтому утверждение
        перевёрнуто, а не снято: событие пишется с session_id=NULL и живым
        task_slug.

        КУДА ПЕРЕЕХАЛА НАСТОЯЩАЯ ЗАЩИТА, которую прежний храповик нёс. Он
        сторожил одно: событие не должно попасть в БД непонятно к чему
        привязанным. Это по-прежнему сторожится, но уже не дропом, а
        ВИДИМОСТЬЮ — строка без задачи И без сессии обязана быть предъявлена в
        отчёте, и это пинают tests/test_usage_events_unattributed_bucket.py
        (корзина «вне задачи» печатается, в том числе когда таблица по задачам
        пуста) и test_usage_events_double_count.py (корзина не удваивает суммы).
        """
        project_dir, db = _seed_project(tmp_path, end_session=True)
        result = _run_hook(project_dir, {"tool_name": "Read", "tool_response": {}})
        assert result.returncode == 0
        events = _read_events(db)
        assert len(events) == 1, "событие без открытой сессии больше не дропается"
        assert events[0]["session_id"] is None
        assert events[0]["task_slug"] == "demo", (
            "атрибуция задачей — единственная причина не дропать это событие"
        )

    def test_no_session_and_no_task_is_still_written(self, tmp_path):
        """НЕГАТИВНЫЙ СЦЕНАРИЙ: ни задачи, ни сессии — строка всё равно есть.

        Самый тихий из возможных дропов и потому единственный, ради которого
        стоит отдельный тест: раньше такое событие исчезало дважды — сначала по
        отсутствию сессии, а если бы прошло, то по отсутствию задачи оно всё
        равно не попало бы ни в один отчёт. Здесь пинается первая половина
        (строка записана); вторую — что её ВИДНО — пинает
        tests/test_usage_events_unattributed_bucket.py.
        """
        project_dir, db = _seed_project(tmp_path, with_active_task=False, end_session=True)
        result = _run_hook(project_dir, {"tool_name": "Read", "tool_response": {}})
        assert result.returncode == 0
        events = _read_events(db)
        assert len(events) == 1
        assert events[0]["session_id"] is None
        assert events[0]["task_slug"] is None
