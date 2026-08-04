"""git-native tree → DB cache import (state-git-import, `tausik state import`/`sync`).

The inverse of state_export: reads the `tausik/` tree (the canonical source of
truth) and rebuilds/updates the SQLite working cache — what an engineer runs after
`git pull` / `git checkout` so the DB reflects the branch. Read-only on the tree,
write-only on the DB.

Contract (docs/ru/team-state-in-git.md):
  * Round-trip: import(export(db)) is equivalent to db by entity set, durable
    fields and the memory graph.
  * Idempotent + delta: an unchanged file touches no row; only entities whose
    parsed projection differs from the current row are written.
  * git wins, but never silently: every overwrite of a locally-diverged row is
    reported, `--dry-run` shows the plan, and NOTHING is deleted (an incremental
    import never removes an entity absent from the tree — a `checkout` of one
    branch must not erase work not yet merged from another).
  * Transactional batch: a malformed file aborts the whole apply (rollback), never
    a partial DB.
  * FTS is rebuilt so search sees the imported state.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from state_export import _dedup_preserve, _json_list  # emitter's own list canonicalizers
from state_parse import ParseError, parse_frontmatter, parse_journal, parse_sections, split_file
from state_serialize import ENTITY_DIRS as _CANONICAL_ENTITY_DIRS
from state_serialize import flatten_line, normalize_body, normalize_ts
from tausik_utils import utcnow_iso

if TYPE_CHECKING:
    from project_service import ProjectService

# Re-exported for readers that walk the tree; declared in state_serialize.
ENTITY_DIRS = _CANONICAL_ENTITY_DIRS
TASK_SECTIONS = ["Goal", "Acceptance Criteria", "Plan", "Rollback", "Journal"]


class _Absent:
    """The file did not declare this key AT ALL — distinct from declaring it empty.

    `fm.get(key)` collapses both into None, which made an omitted key read as a
    request to clear the column: a projection written before a field was set would
    silently revert the DB on the next `sync`. Columns carrying this sentinel are
    dropped from the delta entirely — never compared, never written. An EXPLICIT
    empty value (`key: []`, `key: null`) is untouched and still clears, so the
    git-wins policy holds for divergence while absence stops being a command.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return "ABSENT"


ABSENT = _Absent()


def _fm(fm: dict, key: str) -> Any:
    """A frontmatter scalar, or ABSENT when the file never mentions the key."""
    return fm[key] if key in fm else ABSENT


def _json_or_none(value: Any) -> str | None:
    """A parsed list → its canonical JSON, or None for empty (undeclared)."""
    return json.dumps(value, ensure_ascii=False) if value else None


def _fm_list(fm: dict, key: str) -> Any:
    """`_json_or_none` for a frontmatter list, preserving the ABSENT distinction."""
    return _json_or_none(fm[key]) if key in fm else ABSENT


# --- canonical comparison space ----------------------------------------------
#
# The projection is a LOSSY, CANONICALIZING view: the emitter sorts memory tags,
# dedups task path lists, reformats timestamps to the `Z` form and flattens
# multi-line journal messages onto one line. Comparing a raw DB value against an
# already-canonical file value therefore reports the canonicalization ITSELF as a
# change — which is how `sync` came to want 336 phantom row rewrites and 437
# truncated duplicate journal lines on this repo. The detector has to speak the
# dialect the file is written in, so both sides are pushed through the emitter's
# OWN helpers (imported, never re-implemented, so the two cannot drift apart).
#
# This governs comparison only. What gets WRITTEN on a real divergence is still
# the file's value: git wins, unchanged.

_SORTED_LIST_COLS = frozenset({"tags"})  # _memory_doc: sorted()
_ORDERED_LIST_COLS = frozenset({"relevant_files", "scope_paths", "scope_tools"})  # _dedup_preserve
_TS_COLS = frozenset({"completed_at"})  # normalize_ts
_PROSE_COLS = frozenset(  # render_file/section → normalize_body
    {
        "goal",
        "plan",
        "acceptance_criteria",
        "rollback_plan",
        "description",
        "content",
        "decision",
        "rationale",
    }
)


def _canon(col: str, value: Any) -> Any:
    """The value as the emitter would have written it — for COMPARISON only."""
    if col in _SORTED_LIST_COLS:
        return json.dumps(sorted(_json_list(value)), ensure_ascii=False)
    if col in _ORDERED_LIST_COLS:
        return json.dumps(_dedup_preserve(_json_list(value)), ensure_ascii=False)
    if col in _TS_COLS:
        return normalize_ts(value)
    if col in _PROSE_COLS:
        return normalize_body(value)
    return value


def _journal_key(row: dict) -> tuple[str, str, str | None]:
    """Multiset key for one journal line, in the emitter's canonical dialect."""
    return (
        normalize_ts(row.get("created_at")) or "",
        flatten_line(row.get("message")),
        (row.get("phase") or "").strip() or None,
    )


def _require_slug(fm: dict, rel: str) -> str:
    slug = fm.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        raise ParseError(f"{rel}: missing required 'slug' in frontmatter")
    return slug


# --- read + parse the tree ---------------------------------------------------


def read_tree(root: str) -> dict[str, str]:
    """{relative-path: content} for every *.md under the entity subdirectories."""
    tree: dict[str, str] = {}
    for sub in ENTITY_DIRS:
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if name.endswith(".md"):
                with open(os.path.join(base, name), encoding="utf-8", newline="") as fh:
                    tree[f"{sub}/{name}"] = fh.read()
    return tree


def parse_tree(tree: dict[str, str]) -> dict[str, list[dict]]:
    """Parse every file into {kind: [record, ...]}. Raises ParseError (whole batch).

    A record is {slug, fm, body, rel}; the caller maps it to DB columns. Parsing
    is fully separated from applying so a single bad file aborts BEFORE any write.
    """
    out: dict[str, list[dict]] = {k: [] for k in ENTITY_DIRS}
    for rel in sorted(tree):
        kind = rel.split("/", 1)[0]
        try:
            fm_text, body = split_file(tree[rel])
            fm = parse_frontmatter(fm_text)
        except ParseError as e:
            raise ParseError(f"{rel}: {e}") from e
        slug = _require_slug(fm, rel)
        out[kind].append({"slug": slug, "fm": fm, "body": body, "rel": rel})
    return out


# --- column mappers (file record → DB columns) -------------------------------


def _epic_cols(rec: dict) -> dict:
    return {
        "title": _fm(rec["fm"], "title"),
        "status": _fm(rec["fm"], "status"),
        "description": rec["body"] or None,
    }


def _story_cols(rec: dict, epic_id: int | None) -> dict:
    return {
        "epic_id": epic_id,
        "title": _fm(rec["fm"], "title"),
        "status": _fm(rec["fm"], "status"),
        "description": rec["body"] or None,
    }


def _task_cols(rec: dict, story_id: int | None) -> dict:
    fm, secs = rec["fm"], parse_sections(rec["body"], TASK_SECTIONS)
    return {
        "story_id": story_id,
        "title": _fm(fm, "title"),
        "status": _fm(fm, "status"),
        "stack": _fm(fm, "stack"),
        "complexity": _fm(fm, "complexity"),
        "role": _fm(fm, "role"),
        "tier": _fm(fm, "tier"),
        "goal": secs["Goal"] or None,
        "plan": secs["Plan"] or None,
        "acceptance_criteria": secs["Acceptance Criteria"] or None,
        "rollback_plan": secs["Rollback"] or None,
        "scope": _fm(fm, "scope"),
        "scope_exclude": _fm(fm, "scope_exclude"),
        "scope_paths": _fm_list(fm, "scope_paths"),
        "scope_tools": _fm_list(fm, "scope_tools"),
        "relevant_files": _fm_list(fm, "relevant_files"),
        "defect_of": _fm(fm, "defect_of"),
        "call_budget": _fm(fm, "call_budget"),
        "completed_at": _fm(fm, "completed_at"),
    }


def _decision_cols(rec: dict) -> dict:
    secs = parse_sections(rec["body"], ["Decision", "Rationale"])
    return {
        "decision": secs["Decision"] or "",
        "task_slug": _fm(rec["fm"], "task"),
        "rationale": secs["Rationale"] or None,
    }


def _memory_cols(rec: dict) -> dict:
    fm = rec["fm"]
    return {
        "type": _fm(fm, "type"),
        "title": _fm(fm, "title"),
        "content": rec["body"] or "",
        "tags": _fm_list(fm, "tags"),
        "task_slug": _fm(fm, "task"),
    }


# --- generic idempotent upsert ----------------------------------------------


class _Applier:
    """Delta upsert over one connection; collects a report, honours dry-run."""

    def __init__(self, conn, dry: bool) -> None:
        self.conn = conn
        self.dry = dry
        self.report: dict[str, list[str]] = {"added": [], "updated": [], "journal": []}

    def _rows(self, table: str) -> dict[str, dict]:
        cur = self.conn.execute(f"SELECT * FROM {table}")
        cols = [c[0] for c in cur.description]
        return {r["slug"]: {c: r[c] for c in cols} for r in cur.fetchall()}

    def upsert(
        self, table: str, slug: str, cols: dict, current: dict | None, insert_extra: dict
    ) -> int | None:
        """INSERT (with insert_extra: slug + synthesized created_at/…) or UPDATE the
        changed durable columns. Returns the row id (queried) for FK/edge wiring.

        Columns the file never declared (ABSENT) are dropped before anything else:
        an omitted key is not a request to clear the column. What remains is
        compared in the emitter's canonical space (`_canon`) so the projection's
        own normalization never reads as a change — but written verbatim, so a
        genuine divergence still resolves file-wins."""
        cols = {c: v for c, v in cols.items() if v is not ABSENT}
        if current is None:
            allcols = {**cols, **insert_extra, "slug": slug}
            self.report["added"].append(f"{table}/{slug}")
            if not self.dry:
                names = ",".join(allcols)
                self.conn.execute(
                    f"INSERT INTO {table}({names}) VALUES({','.join('?' * len(allcols))})",
                    tuple(allcols.values()),
                )
        else:
            changed = {c: v for c, v in cols.items() if _canon(c, current.get(c)) != _canon(c, v)}
            if changed:
                self.report["updated"].append(f"{table}/{slug}")
                if not self.dry:
                    sets = ",".join(f"{c}=?" for c in changed)
                    self.conn.execute(
                        f"UPDATE {table} SET {sets} WHERE slug=?",
                        (*changed.values(), slug),
                    )
        row = self.conn.execute(f"SELECT id FROM {table} WHERE slug=?", (slug,)).fetchone()
        return row["id"] if row else None

    def journal(self, task_slug: str, rows: list[dict], now: str) -> None:
        """Reconcile the journal to the file as a MULTISET (append-only).

        Keyed with COUNTS, not mere presence: the DB must end with exactly as many
        copies of each line as the file has, so a task with two genuinely-identical
        log rows round-trips both — while a re-import (counts already equal) still
        adds nothing (idempotent).

        The key is the emitter's CANONICAL form (`_journal_key`), not the raw text.
        `_journal_section` flattens a multi-line message onto one line by design —
        a journal entry must stay one line so two branches merge as added lines —
        so a raw comparison never matches a multi-line DB row and would append a
        flattened duplicate of it on every single sync. Canonical keying makes the
        multiset comparable; the row still INSERTs verbatim from the file."""
        from collections import Counter

        cur = self.conn.execute(
            "SELECT created_at, message, phase FROM task_logs WHERE task_slug=?", (task_slug,)
        )
        db_counts = Counter(_journal_key(dict(r)) for r in cur.fetchall())
        file_rows: dict[tuple, list[dict]] = {}
        for row in rows:
            file_rows.setdefault(_journal_key(row), []).append(row)
        for key, group in file_rows.items():
            for row in group[: max(0, len(group) - db_counts.get(key, 0))]:
                message = row.get("message") or ""
                self.report["journal"].append(f"{task_slug}: {message[:40]}")
                if not self.dry:
                    self.conn.execute(
                        "INSERT INTO task_logs(task_slug, message, phase, created_at) "
                        "VALUES(?,?,?,?)",
                        (task_slug, message, row.get("phase"), row.get("created_at") or now),
                    )

    def edge(
        self, src_type: str, src_id: int, tgt_type: str, tgt_id: int, relation: str, now: str
    ) -> None:
        """Insert a valid edge if an equivalent one is not already present."""
        found = self.conn.execute(
            "SELECT 1 FROM memory_edges WHERE source_type=? AND source_id=? AND "
            "target_type=? AND target_id=? AND relation=? AND valid_to IS NULL",
            (src_type, src_id, tgt_type, tgt_id, relation),
        ).fetchone()
        if found:
            return
        self.report.setdefault("edges", []).append(f"{src_type}#{src_id}->{tgt_type}#{tgt_id}")
        if not self.dry:
            self.conn.execute(
                "INSERT INTO memory_edges(source_type, source_id, target_type, target_id, "
                "relation, confidence, valid_from, created_at) VALUES(?,?,?,?,?,1.0,?,?)",
                (src_type, src_id, tgt_type, tgt_id, relation, now, now),
            )


def _reindex_fts(conn) -> None:
    """Rebuild every external-content FTS index so search sees the imported state."""
    from backend_init import external_content_fts_tables

    for fts in external_content_fts_tables(conn.cursor()):
        try:
            conn.execute(f"INSERT INTO {fts}({fts}) VALUES('rebuild')")
        except Exception:  # noqa: BLE001 — maintenance, non-fatal to the import
            pass


def import_tree(svc: ProjectService, root: str, dry: bool = False) -> dict[str, list[str]]:
    """Read the tree, parse it (whole-batch abort on a bad file), apply the delta.

    Files win over the DB but never silently: the returned report lists every
    add/update/journal/edge so the caller can show what changed (and --dry-run
    shows the plan with no write). Nothing is deleted (incremental, not mirror).
    """
    parsed = parse_tree(read_tree(root))  # ParseError here → nothing written
    now = utcnow_iso()
    conn = svc.be._conn
    ap = _Applier(conn, dry)
    if not dry:
        svc.be.begin_tx()
        # tasks.defect_of is a self-referential FK, and rows are applied in slug
        # order (not dependency order), so a task referencing a not-yet-inserted
        # sibling would trip the per-statement FK check. Defer enforcement to
        # COMMIT, by when every slug exists (reset automatically at tx end).
        conn.execute("PRAGMA defer_foreign_keys=ON")
    try:
        epic_id, story_id = {}, {}
        cur = ap._rows("epics")
        for rec in parsed["epics"]:
            epic_id[rec["slug"]] = ap.upsert(
                "epics", rec["slug"], _epic_cols(rec), cur.get(rec["slug"]), {"created_at": now}
            )
        cur = ap._rows("stories")
        for rec in parsed["stories"]:
            eid = epic_id.get(rec["fm"].get("epic"))
            story_id[rec["slug"]] = ap.upsert(
                "stories",
                rec["slug"],
                _story_cols(rec, eid),
                cur.get(rec["slug"]),
                {"created_at": now},
            )
        cur = ap._rows("tasks")
        for rec in parsed["tasks"]:
            sid = story_id.get(rec["fm"].get("story"))
            ap.upsert(
                "tasks",
                rec["slug"],
                _task_cols(rec, sid),
                cur.get(rec["slug"]),
                {"created_at": now, "updated_at": now},
            )
            ap.journal(
                rec["slug"],
                parse_journal(parse_sections(rec["body"], TASK_SECTIONS)["Journal"]),
                now,
            )
        cur = ap._rows("decisions")
        dec_id: dict[str, int | None] = {}
        for rec in parsed["decisions"]:
            date = rec["fm"].get("date")
            dec_id[rec["slug"]] = ap.upsert(
                "decisions",
                rec["slug"],
                _decision_cols(rec),
                cur.get(rec["slug"]),
                {"created_at": (date if isinstance(date, str) and date else now)},
            )
        cur = ap._rows("memory")
        mem_id: dict[str, int | None] = {}
        for rec in parsed["memory"]:
            mem_id[rec["slug"]] = ap.upsert(
                "memory",
                rec["slug"],
                _memory_cols(rec),
                cur.get(rec["slug"]),
                {"created_at": now, "updated_at": now},
            )
        _apply_edges(ap, parsed, {"memory": mem_id, "decision": dec_id}, now)
        if not dry:
            _reindex_fts(conn)
            svc.be.commit_tx()
    except Exception:
        if not dry:
            svc.be.rollback_tx()
        raise
    return ap.report


def _apply_edges(ap: _Applier, parsed: dict, id_maps: dict[str, dict], now: str) -> None:
    """Reconstruct memory_edges from the `edges` block of memory/decision files."""
    for src_type, kind in (("memory", "memory"), ("decision", "decisions")):
        for rec in parsed[kind]:
            src_id = id_maps[src_type].get(rec["slug"])
            if src_id is None:
                continue
            for e in rec["fm"].get("edges") or []:
                if not isinstance(e, dict):
                    continue
                tgt_type = e.get("target_type")
                relation = e.get("relation")
                if not isinstance(tgt_type, str) or not isinstance(relation, str):
                    # Malformed edge FM (non-string target_type/relation). Dropping
                    # it is correct, but never silently: a partially-corrupted file
                    # would otherwise lose real relationships on import with no
                    # signal. Surface it in the report so the operator sees it.
                    ap.report.setdefault("skipped_edges", []).append(
                        f"{src_type}/{rec['slug']}: malformed edge "
                        f"(target_type={tgt_type!r}, relation={relation!r})"
                    )
                    continue
                tgt_id = id_maps.get(tgt_type, {}).get(e.get("target"))
                if tgt_id is None:
                    continue
                ap.edge(src_type, src_id, tgt_type, tgt_id, relation, now)
