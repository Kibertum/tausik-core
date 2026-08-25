---
slug: v14-doctor-auto-verify-hint
title: "doctor: предупреждение при auto_verify в интерактивном профиле"
status: done
epic: v14-verify-integrity
story: v14-verify-doctor-signals
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_cli_doctor.py tests/test_doctor_auto_verify_hint.py"
scope_exclude: null
relevant_files:
  - "scripts/project_cli_doctor.py"
  - "tests/test_doctor_auto_verify_hint.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T10:14:38Z"
---

## Goal

Не failing по умолчанию; текст понятен.

## Acceptance Criteria

1. Логика в doctor. 2. Тест или snapshot сообщения. 3. Negative: проект без auto_verify не получает warning.

## Plan

## Rollback

## Journal

- 2026-05-01T10:14:35Z [implementation] — AC verified: 1. ✓ Doctor вызывает auto_verify_interactive_warning_detail после config knobs (project_cli_doctor.py). 2. ✓ AC-2: ✓ tested via tests/test_doctor_auto_verify_hint.py. 3. ✓ Negative: конфиг без auto_verify → сообщение=None в тестах и нет WARN внешней ветки.
