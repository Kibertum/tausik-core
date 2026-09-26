---
slug: doctor-warns-forever-about-a-deliberate-verify-profile
title: "doctor предупреждает вечно о профиле Verify-First, который выбран осознанно — предупреждение, которое нельзя погасить, обесценивает все остальные"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: null
role: architect
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_cli_doctor.py"
  - "tests/test_doctor_auto_verify_hint.py"
scope_paths:
  - "scripts/project_cli_doctor.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T06:13:20Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР (сессия #184): `tausik doctor` на этом проекте всегда заканчивается «WARN OK with 1 warning(s)» из-за строки Verify-First profile: task_done.auto_verify=true — heavy gates inline on `task done` (legacy). Предупреждение выдаётся КАЖДЫЙ прогон и не может быть погашено иначе, как изменением профиля.

ПОЧЕМУ ПРОФИЛЬ НЕ НАДО ПРОСТО ПЕРЕКЛЮЧАТЬ. auto_verify=true означает, что тяжёлые гейты прогоняются ВСТРОЕННО на task done. Выключение снимает этот страховочный прогон, то есть ОСЛАБЛЯЕТ энфорсмент. Мы и так работаем по схеме verify -> handle -> task done, но auto_verify остаётся вторым поясом. Менять настройку ради тишины в doctor значит разменивать проверку на опрятность отчёта — размен неверный, и он прямо противоречит fail-closed философии SENAR.

ЧТО НА САМОМ ДЕЛЕ ДЕФЕКТ. Сам doctor это признаёт в тексте: «CI may keep auto_verify for single-step pipelines». То есть значение легитимно, а предупреждение всё равно горит. Предупреждение, которое НЕЛЬЗЯ погасить правильным действием, обучает читателя игнорировать предупреждения — и следующее, настоящее, будет пропущено ровно поэтому. Это тот же класс, что и «результат проверки, который ничего не различает»: сигнал, не несущий решения.

ЧТО РЕШИТЬ: либо doctor перестаёт предупреждать, когда профиль выбран ЯВНО (признак осознанного выбора в конфиге, а не совпадение значения по умолчанию), либо предупреждение понижается до информационной строки, либо профиль объявляется устаревшим по-настоящему и тогда меняется вместе с миграцией. Выбор за владельцем; менять энфорсмент молча нельзя.

НЕ ДЕЛАТЬ: не выключать task_done.auto_verify ради зелёного doctor.

## Acceptance Criteria

1. With task_done.auto_verify=true AND a non-empty task_done._auto_verify_reason (the '_<key>_reason' convention tausik/policy.json already uses), doctor prints an OK line naming the choice and its reason instead of a WARN; the doctor summary stops counting it as a warning. 2. NEGATIVE: auto_verify=true WITHOUT a reason still warns exactly as before (an unexplained legacy profile stays visible); a blank or whitespace reason counts as none. 3. NEGATIVE: the enforcement is untouched — auto_verify is not switched off, and the CI suppression stays as it was. 4. docs/*/doctor.md say how to acknowledge the profile.

## Plan

## Rollback

git revert; doctor returns to warning on every auto_verify=true

## Journal

- 2026-09-24T06:12:55Z [implementation] — Root cause: doctor's only test was the value of auto_verify; the default is off, so 'true' is always somebody's explicit choice and 'explicit' could not tell a deliberate profile from a forgotten one — only a written reason can.
- 2026-09-24T06:12:56Z [implementation] — AC-1: ✓ tests/test_doctor_auto_verify_hint.py::test_a_recorded_reason_turns_the_warning_into_a_report — with _auto_verify_reason doctor prints 'OK Verify-First profile task_done.auto_verify=true, chosen: <reason>' and does not count a warning (auto_verify_acknowledged_reason in project_cli_doctor.py).
- 2026-09-24T06:12:56Z [implementation] — AC-2: ✓ tests/test_doctor_auto_verify_hint.py::test_a_recorded_reason_turns_the_warning_into_a_report — negative: absent and whitespace-only reasons keep the WARN, which now names task_done._auto_verify_reason as the way to acknowledge it.
- 2026-09-24T06:12:56Z [implementation] — AC-3: ✓ tests/test_doctor_auto_verify_hint.py::test_doctor_suppresses_warning_in_ci — negative: CI suppression unchanged; nothing reads _auto_verify_reason except doctor, so enforcement (gate_verify_first auto_verify route) is untouched; 128 doctor tests pass.
- 2026-09-24T06:12:57Z [implementation] — AC-4: ✓ review — docs/en/doctor.md and docs/ru/doctor.md name the acknowledgement key with an example; CHANGELOG EN/RU.
