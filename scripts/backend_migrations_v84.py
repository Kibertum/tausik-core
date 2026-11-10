"""Migration v84: distinguish legacy complex tasks from new package contracts."""

from __future__ import annotations

import json
import sqlite3

MIGRATION_V84 = [
    "ALTER TABLE tasks ADD COLUMN task_package_legacy INTEGER NOT NULL DEFAULT 0",
]


def legacy_package_contract_incomplete(row: dict[str, object]) -> bool:
    """Return whether a pre-v84 complex row needs compatibility defaults."""
    budget = row["call_budget"]
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        return True
    try:
        profiles = json.loads(row["assurance_profiles"] or "[]")  # type: ignore[arg-type]
        impact = json.loads(row["assurance_impact"] or "{}")  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return True
    if (
        not isinstance(profiles, list)
        or not profiles
        or not all(isinstance(value, str) and value.strip() for value in profiles)
    ):
        return True
    return not isinstance(impact, dict) or any(
        not isinstance(impact.get(key), str) or impact.get(key) in ("", "unknown")
        for key in ("level", "blast_radius", "reversibility")
    )


def mark_legacy_task_packages_v84(conn: sqlite3.Connection) -> None:
    """One-shot mark; guarded for intentionally minimal migration fixtures."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('meta','tasks')"
        ).fetchall()
    }
    if tables != {"meta", "tasks"}:
        return
    marker = conn.execute("SELECT value FROM meta WHERE key='v84_legacy_marked'").fetchone()
    if marker:
        return
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    required = {
        "task_package_legacy",
        "complexity",
        "call_budget",
        "assurance_profiles",
        "assurance_impact",
    }
    if required <= columns:
        rows = conn.execute(
            "SELECT rowid,call_budget,assurance_profiles,assurance_impact "
            "FROM tasks WHERE complexity='complex'"
        ).fetchall()
        legacy_ids = [
            row[0]
            for row in rows
            if legacy_package_contract_incomplete(
                {
                    "call_budget": row[1],
                    "assurance_profiles": row[2],
                    "assurance_impact": row[3],
                }
            )
        ]
        if legacy_ids:
            conn.executemany(
                "UPDATE tasks SET task_package_legacy=1 WHERE rowid=?",
                [(task_id,) for task_id in legacy_ids],
            )
    conn.execute("INSERT INTO meta(key,value) VALUES('v84_legacy_marked','1')")
    conn.commit()
