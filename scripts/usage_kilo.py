"""Incremental, read-only Kilo SQLite usage adapter.

Kilo stores prompts and credentials in the same database. This adapter selects
only allowlisted identity, timestamp and token JSON fields; its project cache
contains sanitized observations and never conversation bodies or raw paths.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from usage_observation import observation

COUNTERS = ("input", "cached_input", "cache_write", "output", "reasoning_output")
ADAPTER_VERSION = "2"
_SESSION_COUNTERS = (
    "tokens_input",
    "tokens_output",
    "tokens_reasoning",
    "tokens_cache_read",
    "tokens_cache_write",
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _canonical(path: str | Path) -> str:
    return str(Path(path).resolve()).replace("\\", "/").casefold()


def _source_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("KILO_DB", "").strip()
    if env:
        return Path(env).expanduser()
    data = os.environ.get("XDG_DATA_HOME", "").strip()
    base = Path(data).expanduser() if data else Path.home() / ".local" / "share"
    return base / "kilo" / "kilo.db"


def _empty(reason: str, source: Path) -> dict[str, Any]:
    result = {
        "schema_version": 1,
        "host": "kilo",
        "source_available": False,
        "unavailable_reason": reason,
        "responses": 0,
        "completed_responses": 0,
        "failed_responses": 0,
        "response_rounds": 0,
        "tokens": {key: None for key in COUNTERS},
        "providers": [],
        "models": [],
        "host_versions": [],
        "glm_responses": 0,
        "glm_completed_responses": 0,
        "task_attribution": "unknown",
        "account_quota": None,
        "pricing_applied": False,
        "savings_claim": False,
        "reliable_totals": False,
        "coverage": {"sessions": 0, "rows_read": 0, "malformed": 0, "mismatched_sessions": 0},
        "source": {
            "kind": "kilo-sqlite",
            "path": source.name,
            "scope": "project responses; no task, quota, or cost inference",
        },
    }
    return result


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _valid_schema(conn: sqlite3.Connection) -> bool:
    session = {"id", "directory", "version", *_SESSION_COUNTERS}
    message = {"id", "session_id", "time_updated", "data"}
    return session <= _columns(conn, "session") and message <= _columns(conn, "message")


def _iso(milliseconds: int | None) -> str | None:
    if type(milliseconds) is not int or milliseconds < 0:
        return None
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).isoformat()


def _row_observation(row: sqlite3.Row, project_key: str) -> dict[str, Any]:
    usage = {
        "input": row["input"],
        "output": row["output"],
        "reasoning": row["reasoning"],
        "cache": {"read": row["cache_read"], "write": row["cache_write"]},
    }
    return observation(
        usage,
        "kilo-session",
        observed={
            "host": "kilo",
            "host_version": row["host_version"],
            "provider": row["provider"],
            "model": row["model"],
        },
        source={
            "timestamp": _iso(row["updated"]),
            "source_version": (
                "kilo-sqlite/message-error-v1"
                if row["error_type"] is not None
                else "kilo-sqlite/message-v1"
            ),
            "project": project_key,
            "thread": _digest(row["thread"]),
            "response": _digest(row["response"]),
        },
        attribution="project",
    )


def _message_ids(conn: sqlite3.Connection, sessions: list[str]) -> dict[str, int]:
    if not sessions:
        return {}
    marks = ",".join("?" for _ in sessions)
    query = f"""
        SELECT id, time_updated FROM message
        WHERE session_id IN ({marks}) AND json_valid(data)
          AND json_extract(data, '$.role') = 'assistant'
    """
    return {str(row[0]): int(row[1]) for row in conn.execute(query, sessions)}


def _changed_rows(conn: sqlite3.Connection, changed: list[str]) -> list[sqlite3.Row]:
    if not changed:
        return []
    marks = ",".join("?" for _ in changed)
    query = f"""
        SELECT m.id AS response, m.session_id AS thread, m.time_updated AS updated,
          s.version AS host_version,
          json_extract(m.data, '$.providerID') AS provider,
          json_extract(m.data, '$.modelID') AS model,
          json_extract(m.data, '$.tokens.input') AS input,
          json_extract(m.data, '$.tokens.output') AS output,
          json_extract(m.data, '$.tokens.reasoning') AS reasoning,
          json_extract(m.data, '$.tokens.cache.read') AS cache_read,
          json_extract(m.data, '$.tokens.cache.write') AS cache_write,
          json_type(m.data, '$.error') AS error_type
        FROM message m JOIN session s ON s.id=m.session_id
        WHERE m.id IN ({marks})
    """
    return list(conn.execute(query, changed))


def _cache_rows(
    cache: Path,
    source: Path,
    current: dict[str, int],
    changed_rows: list[sqlite3.Row],
    project_key: str,
) -> list[dict[str, Any]]:
    cache.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(cache, timeout=30)) as out:
        out.execute(
            "CREATE TABLE IF NOT EXISTS responses "
            "(id TEXT PRIMARY KEY, updated INTEGER NOT NULL, observation TEXT NOT NULL)"
        )
        out.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        source_key = _digest(str(source.resolve()))
        old_source = out.execute("SELECT value FROM meta WHERE key='source'").fetchone()
        old_adapter = out.execute("SELECT value FROM meta WHERE key='adapter'").fetchone()
        if (old_source and old_source[0] != source_key) or (
            old_adapter and old_adapter[0] != ADAPTER_VERSION
        ):
            out.execute("DELETE FROM responses")
        out.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('source',?)", (source_key,))
        out.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES('adapter',?)", (ADAPTER_VERSION,)
        )
        stale = {row[0] for row in out.execute("SELECT id FROM responses")} - set(current)
        out.executemany("DELETE FROM responses WHERE id=?", ((item,) for item in stale))
        for row in changed_rows:
            payload = json.dumps(_row_observation(row, project_key), ensure_ascii=False)
            out.execute(
                "INSERT OR REPLACE INTO responses(id,updated,observation) VALUES(?,?,?)",
                (row["response"], row["updated"], payload),
            )
        rows = [json.loads(row[0]) for row in out.execute("SELECT observation FROM responses")]
        out.commit()
        return rows


def _sum(rows: list[dict], key: str) -> int | None:
    values = [row["tokens"].get(key) for row in rows]
    return sum(values) if values and all(type(value) is int for value in values) else None


def _existing_cache(cache: Path, source: Path) -> dict[str, int]:
    if not cache.is_file():
        return {}
    try:
        with closing(sqlite3.connect(cache)) as saved:
            recorded = saved.execute("SELECT value FROM meta WHERE key='source'").fetchone()
            adapter = saved.execute("SELECT value FROM meta WHERE key='adapter'").fetchone()
            if (
                not recorded
                or recorded[0] != _digest(str(source.resolve()))
                or not adapter
                or adapter[0] != ADAPTER_VERSION
            ):
                return {}
            return {
                str(row[0]): int(row[1])
                for row in saved.execute("SELECT id,updated FROM responses")
            }
    except sqlite3.Error:
        return {}


def report(
    project_dir: str,
    *,
    db_path: str | None = None,
    cache_path: str | None = None,
) -> dict[str, Any]:
    """Return a compact project report; absence and schema drift are explicit."""
    source = _source_path(db_path)
    if not source.is_file():
        return _empty("source-not-found", source)
    project = _canonical(project_dir)
    project_key = _digest(project)
    cache = Path(cache_path) if cache_path else Path(project_dir) / ".tausik/usage-kilo.sqlite"
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=5)) as conn:
            conn.row_factory = sqlite3.Row
            if not _valid_schema(conn):
                return _empty("unsupported-schema", source)
            session_rows = [
                row
                for row in conn.execute(
                    "SELECT id,directory,version," + ",".join(_SESSION_COUNTERS) + " FROM session"
                )
                if _canonical(row["directory"]) == project
            ]
            sessions = [str(row["id"]) for row in session_rows]
            current = _message_ids(conn, sessions)
            existing = _existing_cache(cache, source)
            changed = [key for key, stamp in current.items() if existing.get(key) != stamp]
            details = _changed_rows(conn, changed)
            malformed = 0
            if sessions:
                marks = ",".join("?" for _ in sessions)
                malformed = int(
                    conn.execute(
                        f"SELECT COUNT(*) FROM message WHERE session_id IN ({marks}) "
                        "AND NOT json_valid(data)",
                        sessions,
                    ).fetchone()[0]
                )
        rows = _cache_rows(cache, source, current, details, project_key)
    except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
        result = _empty("unreadable-source", source)
        result["source_error"] = type(exc).__name__
        return result

    by_thread: dict[str, list[dict]] = {}
    for row in rows:
        by_thread.setdefault(row["source"]["thread"], []).append(row)
    mismatched = 0
    for session in session_rows:
        observed = by_thread.get(_digest(str(session["id"])), [])
        actual = (
            _sum(observed, "input"),
            _sum(observed, "output"),
            _sum(observed, "reasoning_output"),
            _sum(observed, "cached_input"),
            _sum(observed, "cache_write"),
        )
        expected = tuple(int(session[key]) for key in _SESSION_COUNTERS)
        if actual[0] is not None:
            actual = (
                actual[0] - (actual[3] or 0) - (actual[4] or 0),
                actual[1] - (actual[2] or 0) if actual[1] is not None else None,
                actual[2],
                actual[3],
                actual[4],
            )
        if actual != expected:
            mismatched += 1
    models = sorted(
        {row["identity"]["model"]["value"] for row in rows if row["identity"]["model"]["value"]}
    )
    providers = sorted(
        {
            row["identity"]["provider"]["value"]
            for row in rows
            if row["identity"]["provider"]["value"]
        }
    )
    completed = [row for row in rows if row["source"]["source_version"] == "kilo-sqlite/message-v1"]
    failed = len(rows) - len(completed)
    glm_rows = [
        row for row in rows if "glm" in str(row["identity"]["model"]["value"] or "").casefold()
    ]
    result = {
        "schema_version": 1,
        "host": "kilo",
        "source_available": True,
        "responses": len(rows),
        "completed_responses": len(completed),
        "failed_responses": failed,
        "response_rounds": len(rows),
        "tokens": {key: _sum(rows, key) for key in COUNTERS},
        "providers": providers,
        "models": models,
        "host_versions": sorted({str(row["version"]) for row in session_rows if row["version"]}),
        "glm_responses": len(glm_rows),
        "glm_completed_responses": sum(row in completed for row in glm_rows),
        "task_attribution": "unknown",
        "account_quota": None,
        "pricing_applied": False,
        "savings_claim": False,
        "reliable_totals": bool(session_rows) and malformed == 0 and mismatched == 0,
        "coverage": {
            "sessions": len(session_rows),
            "rows_read": len(details),
            "malformed": malformed,
            "mismatched_sessions": mismatched,
        },
        "source": {
            "kind": "kilo-sqlite",
            "path": source.name,
            "scope": "project responses; no task, quota, or cost inference",
        },
    }
    from benchmark_cohorts import capture_for_project

    result["cohort_capture"] = capture_for_project(Path(project_dir).resolve(), rows)
    return result
