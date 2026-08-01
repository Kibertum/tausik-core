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
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from project_service import ProjectService

_log = logging.getLogger("tausik.state.triggers")


def _auto_export_enabled(tausik_dir: str) -> bool:
    """True iff `state.auto_export` is truthy IN THIS PROJECT. Any error → False (off).

    ``tausik_dir`` selects which ``.tausik/config.json`` answers, and it is
    REQUIRED — not defaulted to the ambient project. Calling ``load_config()``
    with no argument, which this did, reads the config of the process cwd: the
    same mcp-config-read-paths-ignore-project-handle defect ``_tree_root`` names
    three lines below, one policy layer up. The address had been fixed and the
    switch had not, so a mutation on one project's DB was switched on by ANOTHER
    project's config. That is how the whole test suite acquired a projection
    nobody asked for — no test ever set `state.auto_export`, this repository's
    own config set it for every temp DB pytest built.

    The caller derives the argument from the address already in use rather than
    resolving a project a second time, so the two cannot disagree about which
    project is being asked.
    """
    try:
        from project_config import load_config

        node = load_config(tausik_dir).get("state")
        return bool(isinstance(node, dict) and node.get("auto_export"))
    except Exception:  # noqa: BLE001 — config read is best-effort; default off
        return False


def _tree_root(svc: ProjectService) -> str | None:
    """The `tausik/` projection dir for THIS svc's project, or None if there is no project.

    Two properties, each learned by getting it wrong.

    NOT THE AMBIENT ``find_tausik_dir()`` (the process cwd): keying on the cwd is
    the mcp-config-read-paths-ignore-project-handle defect — a mutation on one
    project's DB while cwd is another (e.g. a test with an isolated temp DB)
    would write the projection into the WRONG tree.

    AND NOT ANY ``dirname(db_path)``. The address is ``dirname(tausik_dir)`` plus
    ``tausik``, which names a project root only when ``tausik_dir`` IS some
    project's ``.tausik/`` — an invariant this inherited from ProjectService
    without inheriting what enforced it. Once ``auto_export_write`` moved the
    trigger down to a bare ``SQLiteBackend``, the invariant stopped holding:
    ``SQLiteBackend("<tmp>/case0/tausik.db")`` answers ``<tmp>/case0``, and the
    projection went to ``<tmp>/tausik`` — a SIBLING of case0, outside anything
    the caller owns; at ``:memory:`` it went beside the repository. So the
    directory must NAME itself, and when it does not, there is no projection at
    all rather than one somewhere else. Fail-closed, like the brain publish
    guard, because the costs are asymmetric: a false negative loses one
    unprojected row, a false positive writes into a directory nobody named —
    measured, 31 files in the shared pytest basetemp under colliding universal
    slugs (`e`, `s`, `mvp`, `setup`), never cleaned up.
    """
    try:
        from project_config import TAUSIK_DIR, find_tausik_dir

        tausik_dir = os.path.abspath(
            svc.tausik_dir() if hasattr(svc, "tausik_dir") else find_tausik_dir()
        )
        if os.path.basename(tausik_dir) != TAUSIK_DIR:
            return None
        return os.path.join(os.path.dirname(tausik_dir), "tausik")
    except Exception:  # noqa: BLE001
        return None


def auto_export_entity(
    svc: ProjectService, kind: str, slug: str, *, follow_edges: bool = True
) -> bool:
    """Best-effort: re-serialize ONE changed entity to its file. NEVER raises.

    Returns True iff the projection was actually changed — a file (re)written OR
    removed. Idempotent: an unchanged file is left untouched (no mtime churn).

    ``export_one → None`` means the entity is NOT in the projection any more:
    deleted, or (for memory) archived. That case used to return False and leave
    the stale file behind, so a delete produced a GHOST — a file describing a row
    the DB no longer has. A full `state export` never showed it (it rebuilds the
    whole tree from scratch); only the incremental path accumulated them. The
    projection must be able to shrink, so None now removes the file.

    A departure also restales OTHER files: an `edges:` block naming the row that
    just left now points at nothing, and `build_tree` drops such an edge (with a
    warning) while the incremental path never re-rendered the source. That is why
    the departure — the one signal shared by delete and archive — is where the
    referring entities are refreshed. `follow_edges=False` on the inner call
    bounds the recursion at one hop.
    """
    try:
        root = _tree_root(svc)
        if not root:
            return False
        # The switch is read from the project the address POINTS AT, not resolved
        # anew: `_tree_root` guarantees `<project>/tausik`, so its sibling is that
        # project's `.tausik/`. Deriving it makes "where we write" and "may we
        # write" structurally incapable of naming two different projects.
        from project_config import TAUSIK_DIR

        if not _auto_export_enabled(os.path.join(os.path.dirname(root), TAUSIK_DIR)):
            return False
        from state_export import export_one

        result = export_one(svc, kind, slug)
        if result is None:
            removed = _remove_projection(root, kind, slug)
            # Only memory/decisions can be an edge endpoint (the CHECK constraint
            # on memory_edges says so), so a departing epic/story/task cannot
            # strand one — no reason to pay for the sweep there.
            if follow_edges and kind in ("memory", "decisions"):
                _reproject_orphaned_edge_sources(svc)
            return removed
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


_ORPHANED_EDGE_SOURCES = """
SELECT DISTINCT source_type, source_id FROM memory_edges WHERE valid_to IS NULL AND (
    (target_type='memory'   AND target_id NOT IN (SELECT id FROM memory WHERE archived_at IS NULL))
 OR (target_type='decision' AND target_id NOT IN (SELECT id FROM decisions))
)
"""


def _reproject_orphaned_edge_sources(svc: ProjectService) -> int:
    """Re-serialize every entity holding a live edge to a row that left. Never raises.

    Asked as a QUESTION OF THE DATA — "which live edges now point outside the
    projection" — rather than "which rows referenced the one just deleted",
    because after a DELETE the departed row's id is no longer recoverable from
    its slug. One consequence of that form is real: an edge orphaned by any
    means, past or future, is picked up on the next departure, without anyone
    having to have routed it here.

    IT DOES NOT CONVERGE, and this used to be called "self-healing", which reads
    as if it did. Re-serializing the SOURCE does not touch `memory_edges`, so the
    predicate this scan runs on never clears: the same orphans are found, and
    the same files re-rendered, on every subsequent departure, forever.

    MEASURED, so the cost is a number and not a worry — 2000 memory rows, 40
    orphaned edges, three consecutive sweeps:

        sweep #1: returned=40  export_one=40  47ms   orphans_left=40
        sweep #2: returned=0   export_one=40  281ms  orphans_left=40
        sweep #3: returned=0   export_one=40  16ms   orphans_left=40

    `returned=0` with `export_one=40` is the whole defect in one line: forty
    serializations that changed nothing. It is bounded by the ORPHAN count, not
    by tree size, but archived memory only ever grows, so the per-departure bill
    grows monotonically with it.

    Converging means invalidating the edge (`valid_to`) when its target leaves —
    and that belongs at the SERVICE layer, where the archive or the delete
    happens, not in a fail-open projection trigger that would then be writing to
    the database it is downstream of. Tracked as
    `orphaned-edges-never-converge-so-every-departure-pays-for-them`; deliberately
    not smuggled in here.

    `memory_edges` is polymorphic (`source_type`/`target_type` instead of a
    foreign key), so `_projection_victims` — which reads PRAGMA foreign_key_list
    — is structurally unable to see this dependency. It is real regardless of
    whether the schema can express it, which is why it is followed by hand here
    and nowhere else.
    """
    try:
        rows = svc.be._q(_ORPHANED_EDGE_SOURCES)
    except Exception as e:  # noqa: BLE001 — fail-open: the DB write already happened
        _log.warning("orphaned-edge sweep failed (non-fatal): %s", e)
        return 0
    changed = 0
    for row in rows:
        kind = "memory" if row["source_type"] == "memory" else "decisions"
        try:
            table = "memory" if kind == "memory" else "decisions"
            src = svc.be._q1(f"SELECT slug FROM {table} WHERE id=?", (row["source_id"],))
            if src and src.get("slug"):
                changed += auto_export_entity(svc, kind, src["slug"], follow_edges=False)
        except Exception as e:  # noqa: BLE001 — fail-open, per-row
            _log.warning("re-export of edge source %s failed (non-fatal): %s", row, e)
    return changed


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


class _BackendView:
    """A bare backend, dressed as the two attributes the exporter actually reads.

    `export_one` touches only `svc.be._q`, and `_tree_root` only `svc.tausik_dir()`
    — which `ProjectService` itself defines as `dirname(abspath(be.db_path))`. So
    a backend can answer both without a service, and `auto_export_write` can hang
    the projection off the write layer instead of off ~20 remembered call sites.
    Deliberately NOT a `be` attribute on `SQLiteBackend`: the backend does not
    become a service, it is only viewed as one, here, for one purpose.
    """

    __slots__ = ("be",)

    def __init__(self, be: Any) -> None:
        self.be = be

    def tausik_dir(self) -> str:
        return os.path.dirname(os.path.abspath(str(self.be.db_path)))


def auto_export_write(be: Any, table: str, slug: str) -> bool:
    """Project the row a backend write just COMMITTED. NEVER raises.

    WHAT THIS COVERS, EXACTLY: `_update` (a whitelisted UPDATE by slug) and the
    three `_delete_projected` calls on epics/stories/tasks. Nothing else. This
    docstring used to claim that "a mutator nobody remembers is covered on the
    commit that introduces it", and that was false — measured, not argued: with
    ONLY the manual service-layer calls silenced and this hook fully alive, the
    projection property goes red on all six seeds
    (`test_the_hook_alone_does_not_carry_the_projection`).

    WHAT THIS DOES NOT COVER, by name, so no one has to rediscover it:
      * every INSERT — `_ins` takes raw SQL and knows neither table nor slug, so
        epic_add / story_add / task_add / decision_add / memory_add reach the DB
        and not the tree;
      * `memory` and `decisions` as kinds — their projected files are keyed by
        row id, not by a slug column, and `memory_delete` is a raw `_ex`;
      * the budget setters (`task_set_call_budget`, `task_set_cost_budget`,
        `task_set_token_budget`, the `*_actual` writers) — raw `_ex` on tasks,
        writing the PROJECTED columns `call_budget` and `tier`;
      * `task_append_notes` and `task_claim` — raw `_ex`;
      * the bulk `UPDATE memory SET archived_at` in `backend_graph`.

    SO WHO GUARANTEES COVERAGE? Not this hook, and not the ~18 manual
    `auto_export_entity` / `auto_export_by_id` calls in the service layer either.
    Both are implementations. The guarantee is the PROPERTY — after any sequence
    of mutations with no manual command in between, the tree equals
    `build_tree(db)` — checked on generated sequences with a write-path ratchet
    (`tests/test_state_projection_tracks_db.py`). Adding a mutator means adding
    it to that test's operation set; the ratchet then tells you whether you
    introduced a write path nobody accounted for. That is one answer to "is my
    new mutator covered", and it is the only one that is true.

    The manual calls therefore STAY. Removing them as redundant is what this
    docstring used to invite, and it would silently break the projection for
    every kind listed above. Completing the hook is real work — it means giving
    `_ins` a table and a slug at every call site, moving the raw `_ex` writers
    onto `_update`, and resolving ids for the bulk archive — and it is tracked
    as `v2-projection-hook-covers-every-write`, not pretended to be done here.

    Membership is asked of the export registry (`ENTITY_DIRS`), not of a table
    list kept here — the two would drift, which is the same defect one layer up.
    """
    try:
        from state_import import ENTITY_DIRS

        if table not in ENTITY_DIRS:
            return False
        return auto_export_entity(cast("ProjectService", _BackendView(be)), table, slug)
    except Exception as e:  # noqa: BLE001 — FAIL-OPEN: the DB write already happened
        _log.warning("auto-export write %s/%s failed (non-fatal): %s", table, slug, e)
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
