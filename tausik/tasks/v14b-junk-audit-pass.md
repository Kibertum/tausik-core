---
slug: v14b-junk-audit-pass
title: "B-junk: Realistic cleanup — bilingual docs, research dump, db backups, vendor deps"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: ".gitignore, scripts/project_cli_ops.py (or new scripts/db_prune.py), scripts/project_parser.py, tests/test_db_prune.py"
scope_exclude: ".claude/, .cursor/, .qwen/, scripts/service_*.py, scripts/backend_*.py"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T22:21:03Z"
---

## Goal

Что НЕ ловят существующие audit'ы (которые сейчас все clean): (1) bilingual EN+RU дубликаты — оценить 86 файлов, выделить translate-only updates как стоимость, предложить policy "doc-changes single-language acceptable"; (2) docs/ru/research/ накопленные retrospectives + master plans — выделить устаревшие по контексту v1.3, переместить в _archive; (3) .tausik/tausik.db.bak.v14..v22 backup'ы → политика auto-archive после N дней или git-ignore; (4) vendor/ external skill repos (seo, ui-ux-pro-max, polyakov, etc.) — оценить реальное использование через usage_events, удалить unused. Цель: меньше когнитивной нагрузки + быстрее find/grep в repo.

## Acceptance Criteria

SCOPED to AC #3 (db backup pruning). Original AC #1 (translation drift), #2 (research archive), #4 (vendor usage) spin off as separate Phase B tasks. 1. `.tausik/tausik.db.bak.*` added to .gitignore so future backups are not committed. 2. New CLI command `tausik db prune --keep N` deletes oldest .tausik/tausik.db.bak.* files keeping only the N most recent (default N=3). 3. NEGATIVE: --keep 0 removes ALL backups. 4. NEGATIVE: --keep larger than the number of backups is a no-op (no error). 5. NEGATIVE: when no backups exist the command prints a single-line message and exits 0. 6. Listing existing backups shows the kept set and the deleted set so users see what changed. 7. Three follow-up tasks created: v14b-junk-translation-drift-audit, v14b-junk-research-archive, v14b-junk-vendor-usage-audit. 8. tests/test_db_prune.py covers happy-path + 3 negatives. 9. pytest tests/test_db_prune.py PASS. 10. tausik verify --task &lt;slug&gt; PASS.

## Plan

## Rollback

## Journal

- 2026-05-03T22:21:03Z [implementation] — AC verified: 1.✓ .gitignore already covers .tausik/*.bak.* (verified pattern match against existing tausik.db.bak.v14..v22). 2.✓ tausik db prune --keep N implemented in scripts/cmd_db.py (list_backups + prune_backups + cmd_db dispatcher) wired into project_parser.py + project.py dispatch. 3.✓ keep=0 removes all backups — test_keep_zero_removes_all. 4.✓ keep larger than count is no-op — test_keep_larger_than_count_is_noop. 5.✓ Empty backup set → 'No tausik.db.bak.* files found' single-line message — test_prune_no_backups_message. 6.✓ Kept + deleted sets disjoint, both printed via cmd_db — test_kept_set_and_deleted_set_are_disjoint + test_prune_prints_kept_and_deleted. 7.✓ 3 follow-ups created: v14b-junk-translation-drift-audit, v14b-junk-research-archive, v14b-junk-vendor-usage-audit. 8.✓ pytest tests/test_db_prune.py 13/13 PASS in 0.12s. 9.✓ Negative coverage: nonexistent dir, negative keep clamp, unknown subcommand SystemExit, no backups present. 10.✓ tausik verify exit=0.
