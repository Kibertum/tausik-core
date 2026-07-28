"""Lifecycle triggers for the git-native projection (state-git-triggers).

Ties export/import to the lifecycle so the `tausik/` files track the DB without
manual commands: a durable write incrementally re-serializes JUST the entity that
changed, and session start detects a tree that diverged from the DB (after a
`git pull`) and suggests `tausik sync`.

"A durable write" means EVERY mutation of the five projected kinds
(`state_import.ENTITY_DIRS`), not a chosen few. This once read "task done /
decide / memory add" and the code matched that prose: 18 of ~20 mutating service
methods never exported, so a decision recorded WITH a task_slug — the common
case — reached the DB and never the tree. A periodic full `tausik state export`
papered over it, which is why `status` reported no divergence. The property that
must hold is checked by test, not by counting call sites:
`build_tree(db)` == the tree on disk, after any sequence of mutations, with no
manual command in between.

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


def _tree_root(svc: ProjectService) -> str | None:
    """The `tausik/` projection dir for THIS svc's project.

    Derived from ``svc.tausik_dir()``, NOT the ambient ``find_tausik_dir()`` (the
    process cwd): keying on the cwd is the mcp-config-read-paths-ignore-project-
    handle defect — a mutation on one project's DB while cwd is another (e.g. a
    test with an isolated temp DB) would write the projection into the WRONG
    tree. Falls back to find_tausik_dir only if the svc cannot answer.
    """
    try:
        if hasattr(svc, "tausik_dir"):
            return os.path.join(os.path.dirname(os.path.abspath(svc.tausik_dir())), "tausik")
        from project_config import find_tausik_dir

        return os.path.join(os.path.dirname(find_tausik_dir()), "tausik")
    except Exception:  # noqa: BLE001
        return None


def auto_export_entity(svc: ProjectService, kind: str, slug: str) -> bool:
    """Best-effort: re-serialize ONE changed entity to its file. NEVER raises.

    Returns True iff the projection was actually changed — a file (re)written OR
    removed. Idempotent: an unchanged file is left untouched (no mtime churn).

    ``export_one → None`` means the entity is NOT in the projection any more:
    deleted, or (for memory) archived. That case used to return False and leave
    the stale file behind, so a delete produced a GHOST — a file describing a row
    the DB no longer has. A full `state export` never showed it (it rebuilds the
    whole tree from scratch); only the incremental path accumulated them. The
    projection must be able to shrink, so None now removes the file.
    """
    try:
        if not _auto_export_enabled():
            return False
        from state_export import export_one

        root = _tree_root(svc)
        if not root:
            return False
        result = export_one(svc, kind, slug)
        if result is None:
            return _remove_projection(root, kind, slug)
        rel, content = result
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


def _remove_projection(root: str, kind: str, slug: str) -> bool:
    """Drop the projection file for an entity that left the projection. True iff removed.

    The path is derived from (kind, slug) rather than from export_one, which by
    definition can no longer answer for a row that is gone. Kind is checked
    against the import-side registry so a typo cannot make this unlink an
    arbitrary path.
    """
    from state_import import ENTITY_DIRS

    if kind not in ENTITY_DIRS:
        return False
    path = os.path.join(root, kind, f"{slug}.md")
    if not os.path.isfile(path):
        return False
    os.remove(path)
    return True


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


def prewarm(svc: ProjectService) -> bool:
    """Pay `import_suggested`'s first-touch cost OFF the request path. Never raises.

    The check itself is cheap once warm (~0.6s over 2024 files here), but the
    FIRST call after process start also imports state_import/state_parse and
    cold-reads every file in the tree — which on Windows blew past the 6s
    section watchdog in `session_open`. That mattered more than it sounds: /start
    makes exactly ONE session_open call, and it is always the cold one, so the
    signal degraded to a timeout every single session and hid a real divergence
    for five of them.

    Called from a daemon thread at MCP startup: by the time a tool call arrives
    the modules are imported and the tree is in the page cache. Deliberately
    caches NO RESULT — divergence depends on both the tree AND the DB, so a
    memoized verdict would go stale on the next write. Warming I/O is always
    safe; remembering an answer is not.
    """
    try:
        root = _tree_root(svc)
        if not root or not os.path.isdir(root):
            return False
        from state_import import parse_tree, read_tree

        parse_tree(read_tree(root))
        return True
    except Exception as e:  # noqa: BLE001 — fail-open: a warm-up must never matter
        _log.warning("state prewarm failed (non-fatal): %s", e)
        return False


def import_suggested(svc: ProjectService) -> dict[str, Any] | None:
    """Detect a `tausik/` tree that diverged from the DB (e.g. after `git pull`).

    Content-based (not mtime): a dry-run import reports what WOULD change.
    Returns a compact {added,updated,journal,edges} count dict plus a `direction`
    when the tree and the DB disagree, else None. Fail-open → None.

    DIRECTION IS NOT INFERRED FROM DIVERGENCE. This used to read "a non-empty plan
    means the files carry state the DB does not, so suggest `tausik sync`" — an
    unsound step: a non-empty plan proves only that the two sides DIFFER, never
    which one is newer. The tree can just as easily be BEHIND (a projection not
    re-exported after a CLI close), and `sync` resolves file-wins, so acting on
    that advice would revert the DB to stale content — reopening closed tasks and
    undoing recorded decisions. Only what the counts actually prove is reported:
      * added/journal/edges > 0 — the tree holds entities, log lines or edges the
        DB has no row for. That IS one-directional: import can only add them.
      * updated alone — a field-level disagreement with no direction attached.
        The caller must offer BOTH `tausik sync` (tree is right) and
        `tausik state export` (DB is right) and let a human pick.
    """
    try:
        root = _tree_root(svc)
        if not root or not os.path.isdir(root):
            return None
        from state_import import import_tree

        report = import_tree(svc, root, dry=True)
        counts = {k: len(report.get(k, [])) for k in ("added", "updated", "journal", "edges")}
        if not any(counts.values()):
            return None
        tree_has_extra = bool(counts["added"] or counts["journal"] or counts["edges"])
        return {
            **counts,
            "direction": "tree-has-rows-db-lacks" if tree_has_extra else "field-divergence-only",
            "resolve": (
                "`tausik sync` imports the tree into the DB (files win). "
                "`tausik state export` rewrites the tree from the DB. "
                "Which is correct depends on WHICH SIDE IS NEWER — the counts alone "
                "do not establish that, so confirm before running either."
            ),
        }
    except Exception as e:  # noqa: BLE001 — fail-open: never block session start
        _log.warning("import-suggested check failed (non-fatal): %s", e)
        return None
