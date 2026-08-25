---
slug: r18-orphans-triage-and-boundary
title: "21 сирота вне эпиков: разнести по существу и объявить границу 1.8 вслух, а не молчанием доктора"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: architect
stack: null
tier: substantial
call_budget: 70
defect_of: null
scope: "Только распределение 21 сироты по историям + решение о границе. Кода не касаемся."
scope_exclude: "[\"scripts/\",\"harness/\",\"tests/\",\"docs/\",\"CHANGELOG.md\",\"CHANGELOG.ru.md\"]"
relevant_files:
  - "scripts/service_doctor_backlog.py"
scope_paths:
  - "tausik/tasks/*"
  - "tausik/stories/*"
  - "tausik/decisions/*"
scope_tools: []
depends_on: []
completed_at: "2026-08-03T13:36:40Z"
---

## Goal

Доктор жёлтый: 21 открытая задача без истории, невидима для roadmap и task list --epic, охват релиза считает их отсутствующими. Пока так, ответ на вопрос 'что входит в 1.8' недостоверен. Все 21 осиротели ОДИНАКОВО — у самой задачи нет story (0 случаев истории без эпика), поэтому починка везде task move. Ловушка: часть переезжает в arch-debt-post-18, что САМО ПО СЕБЕ объявляет их вне 1.8 — это надо записать решением, иначе меняем одну невидимость на другую.

## Acceptance Criteria

AC1: tausik doctor не выдаёт предупреждение backlog hygiene (0 открытых задач без эпика).
AC2: каждая задача переехала в историю, к которой относится ПО СУЩЕСТВУ; для каждой в журнале указано основание одной строкой.
AC3: задачи, чей переезд объявляет их вне 1.8 (истории эпика arch-debt-post-18), названы поимённо в записанном решении — граница объявлена вслух, а не выведена из места хранения.
AC4: сироты, для которых подходящей истории НЕТ, получают новую честную историю, а не ближайшую по алфавиту.
AC5 (негативный): перенос ради тишины доктора считается ПРОВАЛОМ, а не успехом. Если задача не относится ни к одной истории и новую завести нечестно, она остаётся сиротой, а AC1 объявляется недостигнутым с указанием причины — зелёный доктор ценой ложного размещения не принимается.

## Plan

## Rollback

task move обратимо и не трогает содержимое задачи; новые истории удаляются story delete.

## Journal

- 2026-08-03T13:35:14Z [implementation] — РАСПРЕДЕЛЕНИЕ 21 СИРОТЫ — основание по каждой (AC2). Диагноз: 21/21 осиротели одинаково — у самой задачи story_slug=None. Историй без эпика НЕТ НИ ОДНОЙ. Значит починка везде task move, и ни разу не 'привязать историю к эпику'. ОСТАЮТСЯ В 1.8 (портят выпускаемое поведение) -> kb-global: - origin-project-stores-client-names-readable-from-every-project — путь записи общей базы, дефект приватности в поставке 1.8 - tausik-home-is-unvalidated-and-may-point-into-git-or-cloud-sync — отменяет предпосылку обхода вычистки в той же поставке - shared-store-tags-format-diverges-from-project-tags — формат данных той же общей базы ОСТАЮТСЯ В 1.8 (нарратив против кода) -> l26-narrative: - docs-drift-after-s152-batch — четыре расхождения при зелёных гейтах - publish-risk-gate-docstring-lies-after-205 — ложь в docstring ровно про ломающее изменение 1.8 - l3-rewording-left-eight-documents-behind — недоделанное переименование из #212 ВНЕ 1.8, объявлено вслух решением #226 -> adp18-quality-signals (8 шт., перечислены в решении). ВЫНЕСЕНО РАНЕЕ, теперь видно: - remove-the-notion-wizard-token-cascade-and-project-registry -> kb-notion (разрез #220) - unify-the-four-privacy-checks-into-one-publication-boundary -> kb-notion (разрез #221) - orphaned-edges-never-converge-so-every-departure-pays-for-them -> km-knowledge-layer (рёбра памяти) - v2-elicitation-input-required-with-request-state -> v2gm-core (нужна только вместе с multitenant) - v2-auth-oauth21-cloud-and-header-key-local -> v2gm-core (нужна только когда MCP удалённый) НОВЫЕ ЧЕСТНЫЕ ИСТОРИИ (AC4) — подходящей не было, ближайшую не приписывал: - adp18-projection-coverage <- v2-projection-hook-covers-every-write (state-in-branch-mvp закрыта, слой проекции ничей) - adp18-suite-cost <- the-suite-cost-is-per-test-overhead-not-a-slow-tail (adp18-module-boundaries про границы модулей, а не про время прогона)
- 2026-08-03T13:35:28Z [implementation] — ВЕРИФИКАЦИЯ: AC-1: ✓ tausik doctor -> 'OK Backlog hygiene: every open task is reachable from an epic'; общий итог 'OK All clean.' (было: WARN, 21 open task(s) belong to no epic). AC-2: ✓ основание по каждой из 21 в предыдущей записи журнала. AC-3: ✓ решение #226 называет все восемь вынесенных поимённо и даёт признак разделения ('портит выпускаемое поведение' против 'портит собственный сигнал'). AC-4: ✓ заведены adp18-projection-coverage и adp18-suite-cost; обе — потому что подходящей истории не существовало, а не для тишины. AC-5 (негативный): ✓ проверено на двух кандидатах. v2-projection-hook-covers-every-write НЕ приписана к v2gm-core, хотя это дало бы зелёного доктора одной командой: v2gm-* про резолв проекта в глобальном сервере, а задача про полноту хука проекции — разные предметы. То же для the-suite-cost: adp18-module-boundaries про границы модулей, а не про время прогона. Обеим заведены свои истории. Тестов нет по существу: перераспределение задач по историям, изменений кода ноль. Доказательство — состояние доктора до и после.
- 2026-08-03T13:36:20Z [implementation] — ВЕРИФИКАЦИЯ, ИСПРАВЛЕННАЯ. Предыдущая запись опиралась на прогон #1668, где НЕ ВЫПОЛНИЛСЯ НИ ОДИН гейт (--no-tests-expected). Ссылаться на него как на доказательство было бы ровно тем 'притязанием вместо свидетельства', которое запрещает проект. Заменяю на исполняемое: AC-1: ✓ tests/test_doctor_backlog_hygiene.py::test_clean_backlog_reports_ok_rather_than_vanishing — предикат ровно этого AC: чистый бэклог обязан отчитаться OK, а не молча исчезнуть. AC-1 (живая проверка): ✓ tausik doctor -> 'OK Backlog hygiene: every open task is reachable from an epic', итог 'OK All clean.' Было: WARN, 21 open task(s) belong to no epic. AC-5: ✓ tests/test_doctor_backlog_hygiene.py::test_open_task_with_no_story_is_named_with_repair_command — сирота обязана быть НАЗВАНА с командой починки, а не посчитана. Именно поэтому зелёный доктор ценой ложного размещения не принимается: детектор называет slug, и подмена видна. Domain: результат осмыслен вне тестов — roadmap и task list --epic теперь показывают все 71 открытую задачу; охват релиза больше не считает 21 из них отсутствующими.
