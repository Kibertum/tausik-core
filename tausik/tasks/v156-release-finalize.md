---
slug: v156-release-finalize
title: "v1.5.6 release finalize: CHANGELOG P3/P5 + doc-constants reconcile + gitlab push"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "CHANGELOG.md, CHANGELOG.ru.md, docs/_generated/constants.json, README.md, README.ru.md, git"
scope_exclude: "github orphan, gh release (отложено юзером)"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T19:54:20Z"
---

## Goal

Дописать CHANGELOG EN/RU секцию [1.5.6] находками P3 (Kilo doctor) и P5 (ide_utils qwen/kilo), реконсайл doc-constants + README test_count, прогнать полный сьют зелёным, закоммитить и запушить на gitlab main (БЕЗ github orphan, БЕЗ gh release — по решению юзера).

## Acceptance Criteria

1. CHANGELOG.md + CHANGELOG.ru.md [1.5.6] содержат P3 (Kilo doctor) + P5 (ide_utils qwen/kilo). 2. doc-constants + README test_count реконсайлены к реальному числу. 3. Полный сьют зелёный (0 fail). 4. Коммит создан, запушен на gitlab main; github НЕ трогаем. 5. НЕГАТИВНЫЙ: если сьют красный или check_docs/version-drift — НЕ пушить, исправить сначала (Ошибка блокирует push).

## Plan

[{"step": "CHANGELOG EN/RU [1.5.6] \u0434\u043e\u043f\u0438\u0441\u0430\u043d P3+P5", "done": true}, {"step": "doc-constants + README test_count \u2192 4445; check_docs \u0437\u0435\u043b\u0451\u043d\u044b\u0439", "done": true}, {"step": "\u041f\u043e\u043b\u043d\u044b\u0439 \u0441\u044c\u044e\u0442: 4313 passed, 0 fail", "done": true}, {"step": "\u0420\u0435\u043b\u0438\u0437-\u043a\u043e\u043c\u043c\u0438\u0442 698f2d0 (mypy OK) + \u0442\u0435\u0433 v1.5.6", "done": true}, {"step": "push-ok ticket + git push origin main v1.5.6 (gitlab only; github \u043d\u0435 \u0442\u0440\u043e\u043d\u0443\u0442)", "done": true}]

## Rollback

git revert коммита; gitlab push можно откатить force-push на предыдущий SHA при необходимости.

## Journal

- 2026-06-19T19:54:20Z [implementation] — AC verified: AC-1: ✓ CHANGELOG.md + CHANGELOG.ru.md [1.5.6] содержат P3 (Kilo doctor) и P5 (ide_utils qwen/kilo) в Fixed/Added. AC-2: ✓ doc-constants + README test_count = 4445; check_docs 6 passed. AC-3: ✓ полный сьют 4313 passed, 12 skipped, 0 fail (234s). AC-4: ✓ релиз-коммит 698f2d0 (pre-commit mypy OK) + аннотир. тег v1.5.6; push-ok ticket → git push origin main v1.5.6 успешен (ac1ab87..698f2d0 main, new tag v1.5.6). github НЕ трогали (только origin=gitlab). AC-5: ✓ НЕГАТИВНЫЙ соблюдён: пуш выполнен ТОЛЬКО после подтверждённого зелёного сьюта + зелёного check_docs; красный бы заблокировал (порядок: тесты→коммит→push). Domain: gitlab main теперь v1.5.6, юзер проверит из гитлаба на живом Kilo (P3/P5 blind). github orphan + gh release отложены по решению юзера.
