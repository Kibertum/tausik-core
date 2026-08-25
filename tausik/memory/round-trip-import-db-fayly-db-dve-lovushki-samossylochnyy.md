---
slug: round-trip-import-db-fayly-db-dve-lovushki-samossylochnyy
title: "Round-trip импорт DB→файлы→DB: две ловушки — самоссылочный FK и дубли журнала как мультимножество"
type: gotcha
tags:
  - determinism
  - foreign-key
  - idempotency
  - import
  - round-trip
  - sqlite
task: state-git-import
edges: []
---

Пин round-trip (ре-экспорт импортированной БД = байт-идентичное дерево) на РЕАЛЬНЫХ данных вскрыл две ловушки, невидимые на синтетике: (1) tasks.defect_of — самоссылочный FK на tasks(slug); при вставке в порядке слагов (не зависимостей) задача, ссылающаяся на ещё не вставленного сиблинга, роняет per-statement FK-проверку. Фикс: `PRAGMA defer_foreign_keys=ON` внутри транзакции — SQLite проверяет FK при COMMIT, когда все слаги уже есть (сбрасывается сам в конце tx). Общий приём для любого импортёра графа с forward-refs. (2) Journal-дедуп по ПРИСУТСТВИЮ (created_at,message,phase) схлопывает подлинно-дублированные строки лога (одинаковые ts+msg+phase, разные лишь по autoincrement id — реально встречается: повторный AC-verified лог). Нужна МУЛЬТИМНОЖЕСТВЕННАЯ семантика: Counter(файл) vs Counter(БД), вставить (want-have) копий. Так и идемпотентность держится (равные счётчики → 0 вставок), и обе копии переживают round-trip. Мораль: пинай round-trip на живом стейте, синтетика не содержит вырожденных дублей и forward-ref рёбер. См. [[gejt-check-slep-k-crlf]] — тот же принцип «проверяй на реальных байтах».
