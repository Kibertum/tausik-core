---
slug: state-git-triggers
title: "Автоматизация round-trip: экспорт при записи, импорт при старте сессии"
status: done
epic: team-state-in-git
story: state-in-branch-mvp
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: "scripts/state_export.py (добавить helper export_one/render одной сущности — переиспользуя рендереры), scripts/hooks/ или service-post-write слой (пост-обработчики task done/decide/memory add), session_open интеграция (mcp/service), config-флаг, tests/test_state_triggers.py"
scope_exclude: "Разгитигнор tausik/ и round-trip гейт (это state-git-roundtrip-gate); изменение самих export/import ядер кроме добавления single-entity helper; полная переработка session_open"
relevant_files:
  - "scripts/state_export.py"
  - "scripts/state_triggers.py"
  - "tests/test_state_triggers.py"
scope_paths:
  - "scripts/state_export.py"
  - "scripts/state_triggers.py"
  - "scripts/service_task.py"
  - "scripts/service_knowledge.py"
  - "scripts/service_cq_row.py"
  - "harness/claude/mcp/project/handlers.py"
  - "tests/test_state_triggers.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-25T20:15:59Z"
---

## Goal

Связать export/import с жизненным циклом, чтобы файлы всегда отражали БД, а БД — ветку, без ручных команд.

Объём: (1) Экспорт при записи durable-сущности: хук/пост-обработчик на task done, decide, memory add (и, вероятно, task log / task update) — сериализует ИЗМЕНЁННУЮ сущность в её файл. Инкрементально (один файл на одно изменение), не полный экспорт каждый раз. (2) Импорт при старте сессии: /start (session_open) обнаруживает, что файлы новее БД (после git pull) и предлагает/выполняет tausik sync. (3) Fail-open: сбой сериализации НЕ должен ронять task done / decide (best-effort, как остальные пост-scope хуки — памятка про gotcha #271). (4) Производительность: инкрементальный экспорт не должен заметно замедлять task done.

Зависит от state-git-export и state-git-import.

## Acceptance Criteria

1. ИНКРЕМЕНТАЛЬНЫЙ экспорт изменённой сущности: пост-обработчик на task done / decide / memory add (+ task update) сериализует ТОЛЬКО эту сущность в её файл tausik/<kind>/<slug>.md, байт-идентично тому, что дал бы полный export для неё (переиспользует рендереры state_export). Не полный экспорт на каждое изменение. 2. FAIL-OPEN (критично, gotcha #271): сбой сериализации (исключение/IO/нет слага) НЕ роняет и НЕ откатывает основную операцию — best-effort, ошибка телеметрируется, не пробрасывается. Тест: замоканный сбой экспорта → task done всё равно успешен. 3. Импорт при старте: session_open/start обнаруживает, что файлы tausik/ новее БД (после git pull) и предлагает/выполняет sync; ничего деструктивного молча. 4. НЕГАТИВ slug-less: сущность без слага → пост-хук НЕ падает, просто пропускает с логом (в отличие от полного export, который отказывает — инкрементальный обязан быть best-effort). 5. НЕГАТИВ отключаемость: флаг config state.auto_export=off — проект, не разгитигноривший tausik/, не получает неожиданных файлов. 6. ИДЕМПОТЕНТНОСТЬ+ПРОИЗВОДИТЕЛЬНОСТЬ: повторное срабатывание без изменений не меняет файл; экспорт одной сущности не пишет всё дерево (тест: 1 файл, не 1953). 7. Полный scoped verify зелёный.

## Plan

## Rollback

Config-флаг state.auto_export=off отключает триггеры мгновенно. Fail-open по построению: даже сломанный триггер не ломает основные операции. Откат: git revert коммита. Не трогает схему/данные; tausik/ ещё в .gitignore до roundtrip-gate, так что лишние файлы не попадают в git.

## Journal

- 2026-07-25T20:15:43Z [implementation] — Завершено. export_one (single-entity рендер, байт-идентичен build_tree — пин-тест) + state_triggers.py (auto_export_entity/by_id fail-open+config-gated+идемпотентный, import_suggested content-based detect). Врезки: task_done (service_task, fold в существующий best-effort try), memory_add+decide (service_knowledge), session_open sync_suggested секция (handlers.py, best-effort+watchdog). Negative: fail-open при замоканном сбое export_one → task/op не падает (test_auto_export_fail_open); slug-less/absent → skip без краха (test_..slugless_skips); disabled по умолчанию → 0 файлов (test_..disabled_writes_nothing). Domain: auto_export пишет РОВНО один файл (не 1953), байт-идентичный полному export; import_suggested детектит расхождение дерево↔БД. Filesize: service_task 398, service_knowledge 380 (извлёк build_cq_row→service_cq_row, схлопнул импорт). 20 unit + 174 регрессионных (session_open/task_done/export/import/cq) зелёные, scoped verify PASS, ruff чист, bootstrap redeploy.
- 2026-07-25T20:15:57Z [implementation] — AC verified: 1. ✓ ИНКРЕМЕНТАЛЬНЫЙ экспорт: export_one байт-идентичен build_tree (test_state_triggers.py::test_export_one_is_byte_identical_to_build_tree); auto_export пишет РОВНО один файл, не дерево (::test_auto_export_writes_byte_identical_single_file — assert written==['exp.md']); врезки в task_done/decide/memory_add 2. ✓ FAIL-OPEN: замоканный сбой export_one → auto_export возвращает False без исключения (::test_auto_export_fail_open_on_serialization_error); врезка в task_done внутри существующего best-effort try; import_suggested → None при любой ошибке 3. ✓ Импорт при старте: session_open несёт секцию sync_suggested (handlers.py, best-effort+watchdog); import_suggested content-based dry-run детектит расхождение (::test_import_suggested_flags_divergence added>0) и None когда совпадает (::test_import_suggested_none_when_tree_matches_db) 4. ✓ НЕГАТИВ slug-less/absent: export_one→None → auto_export skip без краха (::test_auto_export_slugless_skips_without_crash, ::test_export_one_absent_entity_returns_none) 5. ✓ НЕГАТИВ отключаемость: config state.auto_export default off → 0 файлов (::test_auto_export_disabled_writes_nothing, assert not root.exists()) 6. ✓ ИДЕМПОТЕНТНОСТЬ+ПРОИЗВОДИТЕЛЬНОСТЬ: повторный вызов без изменений → False, файл не тронут (::test_auto_export_idempotent); один файл на изменение, не полное дерево (::test_..single_file) 7. ✓ Scoped verify PASS (pytest над test_state_export+test_state_triggers); 20 unit + 174 регрессионных (session_open/task_done/export/import/cq/knowledge) зелёные; ruff чист; filesize service_task 398/service_knowledge 380 под cap (извлёк service_cq_row); bootstrap redeploy --ide all
