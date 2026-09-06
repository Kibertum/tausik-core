---
slug: xargs-executes-its-arguments
title: "xargs исполняет свои аргументы: премиса из передачи #209 не проверена"
status: planning
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ПРЕМИСА ИЗ ПЕРЕДАЧИ #209, не проверена замером ни в #209, ни в #210.
Утверждение: xargs исполняет переданные ему аргументы, и разбор целей записи это не учитывает. Если верно — это тот же класс, что уже закрытая command-prefix-hides-shell-wrapper (префикс env/sudo/nohup/timeout прячет обёртку оболочки) и заведённая nested-wrapper-non-shell-interpreters: команда, ПРЯЧУЩАЯ другую команду от парсера, обходит охрану записи, не ломая её видимым образом.
ПЕРВЫЙ ШАГ — ЗАМЕР, А НЕ РАССУЖДЕНИЕ: составить строку, где xargs исполняет запись в файл, и показать РАЗНИЦУ между тем, что парсер объявляет целью записи, и тем, что реально появилось на диске. Без этой разницы задача останется мнением о том, как устроен xargs.
СВЯЗЬ С БЛОКИРОВАННОЙ ЗАДАЧЕЙ: write-gate-reads-prose-arguments-as-redirections стоит blocked и ждёт выбора владельца из трёх вариантов с цифрами. Если выбор изменит устройство парсера, ЭТУ задачу оценивать ПОСЛЕ него, а не до — иначе оценка будет сделана к парсеру, которого не станет.
ВНЕ ОБЪЁМА 1.9: относится к контуру охраны записи, чей ключевой вопрос сейчас у владельца.

## Acceptance Criteria

## Plan

## Rollback

## Journal
