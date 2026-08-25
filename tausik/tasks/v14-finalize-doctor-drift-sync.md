---
slug: v14-finalize-doctor-drift-sync
title: "Согласовать doctor CLAUDE.md drift detection с update-claudemd --dry-run"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "scripts/project_cli_doctor.py — только detail string в _print_warn для CLAUDE.md drift"
scope_exclude: "scripts/project_cli_extra.py (update-claudemd логика), bootstrap_templates.py, tests/ (новые тесты не нужны — существующие покрывают)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T21:49:35Z"
---

## Goal

tausik doctor показывает «CLAUDE.md drift — 14 static section(s) differ», но tausik update-claudemd --dry-run отвечает «is up-to-date. No drift». Два механизма используют разную логику сравнения. Найти расхождение в scripts/project_cli_doctor.py vs scripts/project_cli.py update-claudemd, привести к единой проверке. False positive в doctor либо ложный negative в update-claudemd — определить и пофиксить корректный из них.

## Acceptance Criteria

1. doctor remediation message больше не указывает на `tausik update-claudemd --dry-run` (misleading — оно не чинит static drift, только dynamic).
2. Новое сообщение явно говорит «static section(s) differ from bootstrap template — likely project customisation; re-bootstrap to reset».
3. test_claudemd_drift.py продолжает проходить (логика _check_claudemd_drift не меняется).
4. Negative: если drift=0 — поведение не меняется, _print_ok как и был.
5. Запустить tausik doctor — увидеть новое сообщение, вместо старого misleading.
6. Negative: pytest на test_claudemd_drift.py + test_doctor_*.py зелёный.
relevant_files: scripts/project_cli_doctor.py

## Plan

## Rollback

## Journal

- 2026-05-02T21:49:31Z [implementation] — AC verified: 1. ✓ doctor remediation message обновлён в scripts/project_cli_doctor.py:185-191 — больше не указывает на 'tausik update-claudemd --dry-run' как remediation. 2. ✓ Новый текст: 'static section(s) differ from bootstrap template (likely project customisation; re-run bootstrap to reset). tausik update-claudemd only refreshes the DYNAMIC block'. 3. ✓ tests/test_claudemd_drift.py 5/5 passed (логика _check_claudemd_drift не тронута). 4. ✓ Negative drift=0 path не тронут — _print_ok как и был. 5. ✓ tausik doctor показывает новое сообщение (deployed copy синхронизирована с source). 6. ✓ pytest test_claudemd_drift.py зелёный. relevant_files: scripts/project_cli_doctor.py
