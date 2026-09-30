"""The TAUSIK session is the host session (decision #376, 1.10, story E).

Task `session-is-the-host-session-not-a-ritual`. Before: a session was a ritual —
`/start` opened it, `/end` closed it, an autonomous agent did neither, and
session #265 stayed open nine days at 76 active minutes. After: SessionStart
opens a session keyed by the host's own `session_id`, SessionEnd closes exactly
that one. Held here from the schema up: the migration on both install paths,
the service contract, two concurrent host sessions, the CLI without a host id,
and the two hooks.
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "scripts", "hooks"))

from backend_init import init_schema  # noqa: E402
from backend_migrations_v63 import MIGRATION_V63  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {r[1] for r in conn.execute("PRAGMA table_info(sessions)")}


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "host.db")))
    yield s
    s.be.close()


class TestTheSchema:
    def test_the_literal_is_frozen(self):
        assert MIGRATION_V63 == [
            "ALTER TABLE sessions ADD COLUMN host_session_id TEXT",
            "CREATE INDEX IF NOT EXISTS idx_sessions_host ON sessions(host_session_id)",
        ]

    def test_a_fresh_install_has_the_column_and_the_index(self, tmp_path):
        conn = sqlite3.connect(str(tmp_path / "fresh.db"))
        init_schema(conn)
        assert "host_session_id" in _columns(conn)
        idx = {r[1] for r in conn.execute("PRAGMA index_list(sessions)")}
        assert "idx_sessions_host" in idx
        conn.close()

    def test_a_v62_database_is_carried_up_by_init_schema(self, tmp_path):
        """The consumer's path: init_schema on an OLD database, cumulative
        scripts first, migrations after (the ordering that broke 1.8 → 1.9 at
        v53, memory #716). A session row that existed before keeps its data."""
        conn = sqlite3.connect(str(tmp_path / "v62.db"))
        init_schema(conn)
        conn.execute("DROP INDEX idx_sessions_host")
        conn.execute("ALTER TABLE sessions DROP COLUMN host_session_id")
        conn.execute(
            "INSERT INTO sessions(started_at, summary) VALUES('2026-09-01T00:00:00Z', 'old')"
        )
        conn.execute("UPDATE meta SET value='62' WHERE key='schema_version'")
        conn.commit()
        assert "host_session_id" not in _columns(conn)
        init_schema(conn)
        assert "host_session_id" in _columns(conn)
        ver = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        assert int(ver) == SCHEMA_VERSION
        row = conn.execute("SELECT summary, host_session_id FROM sessions").fetchone()
        assert row == ("old", None)
        conn.close()


class TestTheService:
    def test_opening_is_idempotent_per_host_session(self, svc):
        first = svc.session_start("host-A")
        again = svc.session_start("host-A")
        assert "started for host session host-A" in first
        assert "already active for host session host-A" in again
        rows = svc.be._q("SELECT id FROM sessions WHERE host_session_id='host-A'")
        assert len(rows) == 1

    def test_a_second_host_session_opens_its_own_row(self, svc):
        svc.session_start("host-A")
        svc.session_start("host-B")
        open_rows = svc.be._q("SELECT host_session_id FROM sessions WHERE ended_at IS NULL")
        assert sorted(r["host_session_id"] for r in open_rows) == ["host-A", "host-B"]

    def test_ending_a_host_session_leaves_the_other_one_open(self, svc, monkeypatch):
        """NEGATIVE: the host that ends does not close another agent's session."""
        monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
        svc.session_start("host-A")
        svc.session_start("host-B")
        svc.session_end(host_session_id="host-A")
        still_open = svc.be._q("SELECT host_session_id FROM sessions WHERE ended_at IS NULL")
        assert [r["host_session_id"] for r in still_open] == ["host-B"]

    def test_ending_an_unknown_host_session_changes_nothing(self, svc, monkeypatch):
        """NEGATIVE: an id with no open session is a no-op with a message, not
        a fallback onto the newest open session."""
        monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
        svc.session_start("host-A")
        msg = svc.session_end(host_session_id="host-Z")
        assert "nothing to end" in msg
        assert svc.be.session_current("host-A") is not None

    def test_the_cli_path_without_a_host_id_is_unchanged(self, svc, monkeypatch):
        """NEGATIVE: a session opened without a host id keeps the old contract —
        one open session, reused, ended by plain `session end`."""
        monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
        assert "started" in svc.session_start()
        assert "already active" in svc.session_start()
        assert svc.be.session_current()["host_session_id"] is None
        svc.session_end()
        with pytest.raises(ServiceError, match="No active session"):
            svc.session_end()


class TestTheHooks:
    def test_session_start_hook_opens_the_host_session(self, monkeypatch, tmp_path):
        import session_start as hook

        calls: list[list[str]] = []
        monkeypatch.setattr(hook, "_tausik_path", lambda _d: "tausik")
        monkeypatch.setattr(
            hook, "_run_tausik", lambda _c, args, _d, **_k: calls.append(args) or ""
        )
        hook._open_host_session(str(tmp_path), {"session_id": "abc-123", "source": "startup"})
        assert calls == [["session", "start", "--host-id", "abc-123"]]

    def test_session_start_hook_without_an_id_opens_nothing(self, monkeypatch, tmp_path):
        """NEGATIVE: another host or a manual run has no id; no row is guessed."""
        import session_start as hook

        calls: list = []
        monkeypatch.setattr(hook, "_tausik_path", lambda _d: "tausik")
        monkeypatch.setattr(hook, "_run_tausik", lambda *a, **k: calls.append(a) or "")
        hook._open_host_session(str(tmp_path), {})
        hook._open_host_session(str(tmp_path), {"session_id": "  "})
        assert calls == []

    def test_session_end_payload_is_read_from_a_pipe_only(self, monkeypatch):
        import session_metrics as hook

        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"session_id": "h1"})))
        assert hook._read_hook_payload() == {"session_id": "h1"}
        monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
        assert hook._read_hook_payload() == {}

    def test_the_read_only_lookup_finds_the_open_host_session(self, tmp_path):
        from session_windows import open_session_for_host

        project = tmp_path / "proj"
        (project / ".tausik").mkdir(parents=True)
        s = ProjectService(SQLiteBackend(str(project / ".tausik" / "tausik.db")))
        try:
            s.session_start("host-A")
            sid = s.be.session_current("host-A")["id"]
            assert open_session_for_host("host-A", str(project)) == sid
            assert open_session_for_host("host-Z", str(project)) is None
        finally:
            s.be.close()
