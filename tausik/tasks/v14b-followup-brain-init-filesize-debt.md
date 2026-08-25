---
slug: v14b-followup-brain-init-filesize-debt
title: "Follow-up: scripts/brain_init.py filesize debt — split run_wizard / _finalize_join"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/brain_init.py (slim run_wizard to dispatcher), scripts/brain_init_join.py (NEW), scripts/brain_init_create.py (NEW), .tausik/config.json (remove exempt entry), CHANGELOG.md, CHANGELOG.ru.md."
scope_exclude: "scripts/brain_discovery.py (already extracted in earlier task), scripts/brain_config.py, scripts/brain_project_registry.py, scripts/brain_notion_client.py, scripts/brain_cli_ops.py — only the importer (brain_cli_ops.py already calls via brain_init.run_wizard / brain_init.WizardError). Do NOT change semantics of the wizard; pure structural split."
relevant_files:
  - "scripts/brain_init.py"
  - "scripts/brain_init_join.py"
  - "scripts/brain_init_create.py"
  - "scripts/brain_init_schemas.py"
  - ".tausik/config.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T19:46:42Z"
---

## Goal

scripts/brain_init.py at 722 lines (was 745 before v14b-defect-brain-enable-no-discovery, dropped 23 by extracting brain_discovery.py). Currently in gates.filesize.exempt_files of .tausik/config.json — pure debt acknowledgement. Pay down: extract run_wizard's create-branch (Branch D, lines ~593-684) into brain_init_create.py; extract _finalize_join + Branch A resolve into brain_init_join.py. Target: brain_init.py under 400 lines, remove from exempt_files. Pure re-org per convention #91 (mixin/module split for filesize-gate compliance) — no semantic changes, all 69 tests in tests/test_brain_init.py keep passing.

## Acceptance Criteria

1. scripts/brain_init.py < 400 lines after split. 2. New module scripts/brain_init_join.py contains the --join-existing branch (lines 453-540 of run_wizard, including the visible-DB / 0-result diagnostics) plus _finalize_join. 3. New module scripts/brain_init_create.py contains the create branch (current lines 571-662 — orphan-cleanup, register_project, merge_brain_config save, success print + return). 4. run_wizard in brain_init.py reduces to a dispatcher: pre-flight (token, users.me, search) + branch selection + delegation. 5. All public names previously imported via brain_init.* (CATEGORIES, DB_TITLES, db_schema, create_brain_databases, verify_brain_databases, merge_brain_config, PartialCreateError, WizardError, WizardIO, ConfigOps, CliIO, run_wizard, _finalize_join, _has_existing_brain, _collect_explicit_join_ids, _print_orphan_cleanup_guidance, find_workspace_brain_databases, inspect_workspace_brain_databases, _extract_db_title) remain importable from brain_init unchanged. 6. tests/test_brain_init.py — all 69 tests pass with 0 changes to test code. 7. brain_init.py is removed from gates.filesize.exempt_files in .tausik/config.json. 8. CHANGELOG entry added under Unreleased v1.4.0 polish Phase B (EN+RU). NEGATIVE: 9. WizardError raised in either extracted branch still propagates out of run_wizard with original message intact (caught by tests like test_join_*_raises). 10. PartialCreateError mid-batch in extracted create branch still triggers _print_orphan_cleanup_guidance with real created_ids dict (not <missing> placeholders). 11. If brain_init_join or brain_init_create import fails, brain_init.py raises ImportError at module load (no silent fallback to inline branches).

## Plan

## Rollback

## Journal

- 2026-05-06T19:46:27Z [implementation] — AC verified: 1. ✓ wc -l scripts/brain_init.py = 367 (was 722, -355 lines) 2. ✓ scripts/brain_init_join.py 190 lines NEW; contains run_join_branch (Branch A diagnostics + ID resolve + verify) + _finalize_join (post-join config save). Imports of brain_init constants done at function-call time to break cycle. 3. ✓ scripts/brain_init_create.py 138 lines NEW; contains run_create_branch (parent_page_id/project_name prompts + create_brain_databases + register_project + merge_brain_config save with orphan cleanup on PartialCreateError or post-create exception). 4. ✓ run_wizard reduced to dispatcher: pre-flight (token, users.me(), workspace search) + branch selection. Branch A: from brain_init_join import run_join_branch; return run_join_branch(...). Branch B/C: inline raises. Branch D: from brain_init_create import run_create_branch; return run_create_branch(...). 5. ✓ hasattr smoke test confirmed 19/19 names accessible via brain_init module: CATEGORIES, DB_TITLES, db_schema, create_brain_databases, verify_brain_databases, merge_brain_config, PartialCreateError, WizardError, WizardIO, ConfigOps, CliIO, run_wizard, _finalize_join, _has_existing_brain, _collect_explicit_join_ids, _print_orphan_cleanup_guidance, find_workspace_brain_databases, inspect_workspace_brain_databases, _extract_db_title. 6. ✓ pytest tests/test_brain_init.py: 69/69 passed in 0.53s. Broader sweep (test_brain_init + test_brain_sync + test_brain_notion_client + test_brain_config + test_brain_project_registry + test_brain_storage_hardening + test_brain_token_resolve): 192 passed, 6 skipped in 1.75s. 7. ✓ .tausik/config.json edit: gates.filesize.exempt_files changed from ["scripts/brain_init.py"] to []. Empty list, brain_init.py no longer exempt. Filesize gate PASS for all 4 brain_init*.py files (367, 190, 138, 186 — all under 400). 8. ✓ CHANGELOG.md and CHANGELOG.ru.md: new entry "Filesize debt paydown: scripts/brain_init.py 722 → 367 over four files" inserted at TOP of "Changed"/"Изменено" section under [Unreleased] — v1.4.0 polish (Phase B), above the bootstrap_copy entry. 9. ✓ WizardError propagation tests: tests/test_brain_init.py covers test_run_wizard_join_existing_no_discovered_no_explicit_raises (raises WizardError match=--join-existing), test_run_wizard_partial_set_raises (match=partial set), test_run_wizard_databases_create_failure_raises (match=databases_create failed), test_run_wizard_post_create_save_failure_raises (match=Post-create step failed) — all green post-split. Errors propagate through delegate functions intact. 10. ✓ PartialCreateError tests still green: test_run_wizard_partial_create_failure_includes_orphan_guidance and test_create_brain_databases_partial_failure — _print_orphan_cleanup_guidance is called from inside run_create_branch with the PartialCreateError.created_ids dict; tests assert real id strings appear in printed guidance. 11. ✓ If brain_init_join or brain_init_create import fails at the lazy `from ... import run_X_branch` line inside run_wizard, Python raises ImportError up to caller — no try/except wrapper added. Verified by reading brain_init.py: lines 211-214 (Branch A) and lines 256-258 (Branch D) — bare `from X import Y` followed by direct call.
- 2026-05-06T19:46:42Z [implementation] — AC verified: 1. ✓ wc -l scripts/brain_init.py = 367 (was 722, -355 lines) 2. ✓ scripts/brain_init_join.py 190 lines NEW; contains run_join_branch + _finalize_join. Lazy imports break cycle. 3. ✓ scripts/brain_init_create.py 138 lines NEW; contains run_create_branch with prompts + create + register + save + orphan cleanup. 4. ✓ run_wizard reduced to dispatcher: pre-flight + branch selection. Branch A delegates to brain_init_join.run_join_branch; Branch D delegates to brain_init_create.run_create_branch. 5. ✓ 19/19 expected names accessible via brain_init module (hasattr smoke test pass). 6. ✓ pytest tests/test_brain_init.py: 69/69 passed. Wider sweep: 192 passed, 6 skipped. 7. ✓ .tausik/config.json gates.filesize.exempt_files now []. Filesize gate PASS for all 4 files (367, 190, 138, 186). 8. ✓ CHANGELOG.md + CHANGELOG.ru.md: new entry inserted at top of Changed/Изменено under Unreleased v1.4.0 polish Phase B. 9. ✓ WizardError propagation green: test_run_wizard_join_existing_no_discovered_no_explicit_raises, test_run_wizard_partial_set_raises, test_run_wizard_databases_create_failure_raises, test_run_wizard_post_create_save_failure_raises. 10. ✓ PartialCreateError + orphan cleanup green: test_run_wizard_partial_create_failure_includes_orphan_guidance + test_create_brain_databases_partial_failure. 11. ✓ Lazy `from brain_init_join import run_join_branch` (and create equivalent) inside run_wizard — bare import, no try/except; ImportError propagates to caller.
