---
slug: repo-coherence-sits-one-line-under-the-size-cap-an
title: "repo_coherence sits one line under the size cap and the next collector will not fit"
status: planning
epic: null
story: null
complexity: null
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

НАЙДЕНО В СМЕНЕ #239 при добавлении коллектора красной истории. scripts/repo_coherence.py = 499 строк при лимите 500 (гейт размера, решение #190). Следующий коллектор физически не помещается, а линза устроена ровно так, чтобы коллекторы добавлялись — это её единственный способ расти.

ШОВ ЕСТЬ И ОН НЕ ПРОИЗВОЛЬНЫЙ: модуль делает две разные вещи. Первая — ОПРЕДЕЛЯЕТ, что такое находка и как коллектор запускается безопасно (Finding, _safe, MAX_FINDINGS, SEVERITY_ORDER, NOT_EXAMINED). Вторая — ДЕРЖИТ ДЕСЯТЬ КОЛЛЕКТОРОВ и собирает их. Первая меняется почти никогда, вторая при каждом новом коллекторе. Тот же шов уже применялся дважды в этом релизе: gate_spec отделён от gate_registry, gate_shellless_exec от gate_command_runner.

НЕ ДЕЛАТЬ: не менять поведение линзы, не переименовывать вид находок, не трогать collectors_run — он теперь считается по фактически запущенным.

## Acceptance Criteria

AC-1. Модуль разрезан по шву «определение против данных»: форма находки и безопасный запуск в одном файле, коллекторы и сборка в другом. Оба под лимитом с запасом, названным числом.
AC-2. Публичная поверхность не меняется: repo_coherence.collect, render_markdown, render_json, Finding продолжают импортироваться теми же именами из того же места. Проверяется тестом на импорт, а не чтением.
AC-3. НЕГАТИВНЫЙ СЦЕНАРИЙ: вывод линзы на живом дереве ДО и ПОСЛЕ разреза совпадает побайтно. Разрез, меняющий отчёт, — это не разрез, а правка поведения под видом уборки.
AC-4. Гейт размера зелёный, и запас в новом файле коллекторов достаточен минимум для трёх новых коллекторов — иначе задача вернётся через месяц.

## Plan

## Rollback

## Journal
