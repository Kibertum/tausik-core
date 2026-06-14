"""RENAR file export — one-way sqlite → ``renar/`` markdown tree (Phase 0).

Decision #109: sqlite is the single source of truth for RENAR artifacts; the
``renar/`` tree is a DERIVED, git-trackable view that gives the substrate its V3
(diff & review) and V4 (branching) surface without a separate doc service. The
tree is NEVER hand-edited — :func:`build_tree` regenerates it from the DB and
``tausik renar export --check`` fails CI on a stale tree (the same contract as
``doc constants --check``).

Determinism is the whole point: artifacts are slug-sorted, frontmatter keys are
emitted in stable (sorted) order, and the conformance view is date-free so a
re-run with an unchanged DB produces byte-identical files (no spurious churn).
The dated RENAR-CONFORMANCE.yaml manifest (write-time metadata) stays separate;
this view carries only the structural conformance state.

Read-only on the DB: the builder queries via ProjectService accessors and never
writes. Only :func:`write_tree` touches the filesystem (the ``renar/`` tree).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from renar_conformance import (
    RENAR_VERSION,
    SENAR_VERSION,
    _require_yaml,
    eval_mandatory_clauses,
    gather_signals,
    infer_level,
)

if TYPE_CHECKING:
    from project_service import ProjectService

# The export owns *.md under the tree; deletion reconciliation is scoped to this
# extension so pointing --out at a populated dir cannot nuke unrelated files.
MANAGED_SUFFIX = ".md"

_DERIVED_BANNER = "> Derived view — do not hand-edit. Regenerate: `tausik renar export`."


def _frontmatter(data: dict[str, Any]) -> str:
    """YAML frontmatter block with stable (sorted) key order."""
    yaml = _require_yaml()
    body = yaml.safe_dump(data, sort_keys=True, allow_unicode=True, default_flow_style=False)
    return f"---\n{body}---\n"


def _doc(front: dict[str, Any], body_lines: list[str]) -> str:
    """Assemble a frontmatter doc with a trailing newline (stable on disk)."""
    return _frontmatter(front) + "\n" + "\n".join(body_lines).rstrip("\n") + "\n"


# --- per-artifact renderers --------------------------------------------------


def _spec_doc(spec: dict[str, Any]) -> str:
    linked = sorted(t["slug"] for t in spec.get("linked_tasks", []))
    front = {
        "artifact": "spec",
        "slug": spec["slug"],
        "type": spec["type"],
        "status": spec["status"],
        "version": spec["version"],
        "content_ref": spec.get("content_ref"),
        "created_at": spec["created_at"],
        "updated_at": spec["updated_at"],
        "linked_tasks": linked,
    }
    body = [
        f"# SPEC-{spec['type']}: {spec['title']}",
        "",
        _DERIVED_BANNER,
        "",
        f"Status **{spec['status']}** · version **{spec['version']}**",
        "",
        f"Content ref: `{spec.get('content_ref') or '(none)'}`",
        "",
        f"Linked tasks: {', '.join(linked) if linked else '(none)'}",
    ]
    return _doc(front, body)


def _adapt_doc(adapt: dict[str, Any]) -> str:
    signatures = [
        {
            "role": s["role"],
            "signed_by": s.get("signed_by"),
            "signed_at": s.get("signed_at"),
            "fingerprint": s.get("fingerprint"),
            "signature": s.get("signature"),
        }
        for s in sorted(adapt.get("signatures", []), key=lambda s: s["role"])
    ]
    links = sorted(
        (
            {"target_type": link["target_type"], "target_slug": link["target_slug"]}
            for link in adapt.get("links", [])
        ),
        key=lambda link: (link["target_type"], link["target_slug"]),
    )
    front = {
        "artifact": "adapt",
        "slug": adapt["slug"],
        "title": adapt["title"],
        "tz_ref": adapt["tz_ref"],
        "status": adapt["status"],
        "parent_adapt": adapt.get("parent_adapt"),
        "delta_n": adapt.get("delta_n", 0),
        "created_at": adapt.get("created_at"),
        "updated_at": adapt.get("updated_at"),
        "signatures": signatures,
        "links": links,
    }
    body = [
        f"# ADAPT: {adapt['title']}",
        "",
        _DERIVED_BANNER,
        "",
        f"Source ТЗ: `{adapt['tz_ref']}` · status **{adapt['status']}** "
        f"· delta **{adapt.get('delta_n', 0)}**",
    ]
    interps = adapt.get("interpretations", [])
    if interps:
        body += ["", "## Forward interpretations"]
        for i in interps:
            body += _interp_lines(i)
    findings = adapt.get("findings", [])
    if findings:
        body += ["", "## Backward findings"]
        for f in findings:
            body += _finding_lines(f)
    return _doc(front, body)


def _interp_lines(i: dict[str, Any]) -> list[str]:
    lines = ["", f"### {i['tz_ref']} — {i['citation']}", "", i["engineering_interpretation"], ""]
    lines.append(f"- scope-in: {i['scope_in']}")
    lines.append(f"- scope-out: {i['scope_out']}")
    if i.get("term_mapping"):
        lines.append(f"- term-mapping: {i['term_mapping']}")
    if i.get("scenarios"):
        lines.append(f"- scenarios: {i['scenarios']}")
    return lines


def _finding_lines(f: dict[str, Any]) -> list[str]:
    ref = f.get("tz_ref") or "—"
    return [
        "",
        f"### [{f['category']}] ({ref})",
        "",
        f["description"],
        "",
        f"Resolution: {f.get('resolution') or '(open)'}",
    ]


def _conformance_doc(conn: Any) -> str:
    """Date-free conformance state (level + signals + clauses) for stable diffs.

    Deliberately OMITS gather_signals()'s raw-counts: those include operational
    counters (verification_runs, memory_edges, reasoning_tasks) that move on
    every `verify`/`memory add` — activity UNRELATED to RENAR artifacts — and
    would make the tree churn (and --check fail) mid-session. The level, signal
    booleans and clause confirmations are all RENAR-artifact-derived, so they
    only change when a SPEC/ADAPT actually changes — the property --check needs.
    """
    bundle = gather_signals(conn)
    clauses = eval_mandatory_clauses(bundle)
    verdict = infer_level(bundle, clauses)
    level = verdict["level"] or "(pre-adoption)"
    front = {
        "artifact": "conformance",
        "renar-version": RENAR_VERSION,
        "senar-version": SENAR_VERSION,
        "level": verdict["level"],
        "pre-adoption": verdict["pre_adoption"],
        "blocked-at": verdict["blocked_at"],
        "mandatory-clauses-confirmed": {n: c["confirmed"] for n, c in clauses.items()},
        "level-signals": {k: bool(v) for k, v in bundle["signals"].items()},
    }
    body = [
        "# RENAR Conformance (derived view)",
        "",
        _DERIVED_BANNER,
        "",
        f"Level: **{level}**",
        "",
        f"Blocked at: {verdict['blocked_at'] or '(nothing — top level)'} — {verdict['reason']}",
        "",
        "> The date-stamped manifest lives at RENAR-CONFORMANCE.yaml (write-time "
        "metadata). This view is date-free so `--check` is stable across days.",
    ]
    return _doc(front, body)


def _readme_doc() -> str:
    return (
        "# RENAR artifact tree — DERIVED VIEW (do not hand-edit)\n\n"
        "Generated by `tausik renar export` from `.tausik/tausik.db`, the single\n"
        "source of truth for RENAR artifacts (Decision #109). This tree is the\n"
        "substrate's V3 (diff & review) / V4 (branching) surface — git tracks it,\n"
        "but it is regenerated, never edited.\n\n"
        "- Regenerate: `tausik renar export`\n"
        "- Fail CI on a stale tree: `tausik renar export --check`\n\n"
        "Layout: `specs/<slug>.md`, `adapts/<slug>.md`, `conformance.md`.\n"
    )


# --- tree assembly -----------------------------------------------------------


def build_tree(svc: ProjectService) -> dict[str, str]:
    """Build {relative-path: file-content} for the whole ``renar/`` tree.

    Pure + read-only: queries the service accessors, never writes. Specs and
    adapts are slug-sorted so iteration order (and thus the file set) is stable.
    """
    tree: dict[str, str] = {
        "README.md": _readme_doc(),
        "conformance.md": _conformance_doc(svc.be._conn),
    }
    for spec in sorted(svc.spec_list(), key=lambda s: s["slug"]):
        full = svc.spec_show(spec["slug"])
        tree[f"specs/{spec['slug']}.md"] = _spec_doc(full)
    for adapt in sorted(svc.adapt_list(), key=lambda a: a["slug"]):
        full = svc.adapt_show(adapt["slug"])
        tree[f"adapts/{adapt['slug']}.md"] = _adapt_doc(full)
    return tree


# --- filesystem write + check ------------------------------------------------


def assert_export_target(out: str, project_root: str) -> str:
    """Refuse an export target that escapes ``project_root``; return its abspath.

    write_tree reconciles deletions (removes *.md not in the tree), so a stray
    ``--out`` (e.g. ``/`` or ``$HOME``) could delete unrelated markdown across
    the filesystem. The target must be a directory STRICTLY INSIDE the project
    root — never the root itself (would reconcile every *.md in the repo) and
    never an outside path. Pure + testable (no project-context dependency).
    """
    out_abs = os.path.abspath(out)
    root_abs = os.path.abspath(project_root)
    try:
        inside = os.path.commonpath([out_abs, root_abs]) == root_abs
    except ValueError:  # different drive on Windows → not inside
        inside = False
    if not inside or out_abs == root_abs:
        raise ValueError(
            f"refusing --out {out_abs!r}: the export target must be a directory "
            f"strictly inside the project root {root_abs!r} — write reconciles "
            "deletions of *.md and must never touch files elsewhere"
        )
    return out_abs


def _managed_on_disk(root: str) -> set[str]:
    """Relative paths of all managed (*.md) files currently under ``root``."""
    found: set[str] = set()
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(MANAGED_SUFFIX):
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                found.add(rel.replace(os.sep, "/"))
    return found


def write_tree(root: str, tree: dict[str, str]) -> dict[str, int]:
    """Write ``tree`` under ``root``, reconciling deletions.

    Managed (*.md) files on disk that are not in ``tree`` are removed (a deleted
    spec/adapt drops its file). Returns {written, deleted} counts.
    """
    deleted = 0
    for rel in sorted(_managed_on_disk(root) - set(tree)):
        os.remove(os.path.join(root, rel.replace("/", os.sep)))
        deleted += 1
    written = 0
    for rel in sorted(tree):
        path = os.path.join(root, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(tree[rel])
        written += 1
    _prune_empty_dirs(root)
    return {"written": written, "deleted": deleted}


def _prune_empty_dirs(root: str) -> None:
    """Remove now-empty subdirectories left after deletion reconciliation.

    ``topdown=False`` yields children before parents so a nested empty subtree
    prunes bottom-up in one pass (do NOT sort — that re-orders parents ahead of
    children and leaves orphans). rmdir is best-effort: a concurrent write
    (ENOTEMPTY) or permission error is swallowed, not propagated.
    """
    for dirpath, _dirs, _files in os.walk(root, topdown=False):
        if os.path.abspath(dirpath) == os.path.abspath(root):
            continue
        if not os.listdir(dirpath):
            try:
                os.rmdir(dirpath)
            except OSError:
                pass


def check_tree(root: str, tree: dict[str, str]) -> list[str]:
    """Return drift messages comparing the on-disk tree to ``tree`` ([] = clean)."""
    drift: list[str] = []
    if not os.path.isdir(root):
        return [f"missing tree: {root} does not exist (run `tausik renar export`)"]
    on_disk = _managed_on_disk(root)
    for rel in sorted(set(tree) - on_disk):
        drift.append(f"missing: {rel} (artifact in DB has no exported file)")
    for rel in sorted(on_disk - set(tree)):
        drift.append(f"stale: {rel} (no matching artifact in DB — should be removed)")
    for rel in sorted(set(tree) & on_disk):
        with open(os.path.join(root, rel.replace("/", os.sep)), encoding="utf-8") as fh:
            if fh.read() != tree[rel]:
                drift.append(f"changed: {rel} (exported file differs from DB state)")
    return drift
