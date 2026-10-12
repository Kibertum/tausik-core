"""Behavior tests for the read-only Kilo usage adapter."""

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from usage_kilo import report


def _database(path: Path, project: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE session (
          id TEXT PRIMARY KEY, directory TEXT, version TEXT,
          tokens_input INTEGER, tokens_output INTEGER, tokens_reasoning INTEGER,
          tokens_cache_read INTEGER, tokens_cache_write INTEGER
        );
        CREATE TABLE message (
          id TEXT PRIMARY KEY, session_id TEXT, time_updated INTEGER, data TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO session VALUES (?,?,?,?,?,?,?,?)",
        ("session-1", str(project), "7.8.1", 10, 3, 5, 20, 2),
    )
    return conn


def _assistant(response: str, updated: int, *, reasoning=5, error=False) -> tuple:
    tokens = {"input": 10, "output": 3, "cache": {"read": 20, "write": 2}}
    if reasoning is not None:
        tokens["reasoning"] = reasoning
    data = {"role": "assistant", "providerID": "zai", "modelID": "glm-5", "tokens": tokens}
    if error:
        data["error"] = {"name": "APIError"}
    return (
        response,
        "session-1",
        updated,
        json.dumps(data),
    )


def test_incremental_resume_reconciles_without_persisting_conversation(tmp_path):
    source = tmp_path / "kilo.db"
    cache = tmp_path / "usage-kilo.sqlite"
    conn = _database(source, tmp_path)
    conn.execute("INSERT INTO message VALUES (?,?,?,?)", _assistant("response-1", 1000))
    conn.execute(
        "INSERT INTO message VALUES (?,?,?,?)",
        ("user-1", "session-1", 900, '{"role":"user","content":"SECRET-PROMPT"}'),
    )
    conn.commit()
    conn.close()

    first = report(str(tmp_path), db_path=str(source), cache_path=str(cache))
    second = report(str(tmp_path), db_path=str(source), cache_path=str(cache))
    assert first["tokens"] == {
        "input": 32,
        "cached_input": 20,
        "cache_write": 2,
        "output": 8,
        "reasoning_output": 5,
    }
    assert first["glm_responses"] == 1 and first["reliable_totals"] is True
    assert first["glm_completed_responses"] == 1 and first["failed_responses"] == 0
    assert first["coverage"] == {
        "sessions": 1,
        "rows_read": 1,
        "malformed": 0,
        "mismatched_sessions": 0,
    }
    assert second["tokens"] == first["tokens"] and second["coverage"]["rows_read"] == 0
    assert b"SECRET-PROMPT" not in cache.read_bytes()

    with sqlite3.connect(source) as conn:
        conn.execute("INSERT INTO message VALUES (?,?,?,?)", _assistant("response-2", 2000))
        conn.execute(
            "UPDATE session SET tokens_input=20,tokens_output=6,tokens_reasoning=10,"
            "tokens_cache_read=40,tokens_cache_write=4 WHERE id='session-1'"
        )
    resumed = report(str(tmp_path), db_path=str(source), cache_path=str(cache))
    assert resumed["responses"] == 2 and resumed["tokens"]["input"] == 64
    assert resumed["tokens"]["output"] == 16
    assert resumed["coverage"]["rows_read"] == 1
    assert resumed["reliable_totals"] is True
    cache.unlink()  # Windows proves the adapter released its SQLite handle.


def test_unavailable_and_missing_reasoning_are_explicit(tmp_path):
    missing = report(str(tmp_path), db_path=str(tmp_path / "absent.db"))
    assert missing["source_available"] is False
    assert missing["tokens"]["input"] is None and missing["account_quota"] is None

    source = tmp_path / "kilo.db"
    conn = _database(source, tmp_path)
    conn.execute(
        "INSERT INTO message VALUES (?,?,?,?)", _assistant("response-1", 1000, reasoning=None)
    )
    conn.commit()
    conn.close()
    partial = report(str(tmp_path), db_path=str(source))
    assert partial["tokens"]["output"] is None
    assert partial["tokens"]["reasoning_output"] is None
    assert partial["reliable_totals"] is False
    assert partial["account_quota"] is None and partial["pricing_applied"] is False

    with sqlite3.connect(source) as conn:
        conn.execute("DELETE FROM message")
        conn.execute("INSERT INTO message VALUES (?,?,?,?)", _assistant("failed", 2000, error=True))
    failed = report(str(tmp_path), db_path=str(source))
    assert failed["glm_responses"] == 1
    assert failed["glm_completed_responses"] == 0 and failed["failed_responses"] == 1


def test_cli_and_mcp_share_kilo_report(tmp_path, monkeypatch, capsys):
    from project_cli_metrics import cmd_metrics
    from project_parser import build_parser

    monkeypatch.syspath_prepend(
        str(Path(__file__).resolve().parents[1] / "harness/claude/mcp/project")
    )
    from handlers_status import _handle_metrics

    source = tmp_path / "kilo.db"
    conn = _database(source, tmp_path)
    conn.execute("INSERT INTO message VALUES (?,?,?,?)", _assistant("response-1", 1000))
    conn.commit()
    conn.close()
    monkeypatch.setenv("KILO_DB", str(source))
    svc = SimpleNamespace(tausik_dir=lambda: str(tmp_path / ".tausik"))

    cmd_metrics(svc, build_parser().parse_args(["metrics", "tokens", "--host", "kilo", "--json"]))
    cli = json.loads(capsys.readouterr().out)
    mcp = json.loads(_handle_metrics(svc, {"host": "kilo"}))
    assert cli["tokens"] == mcp["tokens"]
    assert mcp["responses"] == 1 and mcp["coverage"]["rows_read"] == 0
