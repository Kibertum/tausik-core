---
slug: r18-scope-boundary-shared-knowledge
title: "Граница объёма 1.8: по каждой из 15 planning-задач эпика shared-knowledge должно быть явное решение — вынос в 1.9 или включение"
status: done
epic: landscape-2026-h2
story: release-18-audit
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: "Только фиксация решений о границе объёма 1.8 по 15 planning-задачам эпика shared-knowledge. Кода не касаемся."
scope_exclude: "[\"scripts/\",\"harness/\",\"tests/\",\"CHANGELOG.md\",\"CHANGELOG.ru.md\"]"
relevant_files:
  - "tausik/decisions"
scope_paths:
  - "tausik/decisions/*"
  - "tausik/tasks/*"
scope_tools: []
depends_on: []
completed_at: "2026-08-03T13:32:34Z"
---

## Goal

Решение #217 сузило 1.8 до ядра и потребовало выносить надстройку ОТДЕЛЬНЫМИ РЕШЕНИЯМИ, а не молча. Сейчас 15 задач эпика shared-knowledge висят в planning без записанного решения. Пока так — ответ на вопрос 'что входит в 1.8' недостоверен.

## Acceptance Criteria

AC1: по каждой из 15 planning-задач эпика shared-knowledge зафиксирован явный исход — либо ссылка на существующее решение о выносе в 1.9, либо новое решение, либо явное заявление о включении в 1.8; молчаливого остатка ноль.
AC2: результат сведён в таблицу 'задача → исход → решение #N' и приложен к журналу задачи.
AC3: новые решения записаны через tausik decide и видны в tausik decisions list.
AC4 (негативный): если по задаче исход определить нельзя — она НЕ помечается вынесенной молча; вместо этого фиксируется ошибка 'исход не определён' с причиной, и задача остаётся в отчёте как незакрытый вопрос. Пустая или отсутствующая формулировка исхода считается провалом AC1, а не пропуском.

## Plan

## Rollback

Решения записываются через tausik decide (append-only журнал); откат — запись опровергающего решения. Изменений кода нет.

## Journal

- 2026-08-03T13:31:56Z [implementation] — ГРАНИЦА ОБЪЁМА — таблица исходов по 15 planning-задачам эпика shared-knowledge (AC2). Проверено: post-#217 решения, называющего ХОТЯ БЫ ОДНУ из 15, не существовало. Молчаливый остаток = 15/15. | задача | исход | решение | |---|---|---| | brainh-audit | DEFER 1.9 | #224 | | brainh-reliability | DEFER 1.9 (кандидат на закрытие: #220/#221 сняли предпосылку) | #224 | | brainh-semantic-search | DEFER 1.9 | #224 | | brainh-capture-ux | DEFER 1.9 | #224 | | l26-memory-decay | DEFER 1.9 | #224 | | kb-global-promote | DEFER 1.9 | #224 | | km-stable-identity-backfill | DEFER 1.9 | #224 | | km-topics-aliases-index | DEFER 1.9 | #224 | | km-retrieval-first-write-path | DEFER 1.9 | #224 | | km-memory-lint-report | DEFER 1.9 | #224 | | km-promote-mechanical-checks-blocking | DEFER 1.9 | #224 | | lanes-changelog-fragments | DEFER 1.9 | #224 | | kb-docs-map | РАЗРЕЗАНА: программа в 1.9 | #225 | | kb-docs-swarm | РАЗРЕЗАНА: программа в 1.9 | #225 | | kb-docs-consistency | РАЗРЕЗАНА: программа в 1.9, ложь 1.8 чинится в 1.8 | #225 | Разрез доков не догадка. Проверено вживую три места: docs/en/shared-brain.md:1 (Notion-backed заголовок, снято #222), там же Enforcement п.2 (классификатор, снят #221), docs/{en,ru}/mcp.md:279-284 (обещание зеркалирования decide, снято #221). Все doc-гейты ЗЕЛЁНЫЕ — считают только известные сущности, поэтому их молчание свидетельством не является. Заведена узкая задача r18-docs-falsified-by-breaking-changes. Ни одна из 12 вынесенных не блокирует тег: ядро общей базы закрыто, entry_uuid нативен в knowledge_db.py, замер #187 показал извлечение на потолке.
- 2026-08-03T13:32:29Z [implementation] — ВЕРИФИКАЦИЯ (AC3): AC-1: ✓ tausik decisions --limit 3 -> #224 (12 задач вынесены), #225 (цепочка доков разрезана). Молчаливый остаток 15 -> 0. AC-2: ✓ таблица 'задача -> исход -> решение #N' в предыдущей записи журнала, все 15 строк. AC-3: ✓ обе записи видны в tausik decisions, обе привязаны к task_slug=r18-scope-boundary-shared-knowledge. AC-4 (негативный): ✓ исход, который нельзя было определить механически (три kb-docs-*), НЕ помечен вынесенным молча — по нему проведена живая проверка трёх файлов и записано отдельное решение #225 с разрезом, а не общий DEFER. Тестов нет по существу: задача записывает решения в append-only журнал, кода не касается. Заявлено --no-tests-expected явно и записано в квитанцию #1666.
