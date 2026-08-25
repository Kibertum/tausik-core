---
slug: port-external-pr5-hook-coverage
title: "Перенести внешний PR #5 (покрытие хуков) в основной репозиторий: часть уже сделана в 1.8, часть нет"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: complex
role: backend
stack: null
tier: substantial
call_budget: 90
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/hooks/*.py"
  - "bootstrap/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Каждое утверждение PR #5 проверено против дерева 1.8 и либо перенесено с тестом, либо закрыто как уже сделанное — с указанием, ЧЕМ именно.

## Acceptance Criteria

1. Составлена таблица «утверждение PR #5 -> состояние в 1.8»: что уже закрыто (PowerShell в матчерах, NotebookEdit в task_gate и scope_write_gate, shell_channel, mcp<2 в requirements) и что НЕТ.
2. Перенесено то, что нет: якорение матчеров ^(?:...)$, покрытие MCP-редакторов (serena, windows-mcp), MultiEdit в auto_format, NotebookEdit в memory_posttool_audit, единый источник имён инструментов в _common, поле пути в payload у каждого инструмента (file_path / notebook_path / path / relative_path / destination).
3. Каждая перенесённая правка приходит СО СВОИМ тестом, который на старом коде краснеет.
4. Автор PR #5 указан соавтором в коммите; PR закрыт ссылкой на перенос, а не молча.
5. НЕГАТИВНЫЙ сценарий: тест доказывает, что запись через инструмент, не попадавший в матчер, теперь БЛОКИРУЕТСЯ без активной задачи. Утверждение «хук отработал» не принимается за доказательство: хук, не увидевший вызова, тоже выходит с нулём, и отличить это можно только по факту блокировки.
6. НЕГАТИВНЫЙ сценарий: якорение матчеров не должно ОТКЛЮЧИТЬ ни один работающий сегодня перехват — до и после правки собирается список (инструмент, хук), и он только растёт.

## Plan

## Rollback

git revert коммита; ветка порта отдельная, в main вливается одним куском

## Journal

- 2026-08-25T15:35:26Z [planning] — AC1 ВЫПОЛНЕН В СЕССИИ #179, перенесён сюда из хэндоффа #179 без повторного разбора. Сверка велась по дереву 1.8, не по памяти. PR #5 (Okianiwa, 25 июля) предъявлял шесть охранников; ЧЕТЫРЕ ИЗ ШЕСТИ УЖЕ ЗАКРЫТЫ В 1.8. ТАБЛИЦА «утверждение PR #5 -> состояние в 1.8» (второй столбец — матчер из PR, третий — матчер сегодня в bootstrap/bootstrap_hooks.py): - task_gate: PR «Write|Edit» -> сегодня «Write|Edit|MultiEdit|NotebookEdit» -> ЗАКРЫТО - scope_write_gate: PR «Write|Edit|MultiEdit» -> сегодня «+NotebookEdit» -> ЗАКРЫТО - bash_firewall: PR «Bash» -> сегодня «Bash|PowerShell» через SHELL_MATCHER -> ЗАКРЫТО - git_push_gate: PR «Bash» -> сегодня «Bash|PowerShell» -> ЗАКРЫТО - secret_scan: PR «Write|Edit|MultiEdit» -> сегодня «+Bash|PowerShell», НО БЕЗ NotebookEdit -> ОТКРЫТО - memory_pretool_block: то же -> то же, БЕЗ NotebookEdit -> ОТКРЫТО Дополнительно закрыто в 1.8: mcp<2.0.0 запинен в requirements; shell_channel существует. ВТОРОЙ СЛОЙ (набор имён ВНУТРИ хука) сходится с матчером у scope_write_gate, но у двух оставшихся NotebookEdit выпал В ОБОИХ СЛОЯХ СРАЗУ: secret_scan.py:132 и _PATH_TOOLS в scripts/hooks/memory_pretool_block.py:62. Следствие фактическое: правка ноутбука сегодня не проходит НИ через секрет-сканер, НИ через маршрутизацию памяти. ОТКРЫТО, шесть пунктов (это и есть область AC2): 1. Якорения матчеров ^(?:...)$ нет нигде. Механизм в НАШЕМ дереве живой, а не гипотетический: матчер mcp__tausik-project__tausik_task_done (bootstrap/bootstrap_hooks.py:237) содержит дефисы, то есть по разбору PR уже сегодня исполняется неякоренным RegExp, а не сравнением на равенство. Практический вред сегодня нулевой (только пере-совпадение), но канал открыт. 2. MCP-редакторы serena и windows-mcp не покрыты ни одним хуком. 3. NotebookEdit выпал у secret_scan, memory_pretool_block._PATH_TOOLS и memory_posttool_audit._AUDITED_TOOLS. 4. auto_format сидит на матчере Write|Edit — без MultiEdit. 5. Единого источника имён инструментов НЕТ: четыре литеральных набора в четырёх хуках — _GATED_TOOLS, _PATH_TOOLS, _AUDITED_TOOLS и встроенный кортеж в secret_scan. Тот же класс «две копии одного правила», который релиз чинит на уровне каталогов. 6. task_gate читает из payload только file_path и notebook_path; path, relative_path, destination не читает. РАЗМЕР PR И ЕГО ФОРМА: GitHub отдаёт первые 100 файлов — 10222 добавленных строки, из них 8353 (81%) приходятся на подсистему autoloop, 39 файлов, к заявленной находке отношения не имеющую. Полный размер PR — 19399 строк. Находка внутри настоящая и ценная, но принять PR целиком означало бы принять несвязанную фичу под видом починки хуков. Отсюда форма переноса: берём находку, не берём autoloop; авторство сохраняем (конвенция #382, AC4). ПРОИСХОЖДЕНИЕ ЭТОЙ ЗАПИСИ: разбор сделан в #179, старт задачи тогда отказал гейт ёмкости (budget=90 exceeds remaining -1723/200), поэтому журнал остался пуст, а таблица уехала в хэндофф сессии. Восстановлена в #181. Побочная находка: хэндофф ЛЮБОЙ сессии, кроме последней, не читается ни CLI, ни MCP — session last-handoff отдаёт только свежайший, session show нет вовсе. Таблицу пришлось доставать из транскрипта IDE, то есть из-за пределов фреймворка.
