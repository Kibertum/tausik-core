"""Read observed source-to-test coverage edges from the project graph."""

from __future__ import annotations

import os
import sqlite3


def observed_test_edges_for(base: str, relevant_files: list[str] | None) -> dict[str, set[str]]:
    """Return observed test paths grouped by exact repo-relative source path."""
    if not relevant_files:
        return {}
    db = os.path.join(base, ".tausik", "tausik.db")
    if not os.path.isfile(db):
        return {}
    wanted = [r.replace("\\", "/") for r in relevant_files if r and isinstance(r, str)]
    if not wanted:
        return {}

    placeholders = ",".join("?" for _ in wanted)
    try:
        with sqlite3.connect(db, timeout=2) as conn:
            rows = conn.execute(
                "SELECT dst.path, src.path FROM artifact_edges e "
                "JOIN artifacts src ON src.id = e.source_artifact_id "
                "JOIN artifacts dst ON dst.id = e.target_artifact_id "
                "WHERE e.layer = 'observed_coverage' "
                f"AND dst.path IN ({placeholders})",
                wanted,
            ).fetchall()
    except sqlite3.Error:
        return {}
    # Imported lazily because the resolver re-exports this module's public
    # lookup. At call time initialization is complete, so this avoids a cycle
    # while keeping one canonical definition of collectable test paths.
    from gate_test_resolver import build_tests_index

    allowed_tests = {
        path.replace("\\", "/") for paths in build_tests_index(base).values() for path in paths
    }
    grouped: dict[str, set[str]] = {}
    for source_path, test_path in rows:
        test_rel = str(test_path).replace("\\", "/")
        if test_rel in allowed_tests:
            grouped.setdefault(str(source_path).replace("\\", "/"), set()).add(test_rel)
    return grouped


def observed_tests_for(base: str, relevant_files: list[str] | None) -> set[str]:
    """Return every test observed reaching any relevant file."""
    grouped = observed_test_edges_for(base, relevant_files)
    return {test_rel for tests in grouped.values() for test_rel in tests}
