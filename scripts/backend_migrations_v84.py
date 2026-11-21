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


def legacy_marker_for_imported_task(
    *,
    complexity: object,
    call_budget: object,
    assurance_profiles: object,
    assurance_impact: object,
) -> int | None:
    """Mark incomplete complex imports so start can normalize (TB-001 / TB-011).

    Portable export omits the local one-shot marker. Returning ``1`` means the
    importer should set ``task_package_legacy``; ``None`` means leave the column
    alone (complete complex and non-complex stay strict).
    """
    if complexity != "complex":
        return None
    budget: object = call_budget
    try:
        if isinstance(call_budget, bool):
            budget = None
        elif isinstance(call_budget, int):
            budget = call_budget
        elif isinstance(call_budget, str):
            budget = int(call_budget)
        elif call_budget is None:
            budget = None
        else:
            budget = None
    except (TypeError, ValueError):
        budget = None
    profiles_raw: object = assurance_profiles
    if isinstance(profiles_raw, list):
        profiles_raw = json.dumps(profiles_raw)
    elif profiles_raw is None:
        profiles_raw = "[]"
    impact_raw: object = assurance_impact
    if isinstance(impact_raw, dict):
        impact_raw = json.dumps(impact_raw, sort_keys=True)
    elif impact_raw is None:
        impact_raw = "{}"
    if legacy_package_contract_incomplete(
        {
            "call_budget": budget,
            "assurance_profiles": profiles_raw,
            "assurance_impact": impact_raw,
        }
    ):
        return 1
    return None


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
