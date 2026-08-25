---
slug: dedupe-verify-cache-ttl
title: "Single-source DEFAULT_CACHE_TTL_S (verify-cache TTL дублирован в 3 файлах)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "Новый scripts/verify_constants.py; правка импортов в scripts/service_verification.py, scripts/verify_cache.py, scripts/verify_recent_lookup.py. НЕ трогать: service_gates.py (берёт через re-export), значение 600, поведение кэша."
scope_exclude: "scripts/service_gates.py, логику has_fresh_verify_run, значение TTL"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T23:56:26Z"
---

## Goal

Устранить тройное дублирование магической константы verify-cache TTL (600s) с комментариями 'keep in sync'/'mirrors' в service_verification.py, verify_cache.py, verify_recent_lookup.py. Ввести единый источник истины verify_constants.py (stdlib-only, без upstream-импортов — снимает заявленный import-cycle), остальные модули импортируют из него. Поведение и публичный API (re-export для service_gates) не меняются.

## Acceptance Criteria

1. Литерал '600' для TTL определён РОВНО в одном месте (verify_constants.py); grep по 'CACHE_TTL_S = 600' даёт единственный хит. 2. service_verification.py, verify_cache.py, verify_recent_lookup.py импортируют константу из verify_constants, без локального '= 600'. 3. Комментарии 'keep in sync'/'mirrors' удалены (источник один). 4. service_gates продолжает импортировать DEFAULT_CACHE_TTL_S из service_verification (re-export сохранён) — без правок service_gates. 5. Негативный сценарий / boundary: при наличии import-цикла импорт любого из трёх модулей поднял бы ImportError — проверяем, что `python -c 'import ...'` для всех трёх НЕ выдаёт ошибку (verify_constants не импортирует ни один из них). 6. Ошибка при опечатке имени: импорт несуществующего символа из verify_constants падает с ImportError (sanity отсутствия тихого фолбэка). 7. Существующие тесты verify-cache зелёные, ruff чист.

## Plan

## Rollback

## Journal

- 2026-06-13T23:56:26Z [implementation] — AC verified: 1.✓ grep 'CACHE_TTL_S = 600' даёт единственный хит verify_constants.py:16. 2.✓ три модуля импортируют из verify_constants, локальных '=600' нет. 3.✓ комментарии keep-in-sync/mirrors удалены. 4.✓ service_gates без правок (re-export сохранён, import OK). 5.✓ Negative: import всех трёх + service_gates без ImportError (verify_constants не импортит siblings) — цикла нет. 6.✓ ruff clean. 7.✓ pytest 147 passed (test_service_verification + test_config_knobs + test_qg2_gates). Tested via: tests/test_service_verification.py, tests/test_config_knobs.py. Domain: TTL=600 единый, кэш-поведение неизменно.
