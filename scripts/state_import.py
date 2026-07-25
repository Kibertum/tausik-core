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

from state_parse import ParseError, parse_frontmatter, parse_journal, parse_sections, split_file
from tausik_utils import utcnow_iso

if TYPE_CHECKING:
    from project_service import ProjectService

ENTITY_DIRS = ("epics", "stories", "tasks", "decisions", "memory")
TASK_SECTIONS = ["Goal", "Acceptance Criteria", "Plan", "Rollback", "Journal"]


def _json_or_none(value: Any) -> str | None:
    """A parsed list → its canonical JSON, or None for empty (undeclared)."""
    return json.dumps(value, ensure_ascii=False) if value else None


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
        "title": rec["fm"].get("title"),
        "status": rec["fm"].get("status"),
        "description": rec["body"] or None,
    }


def _story_cols(rec: dict, epic_id: int | None) -> dict:
    return {
        "epic_id": epic_id,
        "title": rec["fm"].get("title"),
        "status": rec["fm"].get("status"),
        "description": rec["body"] or None,
    }


def _task_cols(rec: dict, story_id: int | None) -> dict:
    fm, secs = rec["fm"], parse_sections(rec["body"], TASK_SECTIONS)
    return {
        "story_id": story_id,
        "title": fm.get("title"),
        "status": fm.get("status"),
        "stack": fm.get("stack"),
        "complexity": fm.get("complexity"),
        "role": fm.get("role"),
        "tier": fm.get("tier"),
        "goal": secs["Goal"] or None,
        "plan": secs["Plan"] or None,
        "acceptance_criteria": secs["Acceptance Criteria"] or None,
        "rollback_plan": secs["Rollback"] or None,
        "scope": fm.get("scope"),
        "scope_exclude": fm.get("scope_exclude"),
        "scope_paths": _json_or_none(fm.get("scope_paths")),
        "scope_tools": _json_or_none(fm.get("scope_tools")),
        "relevant_files": _json_or_none(fm.get("relevant_files")),
        "defect_of": fm.get("defect_of"),
        "call_budget": fm.get("call_budget"),
        "completed_at": fm.get("completed_at"),
    }


def _decision_cols(rec: dict) -> dict:
    secs = parse_sections(rec["body"], ["Decision", "Rationale"])
    return {
        "decision": secs["Decision"] or "",
        "task_slug": rec["fm"].get("task"),
        "rationale": secs["Rationale"] or None,
    }


def _memory_cols(rec: dict) -> dict:
    fm = rec["fm"]
    return {
        "type": fm.get("type"),
        "title": fm.get("title"),
        "content": rec["body"] or "",
        "tags": _json_or_none(fm.get("tags")),
        "task_slug": fm.get("task"),
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
        changed durable columns. Returns the row id (queried) for FK/edge wiring."""
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
            changed = {c: v for c, v in cols.items() if current.get(c) != v}
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

        Keyed on (created_at, message, phase) with COUNTS, not mere presence: the
        DB must end with exactly as many copies of each line as the file has, so a
        task with two genuinely-identical log rows round-trips both — while a
        re-import (counts already equal) still adds nothing (idempotent)."""
        from collections import Counter

        cur = self.conn.execute(
            "SELECT created_at, message, phase FROM task_logs WHERE task_slug=?", (task_slug,)
        )
        db_counts = Counter((r["created_at"], r["message"], r["phase"]) for r in cur.fetchall())
        file_counts = Counter((r["created_at"], r["message"], r["phase"]) for r in rows)
        for (created_at, message, phase), want in file_counts.items():
            for _ in range(want - db_counts.get((created_at, message, phase), 0)):
                self.report["journal"].append(f"{task_slug}: {message[:40]}")
                if not self.dry:
                    self.conn.execute(
                        "INSERT INTO task_logs(task_slug, message, phase, created_at) "
                        "VALUES(?,?,?,?)",
                        (task_slug, message, phase, created_at or now),
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
                tgt_id = id_maps.get(tgt_type, {}).get(e.get("target"))
                if tgt_id is None:
                    continue
                ap.edge(src_type, src_id, tgt_type, tgt_id, e.get("relation"), now)
