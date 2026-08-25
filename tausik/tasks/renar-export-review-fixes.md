---
slug: renar-export-review-fixes
title: "Adversarial-review fixes for renar export (--out guard, path sep, prune, error handling)"
status: done
epic: renar-adoption
story: renar-substrate-and-reach-1
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: renar-file-export
scope: "scripts/renar_export.py, scripts/project_cli_renar.py, tests/test_renar_export.py. Bootstrap after."
scope_exclude: "Do NOT change svc.be._conn usage (established codebase pattern — renar_conformance CLI already uses it). Do NOT alter export file format beyond adding adapt timestamps. Do NOT touch conformance/drift logic."
relevant_files:
  - "scripts/renar_export.py"
  - "scripts/project_cli_renar.py"
  - "tests/test_renar_export.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T11:13:27Z"
---

## Goal

Fix valid findings from the separate-model (Sonnet) adversarial review of renar-file-export: (CRITICAL) add --out containment guard so write_tree cannot delete *.md outside the project root; (HIGH) normalize separators in the deletion path; (HIGH) fix _prune_empty_dirs nested-dir orphan + TOCTOU; (MED) adapt frontmatter timestamps for symmetry, robust test key extraction, empty-DB test; (LOW) drop dead SPEC_TYPES import, error-handle the CLI command, context-manage test file reads.

## Acceptance Criteria

AC-1: `tausik renar export --out <path>` refuses (SystemExit 1, no deletion) when path is outside the project root or is a filesystem root — tested via tests/test_renar_export.py. AC-2 (negative): the guard rejects `--out /` and an outside-root dir without touching any file. AC-3: deletion path uses os.sep-normalized paths (consistent with the write path). AC-4: _prune_empty_dirs removes nested empty dirs bottom-up (no orphan parents) and swallows OSError (TOCTOU/ENOTEMPTY) — tested. AC-5: adapt frontmatter carries created_at/updated_at (symmetry with spec); --check stays clean across re-runs. AC-6: empty-DB build_tree yields exactly README.md + conformance.md and round-trips clean — tested. AC-7: dead SPEC_TYPES import removed; _cmd_renar_export wraps OSError → friendly SystemExit(1); ruff+mypy clean, files <400 lines. All prior 13 tests still pass.

## Plan

## Rollback

git revert; changes are localized to scripts/renar_export.py + scripts/project_cli_renar.py + tests/test_renar_export.py. No schema/data change.

## Journal

- 2026-06-14T11:12:38Z [implementation] — Fixed adversarial-review findings: CRITICAL --out containment via assert_export_target (pure/testable, strictly-inside-root, rejects / and outside dirs); HIGH deletion-path os.sep normalization; HIGH _prune_empty_dirs removed sorted() (bottom-up correctness) + try/except OSError (TOCTOU); MED adapt frontmatter created_at/updated_at symmetry, robust regex key-extraction in test, empty-DB test; LOW dropped dead SPEC_TYPES import, _cmd_renar_export wraps ValueError/OSError→SystemExit(1), test context managers. 19 export tests (+6) + 46 renar-suite green; ruff+mypy clean; all <400. CLI guard smoke: --out outside root → exit 1, no write. Tree regenerated, --check clean. HIGH#2 (_conn) intentionally NOT changed — established pattern (renar_conformance CLI uses svc.be._conn).
- 2026-06-14T11:12:57Z [implementation] — Root cause — Category: missing-safety-guard + cross-platform-inconsistency. Description: the original renar-file-export shipped write_tree with deletion reconciliation but no containment check on --out, and a few path/prune asymmetries, because the Phase-0 scope focused on the happy-path export+determinism and the destructive deletion path was not threat-modeled for a hostile --out value. Prevention: adversarial separate-model review (SENAR Rule 4) now runs on new destructive primitives BEFORE close; assert_export_target added as a reusable guard; tests cover the negative (reject + no-delete) path so a regression is caught by CI.
- 2026-06-14T11:13:08Z [implementation] — AC verified: 1. ✓ --out guard rejects outside-root + root-itself — tests/test_renar_export.py::test_out_guard_rejects_outside_root, ::test_out_guard_rejects_root_itself; CLI smoke: --out /tmp/evil-renar → SystemExit 1, nothing written 2. ✓ Negative: rejected target never reaches deletion — tests/test_renar_export.py::test_out_guard_does_not_delete_on_reject (victim .md survives) 3. ✓ deletion path os.sep-normalized matching write path — scripts/renar_export.py write_tree (rel.replace('/', os.sep)) 4. ✓ nested empty dirs pruned bottom-up + OSError swallowed — tests/test_renar_export.py::test_prune_removes_nested_empty_dirs; _prune_empty_dirs dropped sorted(), try/except OSError 5. ✓ adapt frontmatter created_at/updated_at — tests/test_renar_export.py::test_adapt_body_rendered; tree regenerated, --check exit 0 6. ✓ empty-DB → README+conformance only, round-trips clean — tests/test_renar_export.py::test_empty_db_yields_only_base_files 7. ✓ dead SPEC_TYPES import removed; _cmd_renar_export wraps ValueError/OSError→SystemExit(1); ruff+mypy clean; files <400 (export 319, cli 169); 46 renar-suite tests green. Domain: guard genuinely prevents filesystem-wide .md deletion for a hostile --out, verified by real CLI exit code + surviving victim file.
- 2026-06-14T11:13:27Z [implementation] — AC verified: 1. ✓ --out guard rejects outside-root + root-itself — tests/test_renar_export.py::test_out_guard_rejects_outside_root, ::test_out_guard_rejects_root_itself; CLI smoke --out /tmp/evil-renar → SystemExit 1 2. ✓ Negative: rejected target never deletes — tests/test_renar_export.py::test_out_guard_does_not_delete_on_reject 3. ✓ deletion path os.sep-normalized — scripts/renar_export.py write_tree 4. ✓ nested prune bottom-up + OSError swallowed — tests/test_renar_export.py::test_prune_removes_nested_empty_dirs 5. ✓ adapt frontmatter created_at/updated_at — ::test_adapt_body_rendered; --check exit 0 after regen 6. ✓ empty-DB round-trips — ::test_empty_db_yields_only_base_files 7. ✓ dead import removed; CLI ValueError/OSError→SystemExit(1); ruff+mypy clean; <400 lines; 46 renar tests green
- 2026-06-14T11:14:22Z [done] — Root cause (missing-validation): renar export shipped a destructive deletion-reconciliation path without validating that the --out target stays strictly inside the project root, so a hostile/mistaken --out could delete *.md filesystem-wide. Prevention: assert_export_target guard + negative tests (reject + no-delete) added, and adversarial separate-model review now threat-models the hostile argument value for any new delete/overwrite primitive before close.
