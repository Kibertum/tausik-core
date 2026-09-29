---
slug: preparation-before-verify-costs-two-calls-per-task
title: "Подготовка к проверке стоит два вызова на каждую задачу"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_prepare.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_verify.py"
  - "tests/test_verify_prepare.py"
  - "tausik/gates.json"
scope_paths:
  - "scripts/"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T17:16:42Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Перед verify агент обязан сделать два отдельных вызова, иначе гейты краснеют предсказуемо: ruff format (иначе ruff_format red) и python bootstrap/bootstrap.py --ide all после любой правки scripts/ (иначе bootstrap_drift red). Оба детерминированы и оба известны заранее. При 482 000 токенов префикса на вызов это около миллиона токенов на задачу, а задач порядка 400 в месяц. Цель: verify --prepare делает это в том же вызове, и КВИТАНЦИЯ записывает, что подготовка шла и что она изменила — иначе зелёный перестанет значить то, что значил.

## Acceptance Criteria

AC-1 tausik verify --task <slug> --prepare прогоняет ruff format и ре-bootstrap ДО гейтов и затем проверяет подготовленное дерево. ✓ tests/test_verify_prepare.py
AC-2 Квитанция и вывод НАЗЫВАЮТ, что подготовка шла и какие файлы она изменила; зелёный без этой строки означает то же, что раньше.
AC-3 НЕГАТИВНЫЙ: подготовка, завершившаяся ошибкой, ОСТАНАВЛИВАЕТ прогон с текстом ошибки, а не идёт к гейтам по неподготовленному дереву и не выдаёт зелёный.
AC-4 НЕГАТИВНЫЙ: без --prepare поведение не меняется ни в одном байте — флаг по умолчанию выключен, и тест это утверждает.
AC-5 НЕГАТИВНЫЙ: подготовка НЕ трогает ничего, кроме форматирования и развёртывания обвязки; тест требует, чтобы список команд подготовки был объявлен данными, а не собирался по ходу.
AC-6 Полная лента зелёная.

## Plan

## Rollback

git revert; verify без флага не тронут

## Journal

- 2026-09-29T17:16:38Z [implementation] — AC-1 ✓ verify --task <slug> --prepare прогоняет ruff format и ре-bootstrap до гейтов; проверено на себе — «PREPARED: ruff format — 4 files left unchanged», дальше зелёный прогон #3154. ✓ tests/test_verify_prepare.py. AC-2 ✓ каждый шаг печатается строкой PREPARED с его выводом; ::test_every_step_is_reported_by_name и ::test_a_silent_step_still_reports_itself — молчаливый шаг тоже отчитывается, иначе читается как пропущенный. AC-3 ✓ НЕГАТИВНЫЙ: упавший шаг даёт PreparationFailed со своим текстом и словами «NOT run», остановка на ПЕРВОМ отказе: ::test_a_failing_step_stops_the_run_and_carries_its_output. AC-4 ✓ НЕГАТИВНЫЙ: флаг по умолчанию выключен, и обработчик готовит только по просьбе; ::TestWithoutTheFlagNothingChanges, включая проверку, что подготовка стоит ДО run_verify_for_task. AC-5 ✓ НЕГАТИВНЫЙ: список шагов объявлен данными и закрыт — ::test_the_list_is_exactly_formatting_and_redeployment падает на третьем виде, ::test_the_steps_cannot_be_edited_through_the_returned_objects на попытке правки. AC-6 ✓ полная лента 12 441 passed, 34 skipped, 0 deselected. Domain: два вызова на задачу превратились в ноль; при 482 000 токенов префикса это около миллиона токенов на задачу. НАЙДЕНО И ИСПРАВЛЕНО В ХОДЕ РАБОТЫ: первая редакция гнала ruff format по всему дереву и на первом же настоящем прогоне переформатировала 90 файлов, включая намеренно нетронутые из ruff_format.legacy_unformatted — тупик #802. Шаг сужен до объявленной области и пропускается ВСЛУХ, когда области нет. Побочно: scripts/repo_coherence.py снят с legacy_unformatted (83 -> 82), храповик затянулся.
