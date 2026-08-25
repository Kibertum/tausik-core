---
slug: renar-file-export
title: "Phase 0: tausik renar export (sqlite → renar/ tree) + --check drift gate"
status: done
epic: renar-adoption
story: renar-substrate-and-reach-1
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/renar_export.py (new, pure builder), scripts/project_cli_renar.py (add export subcommand dispatch), scripts/project_parser.py (add `renar export` argparse), tests/test_renar_export.py (new). Bootstrap after editing scripts/*."
scope_exclude: "Do NOT touch: renar_conformance.py logic (reuse generate/gather_signals read-only), renar_drift.py, service_specs.py / service_adapts.py (read via existing show/list methods only), DB schema / migrations. Do NOT make the export write to the DB. Do NOT add the export-check to default gates in this task (Phase-0 scope is the command + --check; gate wiring is a follow-up)."
relevant_files:
  - "scripts/renar_export.py"
  - "scripts/project_cli_renar.py"
  - "scripts/project_parser.py"
  - "tests/test_renar_export.py"
  - "renar/README.md"
  - "renar/conformance.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T10:58:47Z"
---

## Goal

Add `tausik renar export [--out renar/] [--check]` that serializes specs + adapts (forward interpretations, backward findings, signatures, delta lineage) + the conformance manifest into a deterministic, git-trackable markdown+frontmatter tree under renar/. One-way (DB is source of truth, files are a derived view — never hand-edited). --check reports drift like `doc constants --check` so CI fails on a stale tree. Stable ordering = no spurious churn. This is the missing substrate surface (V3 diff&review / V4 branching) the user identified; we run no separate doc service.

## Acceptance Criteria

AC-1: `tausik renar export [--out renar/]` writes a deterministic markdown+frontmatter tree (specs/, adapts/, conformance + README) from live DB; re-running with no DB changes produces byte-identical files (no spurious churn) — tested via tests/test_renar_export.py. AC-2: ordering is stable (slug-sorted) and YAML frontmatter keys are stable-ordered — tested. AC-3: `tausik renar export --check` exits 0 when the tree matches the DB and exits 1 with a clear remediation message when a spec/adapt is added, edited, or removed (stale/missing/extra file) — tested. AC-4: the writer reconciles deletions (a removed spec/adapt drops its file) — tested. AC-5: export is one-way/read-only on the DB (never writes DB) and conformance view excludes volatile write-time date fields so --check is stable across days — tested.

## Plan

[{"step": "Write renar_export.py: pure build_tree(conn)->{relpath:content} for specs/, adapts/, conformance.md, README.md (deterministic, slug-sorted, stable frontmatter keys, no volatile dates)", "done": true}, {"step": "Add write_tree(root,tree) with deletion reconciliation + check_tree(root,tree)->drift messages", "done": true}, {"step": "Wire CLI: project_cli_renar.py export dispatch (--out, --check) + project_parser.py argparse subparser", "done": true}, {"step": "Write tests/test_renar_export.py: determinism, ordering, --check add/edit/remove, deletion reconcile, read-only DB", "done": true}, {"step": "Run bootstrap.py to sync .claude/, run pytest + ruff", "done": true}, {"step": "verify --task + task done --ac-verified", "done": true}]

## Rollback

git revert the commit; new module renar_export.py + CLI/parser additions are additive — deleting renar_export.py and reverting project_cli_renar.py/project_parser.py restores prior behavior. No DB migration, no schema change. The generated renar/ tree is a derived view; rm -rf renar/ is safe.

## Journal

- 2026-06-14T10:57:22Z [implementation] — Implemented renar_export.py (pure build_tree + write_tree w/ deletion reconcile + check_tree), wired `tausik renar export [--out] [--check]` in project_cli_renar.py + project_parser.py. 13 new tests (determinism, ordering, --check add/edit/remove, deletion reconcile, read-only, date-free conformance) all pass; 76 RENAR+adapts tests green; ruff+mypy clean; all files <400 lines (export 285). Bootstrap synced .claude/. Smoke via .tausik CLI: export writes tree, --check exit 0 clean / exit 1 on drift (verified real exit code).
- 2026-06-14T10:57:56Z [implementation] — AC verified: 1. ✓ deterministic byte-identical export — tested via tests/test_renar_export.py::test_build_is_deterministic + ::test_rewrite_is_byte_identical (re-run with unchanged DB byte-identical) 2. ✓ slug-sorted paths + sorted frontmatter keys — tests/test_renar_export.py::test_expected_paths_and_slug_order + ::test_frontmatter_keys_sorted 3. ✓ --check exits 0 clean / 1 on drift — tests/test_renar_export.py::test_check_missing_when_artifact_added, ::test_check_changed_when_artifact_edited, ::test_check_stale_when_extra_file, ::test_check_reports_missing_tree; CLI smoke real exit=1 on tamper, exit=0 clean 4. ✓ deletion reconcile drops removed artifact's file — tests/test_renar_export.py::test_delete_reconciles_file (deleted count==1, file gone, check clean) 5. ✓ read-only DB + date-free conformance view — tests/test_renar_export.py::test_build_does_not_mutate_db + ::test_conformance_is_date_free (no assessment-date/next-due/manifest-id)
- 2026-06-14T10:58:19Z [implementation] — AC verified: 1. ✓ deterministic byte-identical export — tests/test_renar_export.py::test_build_is_deterministic + ::test_rewrite_is_byte_identical 2. ✓ slug-sorted paths + sorted frontmatter keys — tests/test_renar_export.py::test_expected_paths_and_slug_order + ::test_frontmatter_keys_sorted 3. ✓ --check exits 0 clean / 1 on drift — tests/test_renar_export.py::test_check_missing_when_artifact_added, ::test_check_changed_when_artifact_edited, ::test_check_stale_when_extra_file, ::test_check_reports_missing_tree; CLI smoke real exit=1 4. ✓ deletion reconcile — tests/test_renar_export.py::test_delete_reconciles_file 5. ✓ read-only DB + date-free conformance — tests/test_renar_export.py::test_build_does_not_mutate_db + ::test_conformance_is_date_free
- 2026-06-14T10:58:46Z [implementation] — AC verified: 1. ✓ deterministic byte-identical export — tests/test_renar_export.py::test_build_is_deterministic + ::test_rewrite_is_byte_identical 2. ✓ slug-sorted paths + sorted frontmatter keys — tests/test_renar_export.py::test_expected_paths_and_slug_order + ::test_frontmatter_keys_sorted 3. ✓ --check exits 0 clean / 1 on drift — tests/test_renar_export.py 4 check tests; CLI smoke real exit=1 4. ✓ deletion reconcile — tests/test_renar_export.py::test_delete_reconciles_file 5. ✓ read-only DB + date-free conformance — tests/test_renar_export.py::test_build_does_not_mutate_db + ::test_conformance_is_date_free
