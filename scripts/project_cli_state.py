"""TAUSIK CLI handler for `tausik state export` (state-git-export, Decision #172).

`tausik state export` serializes durable project state (tasks, task_logs, epics,
stories, decisions, memory, memory_edges) from `.tausik/tausik.db` to a
git-native `tausik/` markdown tree — one file per entity, byte-stable across
machines and re-runs. `--check` fails (exit 1) on a stale tree, the same CI
contract as `tausik renar export --check` / `doc constants --check`.

The DB is the working cache; the `tausik/` tree is the canonical, branch-coupled
source of truth once state-git-roundtrip-gate lands. This command is read-only
on the DB and only ever writes under the (project-root-confined) target dir.
"""

from __future__ import annotations

import os
from typing import Any

from project_service import ProjectService


def _resolve_out_dir(explicit: str | None) -> str:
    """Resolve + safety-check the export target dir (default <root>/tausik/).

    An explicit --out is accepted only if it stays strictly inside the project
    root (assert_export_target) — the write path reconciles *.md deletions and
    must never escape the repo.
    """
    from project_config import find_tausik_dir
    from state_serialize import assert_export_target

    project_root = os.path.dirname(find_tausik_dir())
    target = (
        explicit.strip()
        if (explicit and explicit.strip())
        else os.path.join(project_root, "tausik")
    )
    return assert_export_target(target, project_root)


def cmd_state(svc: ProjectService, args: Any) -> None:
    cmd = getattr(args, "state_cmd", None)
    if cmd == "export":
        _cmd_state_export(svc, args)
        return
    if cmd == "import":
        _cmd_state_import(svc, args)
        return
    print(f"Unknown state subcommand: {cmd!r} (try `tausik state export|import`)")
    raise SystemExit(1)


def cmd_sync(svc: ProjectService, args: Any) -> None:
    """Top-level `tausik sync` — alias for `tausik state import`."""
    _cmd_state_import(svc, args)


def _cmd_state_import(svc: ProjectService, args: Any) -> None:
    """`tausik state import [--out tausik/] [--dry-run]` — git-native tree → DB cache."""
    from state_import import import_tree
    from state_parse import ParseError

    out = _resolve_out_dir(getattr(args, "out", None))
    if not os.path.isdir(out):
        print(f"state import: no tree at {out} (run `tausik state export` first)")
        raise SystemExit(1)
    dry = getattr(args, "dry_run", False)
    try:
        report = import_tree(svc, out, dry=dry)
    except ParseError as e:
        # Negative AC-6: a malformed file aborts the whole batch, no partial DB.
        print(f"state import refused (no changes written): {e}")
        raise SystemExit(1) from e

    for kind in ("added", "updated", "journal", "edges", "skipped_edges"):
        for item in report.get(kind, []):
            print(f"  {kind}: {item}")
    added, updated = len(report.get("added", [])), len(report.get("updated", []))
    jn, ed = len(report.get("journal", [])), len(report.get("edges", []))
    verb = "Would apply" if dry else "Applied"
    print(f"{verb}: {added} added, {updated} updated, {jn} journal, {ed} edges from {out}")
    if updated and not dry:
        print("  note: files won over local DB rows (git is the source of truth).")


def _cmd_state_export(svc: ProjectService, args: Any) -> None:
    """`tausik state export [--out tausik/] [--check]` — sqlite → git-native tree."""
    from state_export import ENTITY_DIRS, ExportError, build_tree
    from state_serialize import check_tree, write_tree

    managed = set(ENTITY_DIRS)

    try:
        out = _resolve_out_dir(getattr(args, "out", None))
    except ValueError as e:
        print(f"state export: {e}")
        raise SystemExit(1) from e

    try:
        tree, warnings = build_tree(svc)
    except ExportError as e:
        # Negative AC-5: a slug-less entity refuses loudly, never a silent skip.
        print(f"state export refused: {e}")
        raise SystemExit(1) from e

    for w in warnings:
        print(f"  warn: {w}")

    if getattr(args, "check", False):
        drift = check_tree(out, tree, managed_dirs=managed)
        if drift:
            print(f"Drift: {out} does not match live DB state ({len(drift)} issue(s)):")
            for msg in drift:
                print(f"  {msg}")
            print("  Run: tausik state export")
            raise SystemExit(1)
        print(f"OK — {out} matches live DB state ({len(tree)} file(s)).")
        return

    try:
        counts = write_tree(out, tree, managed_dirs=managed)
    except OSError as e:
        print(f"state export failed: {e}")
        raise SystemExit(1) from e

    # Deletions are never silent: name every reconciled removal (contract §
    # "Удаление сущности — удаление файла", but a human must still see it happen).
    for rel in counts["deleted_paths"]:
        print(f"  removed stale: {rel}")
    print(
        f"Exported {counts['written']} file(s) to {out}"
        + (f" (removed {counts['deleted']} stale)" if counts["deleted"] else "")
    )


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
