---
slug: split-backend-queries-metrics
title: "Filesize: backend_queries.py 461→<400 (извлечь Metrics-миксин)"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "Новый scripts/backend_queries_metrics.py (BackendQueriesMetricsMixin + _session_hours); scripts/backend_queries.py (удалить 3 метода + helper, добавить импорт+наследование). НЕ трогать: SQL-логику методов, прочие блоки (Search/FTS/Roadmap/Graph/Events), backend_tier_metrics."
scope_exclude: "SQL-запросы, backend_tier_metrics.py, backend_queries_usage.py, публичные сигнатуры методов"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T00:23:04Z"
---

## Goal

backend_queries.py = 461 строк, нарушает hard-лимит 400 (gate пропустил — сканирует только changed-files). Извлечь когезивный блок Status & Metrics (get_status_data, get_metrics, session_capacity_summary + helper _session_hours, ~110 строк) в новый backend_queries_metrics.py как BackendQueriesMetricsMixin. BackendQueriesMixin наследует его — публичная поверхность SQLiteBackend (svc.be.get_metrics и т.д.) неизменна.

## Acceptance Criteria

1. backend_queries.py < 400 строк (было 461). 2. backend_queries_metrics.py содержит get_status_data, get_metrics, session_capacity_summary, _session_hours; BackendQueriesMixin наследует BackendQueriesMetricsMixin. 3. Публичная поверхность неизменна: svc.be.get_metrics()/get_status_data()/session_capacity_summary() работают (MRO корректен). 4. Negative/boundary: вызов get_metrics на пустой БД не падает (done=0 → деления защищены) — существующий тест metrics. 5. Метрики возвращают идентичный результат (значения те же, перемещение без изменения логики). 6. filesize-gate проходит для обоих файлов. 7. pytest (metrics/backend/service тесты) зелёный, ruff чист.

## Plan

## Rollback

git checkout scripts/backend_queries.py + rm scripts/backend_queries_metrics.py. Чисто механическое перемещение кода без изменения логики/схемы — откат тривиален, runtime не затронут.

## Journal

- 2026-06-14T00:23:04Z [implementation] — AC-1: ✓ backend_queries.py 461→350 строк (<400). AC-2: ✓ backend_queries_metrics.py (124 строки) с 3 методами+_session_hours; BackendQueriesMixin(BackendQueriesUsageMixin, BackendQueriesMetricsMixin). AC-3: ✓ SQLiteBackend.get_metrics/get_status_data/session_capacity_summary доступны (MRO проверен import-смоком). AC-4: ✓ Negative: пустая БД done=0, деления защищены — tested via tests/test_tausik_backend.py. AC-5: ✓ значения идентичны (чистое перемещение, SQL не тронут) — 146 metrics-тестов зелёные. AC-6: ✓ filesize-gate проходит оба файла. AC-7: ✓ pytest 146 passed (metrics_session_usage/tier/senar/e2e/backend), ruff clean. Domain: метрики SQLiteBackend неизменны.
