"""Local Codex report shared by CLI and MCP; independent of legacy task ledger."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path

from usage_codex import read_incremental, summarize


def _accepted_tasks(project: Path) -> tuple[list[str], dict[str, int]]:
    """Read accepted lifecycle state; absence stays empty rather than inferred."""
    db = project / ".tausik" / "tausik.db"
    if not db.is_file():
        return [], {}
    try:
        uri = db.absolute().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2) as conn:
            rows = conn.execute(
                "SELECT slug, attempts FROM tasks WHERE status='done' AND resolution IS NULL"
            ).fetchall()
        return [str(row[0]) for row in rows], {str(row[0]): int(row[1]) for row in rows}
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return [], {}


def report(
    project_dir: str,
    *,
    sessions_dir: str | None = None,
    thread_id: str | None = None,
) -> dict:
    """Incremental opt-in scan; cache only allowlisted observations in project state."""
    project = Path(project_dir).resolve()
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    sessions = Path(sessions_dir) if sessions_dir else home / "sessions"
    paths = sorted(sessions.rglob("*.jsonl")) if sessions.is_dir() else []
    if thread_id:
        paths = [path for path in paths if path.stem.endswith(thread_id)]
    cache = project / ".tausik" / "usage-codex.sqlite"
    cache.parent.mkdir(parents=True, exist_ok=True)
    states = []
    with sqlite3.connect(cache, timeout=30) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, state TEXT NOT NULL)"
        )
        conn.execute("BEGIN IMMEDIATE")
        for path in paths:
            key = hashlib.sha256(str(path.resolve()).encode()).hexdigest()
            saved = conn.execute("SELECT state FROM sources WHERE id=?", (key,)).fetchone()
            previous = json.loads(saved[0]) if saved else None
            state = read_incremental(path, project, previous)
            conn.execute(
                "INSERT OR REPLACE INTO sources (id, state) VALUES (?, ?)", (key, json.dumps(state))
            )
            states.append(state)
    accepted, attempts = _accepted_tasks(project)
    observed_tasks = {
        str(row["source"]["task"])
        for state in states
        for row in state.get("rows", {}).values()
        if row.get("attribution") == "exact" and row.get("source", {}).get("task")
    }
    accepted = [slug for slug in accepted if slug in observed_tasks]
    result = summarize(states, accepted, attempts=attempts)
    from project_config import load_project_config
    from usage_credit import attach_task_credits

    observations = [row for state in states for row in state.get("rows", {}).values()]
    from benchmark_cohorts import capture_for_project

    project_observations = [row for row in observations if row.get("source", {}).get("project")]
    result["cohort_capture"] = capture_for_project(project, project_observations)
    config = load_project_config(str(project / ".tausik"))
    attach_task_credits(result, observations, accepted, config)
    thread_rows = [
        row
        for state in states
        if not thread_id or state.get("thread") == thread_id
        for row in state.get("rows", {}).values()
        if row.get("source", {}).get("project")
    ]
    latest = max(
        thread_rows,
        key=lambda row: str(row.get("source", {}).get("timestamp") or ""),
        default=None,
    )
    result["latest_context_tokens"] = latest["tokens"].get("input") if latest else None
    result["coverage"]["observed_task_windows"] = len(observed_tasks)
    result["coverage"]["accepted_task_windows"] = len(accepted)
    result["source_available"] = sessions.is_dir()
    result["scope"] = (
        "project responses; accepted-task cost from explicit native boundaries and DB done state; "
        "quota account-wide"
    )
    return result
