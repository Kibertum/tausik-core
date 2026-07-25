"""Lifecycle triggers for the git-native projection (state-git-triggers).

Ties export/import to the task lifecycle so the `tausik/` files track the DB
without manual commands: a durable write (task done / decide / memory add)
incrementally re-serializes JUST that entity, and session start detects a tree
that diverged from the DB (after a `git pull`) and suggests `tausik sync`.

FAIL-OPEN by construction (gotcha #271): every trigger swallows its own errors —
a serialization or IO fault must NEVER break or roll back the underlying
operation. The projection is best-effort; the DB write is the source of truth.

Gated behind config `state.auto_export` (default OFF): until
state-git-roundtrip-gate un-gitignores `tausik/`, a project must opt in so it
never gets surprise untracked files.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_service import ProjectService

_log = logging.getLogger("tausik.state.triggers")


def _auto_export_enabled() -> bool:
    """True iff config `state.auto_export` is truthy. Any error → False (off)."""
    try:
        from project_config import load_config

        node = load_config().get("state")
        return bool(isinstance(node, dict) and node.get("auto_export"))
    except Exception:  # noqa: BLE001 — config read is best-effort; default off
        return False


def _tree_root() -> str | None:
    try:
        from project_config import find_tausik_dir

        return os.path.join(os.path.dirname(find_tausik_dir()), "tausik")
    except Exception:  # noqa: BLE001
        return None


def auto_export_entity(svc: ProjectService, kind: str, slug: str) -> bool:
    """Best-effort: re-serialize ONE changed entity to its file. NEVER raises.

    Returns True iff a file was actually (re)written. A slug-less/absent/archived
    entity (export_one → None) is skipped silently — unlike the full export, the
    incremental trigger must be fail-open, not refuse. Idempotent: an unchanged
    file is left untouched (no mtime churn)."""
    try:
        if not _auto_export_enabled():
            return False
        from state_export import export_one

        result = export_one(svc, kind, slug)
        if result is None:
            return False
        rel, content = result
        root = _tree_root()
        if not root:
            return False
        path = os.path.join(root, rel.replace("/", os.sep))
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as fh:
                if fh.read() == content:
                    return False  # idempotent: no change → no write
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        return True
    except Exception as e:  # noqa: BLE001 — FAIL-OPEN: telemetry, never propagate
        _log.warning("auto-export %s/%s failed (non-fatal): %s", kind, slug, e)
        return False


def auto_export_by_id(svc: ProjectService, kind: str, entity_id: int) -> bool:
    """auto_export_entity for a call site that has the row id, not the slug."""
    try:
        table = {"decisions": "decisions", "memory": "memory"}.get(kind)
        if not table:
            return False
        row = svc.be._q1(f"SELECT slug FROM {table} WHERE id=?", (entity_id,))
        if not row or not row.get("slug"):
            return False
        return auto_export_entity(svc, kind, row["slug"])
    except Exception as e:  # noqa: BLE001 — fail-open
        _log.warning("auto-export %s#%s failed (non-fatal): %s", kind, entity_id, e)
        return False


def import_suggested(svc: ProjectService) -> dict[str, Any] | None:
    """Detect a `tausik/` tree that diverged from the DB (e.g. after `git pull`).

    Content-based (not mtime): a dry-run import reports what WOULD change; a
    non-empty plan means the files carry state the DB does not, so session start
    can suggest `tausik sync`. Returns a compact {added,updated,journal,edges}
    count dict when a sync is worth offering, else None. Fail-open → None."""
    try:
        root = _tree_root()
        if not root or not os.path.isdir(root):
            return None
        from state_import import import_tree

        report = import_tree(svc, root, dry=True)
        counts = {k: len(report.get(k, [])) for k in ("added", "updated", "journal", "edges")}
        return counts if any(counts.values()) else None
    except Exception as e:  # noqa: BLE001 — fail-open: never block session start
        _log.warning("import-suggested check failed (non-fatal): %s", e)
        return None
