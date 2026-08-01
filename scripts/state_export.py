"""DB → `tausik/` git-native state export (state-git-export, Decision #172).

One file per entity under `tausik/{epics,stories,tasks,decisions,memory}/<slug>.md`,
markdown + YAML frontmatter, so durable project state travels git-native and
merges by identity (the stable slug from state-git-stable-ids), branch-coupled to
the code. Scope here is DB→files only; the inverse is `state-git-import`.

Scope of entities (from the task goal/AC): tasks, task_logs (→ task Journal),
epics, stories, decisions, memory, memory_edges (→ edges on the source file).
`specs`/`task_specs` travel per the spec but are OUT of this task's scope. Only
**live** state is projected: archived memory (`archived_at`) and invalidated
edges (`valid_to`) are retired, not durable shared state — excluded by design.

Determinism (the whole point) is enforced in :mod:`state_serialize`; this module
owns the entity field selection, the fixed frontmatter key order, and the
deterministic ordering of every multi-valued field (entities by slug, tags
alphabetical, edges by `(relation, target_type, target)`, journal by
`(created_at, id)`, ordered lists deduped preserving declared order).

Read-only on the DB. Refuses (loudly) to export a slug-less decision/memory — a
pre-migration DB must run state-git-stable-ids first, never get an ephemeral slug
that would diverge between machines.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from state_serialize import (
    ENTITY_DIRS as _CANONICAL_ENTITY_DIRS,
    flatten_line,
    join_sections,
    normalize_ts,
    render_file,
    section,
)

if TYPE_CHECKING:
    from project_service import ProjectService


class ExportError(Exception):
    """A precondition the export refuses to paper over (e.g. a slug-less entity)."""


# The top-level subdirectories this exporter OWNS. Deletion reconciliation is
# scoped to these so a hand-written file elsewhere under tausik/ (a root
# README.md, a NOTES/ dir) is never swept — see state_serialize._managed_on_disk.
# Derived, not re-declared — see state_serialize.ENTITY_DIRS for why.
ENTITY_DIRS = frozenset(_CANONICAL_ENTITY_DIRS)


# --- small pure helpers ------------------------------------------------------


def _json_list(raw: Any) -> list[str]:
    """Lenient JSON-list parse → list of non-empty strings ([] on any defect)."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if isinstance(v, str) and v.strip()]


def _dedup_preserve(items: list[str]) -> list[str]:
    """Drop duplicates keeping first-seen order (list order is a declared signal)."""
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def _edge_rows(
    edges: list[dict[str, Any]],
    source_type: str,
    source_id: int,
    id_to_slug: dict[tuple[str, int], str],
    warnings: list[str],
    origin: str,
) -> list[list[tuple[str, Any]]]:
    """Ordered-mapping rows for edges whose SOURCE is this entity.

    Each row is `[(relation, r), (target_type, tt), (target, slug)]`, sorted by
    `(relation, target_type, target)` for byte-stability. A valid edge whose
    target row is gone is DROPPED with a warning (never silently) — it cannot be
    given a stable slug and the target no longer exists.
    """
    rows: list[tuple[str, str, str]] = []
    for e in edges:
        if e["source_type"] != source_type or e["source_id"] != source_id:
            continue
        target = id_to_slug.get((e["target_type"], e["target_id"]))
        if target is None:
            warnings.append(
                f"dropped dangling edge from {origin}: {e['relation']} -> "
                f"{e['target_type']}#{e['target_id']} (target has no exported slug)"
            )
            continue
        rows.append((e["relation"], e["target_type"], target))
    # sorted(set(...)): a non-'supersedes' relation can be linked twice between the
    # same node pair — collapse logically-identical edges, as relevant_files does.
    return [
        [("relation", rel), ("target_type", tt), ("target", tgt)]
        for rel, tt, tgt in sorted(set(rows))
    ]


# --- per-entity renderers ----------------------------------------------------


def _epic_doc(epic: dict[str, Any]) -> str:
    pairs = [("slug", epic["slug"]), ("title", epic["title"]), ("status", epic["status"])]
    return render_file(pairs, epic.get("description"))


def _story_doc(story: dict[str, Any], epic_slug: str | None) -> str:
    pairs = [
        ("slug", story["slug"]),
        ("title", story["title"]),
        ("status", story["status"]),
        ("epic", epic_slug),
    ]
    return render_file(pairs, story.get("description"))


def _task_doc(task: dict[str, Any], story_slug: str | None, epic_slug: str | None) -> str:
    pairs: list[tuple[str, Any]] = [
        ("slug", task["slug"]),
        ("title", task["title"]),
        ("status", task["status"]),
        ("epic", epic_slug),
        ("story", story_slug),
        ("complexity", task.get("complexity")),
        ("role", task.get("role")),
        ("stack", task.get("stack")),
        ("tier", task.get("tier")),
        ("call_budget", task.get("call_budget")),
        ("defect_of", task.get("defect_of")),
        ("scope", task.get("scope")),
        ("scope_exclude", task.get("scope_exclude")),
        ("relevant_files", _dedup_preserve(_json_list(task.get("relevant_files")))),
        ("scope_paths", _dedup_preserve(_json_list(task.get("scope_paths")))),
        ("scope_tools", _dedup_preserve(_json_list(task.get("scope_tools")))),
        ("completed_at", normalize_ts(task.get("completed_at"))),
    ]
    body = join_sections(
        section("Goal", task.get("goal")),
        section("Acceptance Criteria", task.get("acceptance_criteria")),
        section("Plan", task.get("plan")),
        section("Rollback", task.get("rollback_plan")),
        _journal_section(task.get("_journal", [])),
    )
    return render_file(pairs, body)


def _journal_section(logs: list[dict[str, Any]]) -> list[str]:
    """`## Journal` block: one append-only line per task_log, oldest first."""
    lines = ["## Journal", ""]
    for row in logs:
        ts = normalize_ts(row.get("created_at")) or ""
        phase = (row.get("phase") or "").strip()
        msg = flatten_line(row.get("message"))
        marker = f" [{phase}]" if phase else ""
        lines.append(f"- {ts}{marker} — {msg}")
    return lines


def _decision_doc(dec: dict[str, Any], edges: list[list[tuple[str, Any]]]) -> str:
    date = normalize_ts(dec.get("created_at"))
    pairs = [
        ("slug", dec["slug"]),
        ("task", dec.get("task_slug")),
        ("date", (date or "")[:10] or None),
        ("edges", edges),
    ]
    body = join_sections(
        section("Decision", dec.get("decision")),
        section("Rationale", dec.get("rationale")),
    )
    return render_file(pairs, body)


def _memory_doc(mem: dict[str, Any], edges: list[list[tuple[str, Any]]]) -> str:
    tags = sorted(_json_list(mem.get("tags")))
    pairs = [
        ("slug", mem["slug"]),
        # `title` is a NOT NULL durable column and slug→title is lossy/non-
        # invertible, so it must be serialized for round-trip completeness (AC-2)
        # even though the spec's illustrative memory template omits it.
        ("title", mem["title"]),
        ("type", mem["type"]),
        ("tags", tags),
        ("task", mem.get("task_slug")),
        ("edges", edges),
    ]
    return render_file(pairs, mem.get("content"))


# --- tree assembly -----------------------------------------------------------


def _refuse_slugless(rows: list[dict[str, Any]], kind: str) -> None:
    missing = [r for r in rows if not (r.get("slug") or "").strip()]
    if missing:
        raise ExportError(
            f"{len(missing)} {kind} row(s) have no stable slug — run the "
            f"state-git-stable-ids migration first (a slug-less {kind} cannot be "
            "exported: an ephemeral slug would diverge between machines). "
            f"Offending {kind} id(s): {sorted(r['id'] for r in missing)[:10]}"
        )


def build_tree(svc: ProjectService) -> tuple[dict[str, str], list[str]]:
    """Build ({relative-path: content}, warnings). Pure + read-only on the DB.

    Entities are slug-sorted so the file set and iteration order are stable;
    every multi-valued field is deterministically ordered by the renderers.
    """
    q = svc.be._q
    warnings: list[str] = []

    epics = q("SELECT id, slug, title, status, description FROM epics")
    stories = q("SELECT id, slug, title, status, description, epic_id FROM stories")
    tasks = q(
        "SELECT id, slug, title, status, stack, complexity, role, tier, goal, plan, "
        "acceptance_criteria, scope, scope_exclude, rollback_plan, scope_paths, "
        "scope_tools, relevant_files, defect_of, call_budget, completed_at, story_id "
        "FROM tasks"
    )
    task_logs = q("SELECT task_slug, message, phase, created_at, id FROM task_logs")
    decisions = q("SELECT id, slug, decision, task_slug, rationale, created_at FROM decisions")
    memory = q(
        "SELECT id, slug, type, title, content, tags, task_slug "
        "FROM memory WHERE archived_at IS NULL"
    )
    edges = q(
        "SELECT source_type, source_id, target_type, target_id, relation "
        "FROM memory_edges WHERE valid_to IS NULL"
    )

    # Negative AC-5: refuse (never silently skip / mint ephemeral) before writing.
    _refuse_slugless(decisions, "decision")
    _refuse_slugless(memory, "memory")

    epic_by_id = {e["id"]: e["slug"] for e in epics}
    story_by_id = {s["id"]: (s["slug"], epic_by_id.get(s["epic_id"])) for s in stories}
    id_to_slug: dict[tuple[str, int], str] = {}
    id_to_slug.update({("memory", m["id"]): m["slug"] for m in memory})
    id_to_slug.update({("decision", d["id"]): d["slug"] for d in decisions})

    logs_by_task: dict[str, list[dict[str, Any]]] = {}
    for row in task_logs:
        logs_by_task.setdefault(row["task_slug"], []).append(row)
    # Tiebreak on CONTENT (message, phase), never the machine-local autoincrement
    # id: two logs sharing a created_at must order identically on every machine
    # (AC-6), and genuinely-identical lines sort adjacently either way.
    for rows in logs_by_task.values():
        rows.sort(
            key=lambda r: (
                normalize_ts(r.get("created_at")) or "",
                flatten_line(r.get("message")),
                (r.get("phase") or ""),
            )
        )

    tree: dict[str, str] = {}
    for e in sorted(epics, key=lambda r: r["slug"]):
        tree[f"epics/{e['slug']}.md"] = _epic_doc(e)
    for s in sorted(stories, key=lambda r: r["slug"]):
        tree[f"stories/{s['slug']}.md"] = _story_doc(s, epic_by_id.get(s["epic_id"]))
    for t in sorted(tasks, key=lambda r: r["slug"]):
        story_slug, epic_slug = story_by_id.get(t["story_id"], (None, None))
        t = {**t, "_journal": logs_by_task.get(t["slug"], [])}
        tree[f"tasks/{t['slug']}.md"] = _task_doc(t, story_slug, epic_slug)
    for d in sorted(decisions, key=lambda r: r["slug"]):
        edge_rows = _edge_rows(
            edges, "decision", d["id"], id_to_slug, warnings, f"decision/{d['slug']}"
        )
        tree[f"decisions/{d['slug']}.md"] = _decision_doc(d, edge_rows)
    for m in sorted(memory, key=lambda r: r["slug"]):
        edge_rows = _edge_rows(
            edges, "memory", m["id"], id_to_slug, warnings, f"memory/{m['slug']}"
        )
        tree[f"memory/{m['slug']}.md"] = _memory_doc(m, edge_rows)

    # Reproducible diagnostics: the edges query has no ORDER BY, so sort the
    # dangling-edge warnings by content (not SQLite row order) before returning.
    warnings.sort()
    return tree, warnings


def export_one(svc: ProjectService, kind: str, slug: str) -> tuple[str, str] | None:
    """Render ONE entity's file, byte-identical to build_tree's, or None if absent.

    The incremental counterpart to build_tree: `state-git-triggers` re-serializes
    just the entity that changed (task done / decide / memory add) instead of the
    whole tree. Reuses the same renderers so a single-entity write is provably the
    same bytes build_tree would produce — only the context (story/epic, journal,
    edge targets) is fetched narrowly for this one entity. Archived memory returns
    None (excluded from the projection, same as build_tree)."""
    q = svc.be._q
    if kind == "epics":
        rows = q("SELECT id, slug, title, status, description FROM epics WHERE slug=?", (slug,))
        return (f"epics/{slug}.md", _epic_doc(rows[0])) if rows else None
    if kind == "stories":
        rows = q(
            "SELECT id, slug, title, status, description, epic_id FROM stories WHERE slug=?",
            (slug,),
        )
        if not rows:
            return None
        er = q("SELECT slug FROM epics WHERE id=?", (rows[0]["epic_id"],))
        return f"stories/{slug}.md", _story_doc(rows[0], er[0]["slug"] if er else None)
    if kind == "tasks":
        rows = q(
            "SELECT id, slug, title, status, stack, complexity, role, tier, goal, plan, "
            "acceptance_criteria, scope, scope_exclude, rollback_plan, scope_paths, "
            "scope_tools, relevant_files, defect_of, call_budget, completed_at, story_id "
            "FROM tasks WHERE slug=?",
            (slug,),
        )
        if not rows:
            return None
        t = dict(rows[0])
        story_slug = epic_slug = None
        if t["story_id"]:
            sr = q("SELECT slug, epic_id FROM stories WHERE id=?", (t["story_id"],))
            if sr:
                story_slug = sr[0]["slug"]
                er = q("SELECT slug FROM epics WHERE id=?", (sr[0]["epic_id"],))
                epic_slug = er[0]["slug"] if er else None
        logs = q(
            "SELECT task_slug, message, phase, created_at, id FROM task_logs WHERE task_slug=?",
            (slug,),
        )
        logs.sort(
            key=lambda r: (
                normalize_ts(r.get("created_at")) or "",
                flatten_line(r.get("message")),
                (r.get("phase") or ""),
            )
        )
        t["_journal"] = logs
        return f"tasks/{slug}.md", _task_doc(t, story_slug, epic_slug)
    if kind in ("decisions", "memory"):
        return _export_one_knowledge(q, kind, slug)
    return None


def _export_one_knowledge(q, kind: str, slug: str) -> tuple[str, str] | None:
    """Single-entity render for a decision/memory (with its outgoing edges)."""
    if kind == "decisions":
        rows = q(
            "SELECT id, slug, decision, task_slug, rationale, created_at FROM decisions WHERE slug=?",
            (slug,),
        )
        src_type = "decision"
    else:
        rows = q(
            "SELECT id, slug, type, title, content, tags, task_slug, archived_at "
            "FROM memory WHERE slug=?",
            (slug,),
        )
        src_type = "memory"
    if not rows or (kind == "memory" and rows[0].get("archived_at")):
        return None
    row = rows[0]
    edges = q(
        "SELECT source_type, source_id, target_type, target_id, relation FROM memory_edges "
        "WHERE source_type=? AND source_id=? AND valid_to IS NULL",
        (src_type, row["id"]),
    )
    id_to_slug: dict[tuple[str, int], str] = {}
    for e in edges:
        # `build_tree` resolves edge targets against the LIVE projection only
        # (`memory ... WHERE archived_at IS NULL`), so an edge to an archived
        # entry is dropped there. Looking the target up without that filter made
        # this renderer keep the edge — the two disagreed on the same entity's
        # bytes, which is exactly what "byte-identical to build_tree" forbids.
        if e["target_type"] == "memory":
            tr = q("SELECT slug FROM memory WHERE id=? AND archived_at IS NULL", (e["target_id"],))
        else:
            tr = q("SELECT slug FROM decisions WHERE id=?", (e["target_id"],))
        if tr:
            id_to_slug[(e["target_type"], e["target_id"])] = tr[0]["slug"]
    rows_edges = _edge_rows(edges, src_type, row["id"], id_to_slug, [], f"{src_type}/{slug}")
    if kind == "decisions":
        return f"decisions/{slug}.md", _decision_doc(row, rows_edges)
    return f"memory/{slug}.md", _memory_doc(row, rows_edges)


__all__ = ["ExportError", "build_tree", "export_one"]
