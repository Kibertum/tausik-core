---
slug: review-mlow-polish-batch
title: "[A5+A6+B4+B5+C-L3+A2+A3 LOW/MED] Polish batch"
status: done
epic: senar-verify-redesign
story: review-findings-mlow-fix
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_verification.py, scripts/project_cli_verify.py, scripts/brain_init.py, tests/test_brain_init.py, tests/test_brain_notion_client.py, tests/test_service_verification.py"
scope_exclude: "scripts/service_gates.py, scripts/brain_project_registry.py"
relevant_files:
  - "scripts/service_verification.py"
  - "scripts/project_cli_verify.py"
  - "scripts/brain_init.py"
  - "tests/test_brain_init.py"
  - "tests/test_brain_notion_client.py"
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:34:57Z"
---

## Goal

7 LOW/MED findings: A5 type append_notes_fn как Callable[[str,str],None]|None (was Any). A6 CLI verify cache HIT теперь пишет в events table для telemetry. B4 create_brain_databases per-category try/except → партиальный create surface'ит созданные ids в orphan guidance. B5 EOF message wording — branch на exception type ("Aborted" vs "No input available"). C-L3 caplog test добавляет assert len(caplog.records)>=1 чтобы поймать silent pass. A2 + A3 — документация limitations (race wasteful but safe, mtime resolution Linux/Mac caveat).

## Acceptance Criteria

1. A5: append_notes_fn в run_gates_with_cache типизирован Callable[[str, str], None] | None (был Any)
2. A6: cmd_verify на cache HIT пишет в events table action='verify_cache_hit' для telemetry
3. B4: create_brain_databases per-category try/except — surfaces partial ids в exception attribute (created_ids: dict)
4. B4: WizardError на partial create включает orphan-cleanup guidance с реально-созданными ids (не <missing>)
5. B5: brain_init.CliIO.prompt — branch по exception type ("Aborted (Ctrl+C)" vs "No input available (stdin closed)") вместо общего "Aborted by user"
6. C-L3: test_token_not_in_retry_log добавляет assert len(caplog.records) >= 1 (поймать silent pass на empty caplog)
7. A2 docstring: run_gates_with_cache добавляет note про race "concurrent task_done безопасен под WAL, но может дублировать записи и работу — accepted"
8. A3 docstring: compute_files_hash добавляет note про mtime resolution на FAT/exFAT/HFS+ (2-сек/1-сек) — false cache hits possible на быстрых правках на таких FS
9. Регрессия: existing tests все зелёные
10. Ошибка/граничный случай: A6 — events.event_add фейлит → не блокировать verify, log warning
11. Новые тесты: test_create_databases_partial_orphan_in_guidance + test_eof_vs_keyboard_message_branches
12. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:30:26Z [implementation] — AC verified: ✓1 A5 append_notes_fn типизирован Callable[[str,str],None]|None ✓2 A6 cmd_verify cache HIT пишет event_add('task', slug, 'verify_cache_hit', details) с try/except (best-effort, log warning не block) ✓3 B4 PartialCreateError(NotionError) с created_ids attribute, raised если ids уже не пуст; первый fail → plain NotionError ✓4 run_wizard catch PartialCreateError → _print_orphan_cleanup_guidance с реальными ids → WizardError "partially failed" ✓5 B5 prompt() branches: KeyboardInterrupt → "Aborted by user (Ctrl+C)", EOFError → "Aborted: no input available (stdin closed/piped)" ✓6 C-L3 test_token_not_in_retry_log assert len(caplog.records)>=1 первым — поймать silent pass на empty caplog ✓7 A2 docstring concurrency note: "WAL safe but duplicate rows accepted; BEGIN IMMEDIATE worse" ✓8 A3 docstring mtime caveat: NTFS 100ns / ext4 1us / HFS+ 1s / FAT 2s ✓9 регрессия pytest 150/150 (3 файла) ✓10 try/except event_add (log warning) ✓11 +4 теста: test_partial_create_surfaces_created_ids, test_first_category_failure_raises_plain_notion_error, test_run_wizard_partial_create_prints_real_orphan_ids, test_eof_and_ctrl_c_messages_distinct ✓12 ruff clean
