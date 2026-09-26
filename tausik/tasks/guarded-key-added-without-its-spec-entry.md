---
slug: guarded-key-added-without-its-spec-entry
title: "Новый охраняемый ключ task_done.changelog_gate.enabled не описан в SPEC sec-config-trust-tiers — охрана полноты SPEC покраснела после пуша"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: changelog-gate-switch-is-outside-config-trust-guards
scope: null
scope_exclude: null
relevant_files:
  - "docs/ru/config-trust-tiers.md"
  - "docs/en/config-trust-tiers.md"
  - "tests/test_spec_completeness.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-04T22:11:34Z"
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО ПОЛНЫМ ПРОГОНОМ ЛЕНТЫ в #213 после закрытия и пуша changelog-gate-switch-is-outside-config-trust-guards (ca6ca34): tests/test_spec_completeness.py::test_the_live_repository_reports_exactly_the_gap_it_has красный — sec-config-trust-tiers выпал из complete: аудит полноты (enumerator config_trust_guarded_keys) нашёл OMISSION «the body never names 'task_done.changelog_gate.enabled'». Тело SPEC — docs/ru/config-trust-tiers.md (content_ref). Пайплайн GitLab 6779 зелёный, потому что аудит читает живую БД, которой в CI нет; локальный полный прогон обязателен перед пушем (память #559), а я прогнал только целевые файлы.

ЧТО СДЕЛАТЬ: дополнить docs/ru/config-trust-tiers.md описанием нового ключа рядом с остальными охраняемыми; тест снова зелёный; аудит по-прежнему называет ровно один настоящий разрыв (renar-adoption UNCHECKED).

Root cause (missing-validation): закрытие задачи по scoped verify без полного прогона; SPEC-полнота не входит в scoped-набор, потому что связь GUARDS → SPEC идёт через БД (content_ref), а не через импорт. Prevention: полный прогон перед каждым пушем, а не только в конце смены.

## Acceptance Criteria

AC-1: docs/ru/config-trust-tiers.md и docs/en/config-trust-tiers.md несут строку таблицы охраняемых ключей для task_done.changelog_gate.enabled с тем же смыслом, что note в GUARDS.
AC-2: tests/test_spec_completeness.py::test_the_live_repository_reports_exactly_the_gap_it_has зелёный: sec-config-trust-tiers снова complete, единственная находка — renar-adoption UNCHECKED.
AC-3 (negative): аудит полноты действительно читает тело — при временном удалении строки из docs/ru (не коммитить) находка OMISSION с именем ключа возвращается; проверено прогоном и записано в журнал.
AC-4: docs_lint/doc-drift зелёные на обоих файлах; полный прогон ленты перед пушем.

## Plan

## Rollback

git revert; только документация.

## Journal

- 2026-09-04T22:10:00Z [implementation] — Строка для task_done.changelog_gate.enabled добавлена в таблицы охраняемых ключей docs/ru/config-trust-tiers.md (тело SPEC по content_ref) и docs/en/config-trust-tiers.md. tests/test_spec_completeness.py — 27 passed. AC-3 negative прогоном: при временном удалении строки (в процессе, с восстановлением в finally) аудит даёт OMISSION sec-config-trust-tiers «the body never names 'task_done.changelog_gate.enabled'»; после восстановления complete = [sec-config-trust-tiers, team-state-in-git-format], единственная находка — renar-adoption UNCHECKED. Root cause (missing-validation): scoped verify не выбирает test_spec_completeness, потому что связь GUARDS → SPEC идёт через content_ref в БД, а не через импорт; полный прогон был отложен на конец смены. Prevention: полный прогон перед КАЖДЫМ пушем.
- 2026-09-04T22:11:06Z [implementation] — AC-1: ✓ docs/ru/config-trust-tiers.md и docs/en/config-trust-tiers.md — строка task_done.changelog_gate.enabled в таблицах охраняемых ключей. AC-2: ✓ tests/test_spec_completeness.py::test_the_live_repository_reports_exactly_the_gap_it_has (27 passed). AC-3 (negative): ✓ прогон с временно удалённой строкой — OMISSION sec-config-trust-tiers с именем ключа возвращается, после восстановления complete снова две SPEC (журнал). AC-4: ✓ scoped verify 12 файлов (doc-gate/doc-drift/check_docs) зелёный. Root cause (missing-validation): scoped verify не выбирает test_spec_completeness — связь GUARDS→SPEC через content_ref в БД. Prevention: полный прогон перед каждым пушем. Domain: SPEC-полнота (spec_completeness), документация трастовых тиров.
- 2026-09-04T22:11:30Z [implementation] — AC-1: ✓ docs/ru/config-trust-tiers.md и docs/en/config-trust-tiers.md — строка task_done.changelog_gate.enabled в таблицах охраняемых ключей. AC-2: ✓ tests/test_spec_completeness.py::test_the_live_repository_reports_exactly_the_gap_it_has (27 passed). AC-3 (negative): ✓ прогон с временно удалённой строкой — OMISSION sec-config-trust-tiers с именем ключа возвращается, после восстановления complete снова две SPEC (журнал). AC-4: ✓ scoped verify 12 файлов (doc-gate/doc-drift/check_docs) зелёный. Root cause (missing-validation): scoped verify не выбирает test_spec_completeness — связь GUARDS→SPEC через content_ref в БД. Prevention: полный прогон перед каждым пушем (память #592). Domain: SPEC-полнота (spec_completeness), документация трастовых тиров.
