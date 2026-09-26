---
slug: memory-search-crashes-on-two-word-queries
title: "memory search падает трейсбеком на половине запросов из двух слов"
status: planning
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
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

НАЙДЕНО СВОИМ ЖЕ ИСПОЛЬЗОВАНИЕМ, смена #277: `.tausik/tausik memory search "bootstrap_drift редеплой"` падает НЕПЕРЕХВАЧЕННЫМ sqlite3.OperationalError: fts5: syntax error near "OR" — трейсбек на 12 кадров вместо сообщения. Это отказ CLI, а по принципу проекта отказ CLI есть баг.

ПРИЧИНА НАЙДЕНА И ОНА ОБЩАЯ, а не про одно слово. backend_queries._sanitize_fts5 раскрывает словоформы через fts_morphology.expand в ГРУППУ В СКОБКАХ: «редеплой» даёт «(редеплой OR редепл*)». Части соединяются ПРОБЕЛОМ. В FTS5 неявное И работает между токенами («a b» годно), но НЕ между токеном и группой в скобках. ЗАМЕРЕНО на чистой БД: «a b» годно, «(x OR y*)» годно, «bootstrap (x OR y*)» ОТКАЗ, «(a OR b*) x» ОТКАЗ, «x (a OR b*)» ОТКАЗ.

ОБЪЁМ ШИРЕ ОДНОЙ КОМАНДЫ: _sanitize_fts5 вызывается из backend_queries.py:96 (memory_search), backend_queries.py:143 и knowledge_read.py:134. Падает любой запрос, где хотя бы одно слово раскрылось, а рядом стоит ещё токен — то есть значительная доля русских запросов из двух слов. Запрос из одного слова проходит, поэтому дефект и прожил незамеченным.

ПОЧЕМУ ЭТО ДОРОГО ИМЕННО АГЕНТУ: память — то, чем агент заменяет чтение файлов, и отказ поиска толкает его читать дерево вместо того, чтобы спросить. Один оборот в этом проекте измерен как ~482k токенов cache_read.

## Acceptance Criteria

## Plan

## Rollback

## Journal
