"""Post-migration data steps (v18 role seed + v34 event hash-chain backfill).

Extracted from backend_migrations.py to keep that file under the 400-line
filesize gate. ``run_post_migrations`` runs once AFTER the version loop in
``run_migrations`` and is idempotent: the v18 seed is guarded by a meta flag,
the v34 backfill no-ops when the chain is already sealed.
"""

from __future__ import annotations

import sqlite3

from backend_migrations_legacy import seed_v18_roles
from backend_migrations_v34 import maybe_backfill_v34
from backend_migrations_v42_backfill import maybe_backfill_v42
from backend_migrations_v43 import maybe_rebuild_tasks_v43
from backend_migrations_v48 import maybe_rebuild_usage_events_v48
from backend_migrations_v49 import maybe_widen_spec_types_v49
from backend_migrations_v50 import maybe_widen_adapt_statuses_v50
from backend_migrations_v53 import ensure_actz_points_tz_ref_index


def run_post_migrations(conn: sqlite3.Connection, current_version: int) -> None:
    """Idempotent post-migration seeding for an already-migrated connection."""
    if current_version >= 18:
        try:
            already = conn.execute("SELECT value FROM meta WHERE key='v18_seeded'").fetchone()
        except Exception:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
            already = None
        try:
            roles_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='roles'"
            ).fetchone()
        except Exception:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
            roles_exists = None
        if not already and roles_exists:
            report = None
            try:
                conn.execute("BEGIN IMMEDIATE")
                report = seed_v18_roles(conn)
                conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('v18_seeded', '1')")
                conn.commit()
            except Exception as e:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
                import logging

                logging.getLogger("tausik.migrations").warning("v18 seed/flag failed: %s", e)
                try:
                    conn.rollback()
                except Exception:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
                    pass
            if report and report["dropped_legacy_values"]:
                import sys

                print(
                    f"  v18 role normalization: {report['seeded']} seeded, "
                    f"{report['tasks_rewritten']} tasks rewritten, "
                    f"dropped {len(report['dropped_legacy_values'])} unparseable: "
                    f"{report['dropped_legacy_values']}",
                    file=sys.stderr,
                )
    if current_version >= 34:  # seal historical events into the hash-chain
        maybe_backfill_v34(conn)
    if current_version >= 42:  # stable slugs for decisions + memory, then UNIQUE index
        maybe_backfill_v42(conn)
    if current_version >= 43:  # tighten tasks.model_mismatch to NOT NULL (guarded rebuild)
        maybe_rebuild_tasks_v43(conn)
    if current_version >= 48:  # relax usage_events.session_id to optional (guarded rebuild)
        maybe_rebuild_usage_events_v48(conn)
    if current_version >= 49:  # widen specs.type to the standard's eleven (guarded rebuild)
        maybe_widen_spec_types_v49(conn)
    if current_version >= 50:  # widen adapts.status to the standard's seven (guarded rebuild)
        maybe_widen_adapt_statuses_v50(conn)
    if current_version >= 53:  # index on actz_points.tz_ref, safe on either path (guarded)
        ensure_actz_points_tz_ref_index(conn)
