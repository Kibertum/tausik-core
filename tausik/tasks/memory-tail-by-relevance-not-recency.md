---
slug: memory-tail-by-relevance-not-recency
title: "Хвост памяти в CLAUDE.md отбирается по свежести, а не по значимости"
status: blocked
epic: release-112-knowledge
story: release112-knowledge
complexity: complex
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#125"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Свежий агент на старте сессии видит то, что ему СЕЙЧАС нужно, а не то, что записали последним. Запись двухмесячной давности, на которую ссылались двадцать раз, обязана вытеснять вчерашнюю, которую не открыли ни разу.

## Acceptance Criteria

AC1. ПРОБЛЕМА НАЗВАНА ЧИСЛОМ, А НЕ ОЩУЩЕНИЕМ: показано, сколько записей корпуса конкурируют за пять строк хвоста на тип, и какая доля хвоста за последние N сессий состояла из записей, к которым больше ни разу не обратились.
AC2. У записи появляется СЛОЙ (у kaeru это core/hot/warm/cold/frozen). Слой меняется по накоплению — обращения, ссылки, возраст, — а не по расписанию и не вручную при каждой записи.
AC3. ПРОБНЫЙ ПРОГОН ОБЯЗАТЕЛЕН. Отдельная команда показывает, что следующий проход сделает и почему, НИЧЕГО не меняя. У kaeru это hygiene <initiative>, и рекомендация прямая: сначала прогнать на хранилище, которое дорого, и только потом включать.
AC4. ЛЮБОЕ ПЕРЕМЕЩЕНИЕ ОБРАТИМО ОДНОЙ КОМАНДОЙ и ничего не удаляет. Понижение слоя — не удаление; запись остаётся достижимой по прямому запросу.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: запись, помеченная как обязательная к показу, не понижается автоматически НИКОГДА. Иначе первая же гигиена уронит из хвоста то, ради чего он существует.
AC6. НЕГАТИВНЫЙ СЦЕНАРИЙ: при пустом корпусе и при корпусе из одной записи хвост не ломается и не даёт пустых заголовков. Тот же класс дефекта уже ловился в mcp-update-claudemd-erases-the-memory-tail.
AC7. Механизм включается ЯВНО и по умолчанию выключен, пока не набрано доказательство на нашем корпусе. У kaeru он тоже opt-in, и это осознанная осторожность, а не недоделка.

## Plan

## Rollback

git revert: отбор возвращается к последним N по типу; слои остаются в БД неиспользованными и не мешают

## Journal

- 2026-09-29T21:19:32Z [implementation] — Taken out of 1.10 (my own inclusion error, session #279): AC1 needs per-record access counts that do not exist (brain_events has no memory id), AC7 ships it off by default, and it does not shrink the tail — so it pays nothing to 1.10 token economy. Prerequisite: record memory hits per id. Back to deferred for 1.11.
