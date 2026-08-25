---
slug: s128-review-fixes-supervision-provenance
title: "Ревью-фиксы сессии #128: честный CLI-emit результат, provenance без ambient-cwd, LIKE-underscore, лишний ре-экспорт"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/hook_supervision.py (return bool), scripts/hooks/_common.py (ре-экспорт), scripts/project_cli_events.py (WARNING), scripts/backend_queries_metrics.py (ESCAPE/GLOB), scripts/model_routing_matrix.py (provenance elimination), tests/"
scope_exclude: "хуки task_gate/scope_write_gate/memory_pretool_block (ordering — follow-up), tausik-qg0.js (negative cache — follow-up), scripts_drift_names (follow-up)"
relevant_files:
  - "scripts/hooks/hook_supervision.py"
  - "scripts/hooks/_common.py"
  - "scripts/project_cli_events.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/model_routing_matrix.py"
  - "tests/test_model_routing.py"
  - "tests/test_fail_open_degradation_telemetry.py"
  - "tests/test_opencode_qg0_plugin.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-21T11:35:26Z"
---

## Goal

Адверсариальное ревью батча #128 (телеметрия надзора + config-trust) нашло 4 контейнерных дефекта для немедленного исправления. (HIGH-1) project_cli_events.cmd_events_emit_supervision печатает «Recorded supervision event» безусловно, хотя emit_supervision_* — best-effort и молча глотают ЛЮБУЮ ошибку записи (hook_supervision:_emit_supervision except: pass), возвращая None. Провал записи неотличим от успеха на ЕДИНСТВЕННОЙ команде, от которой зависит кросс-харнесс паритет — подрывает тезис фальсифицируемости. Фикс: эмиттеры возвращают bool (записано/нет), CLI печатает WARNING в stderr при провале. (HIGH-2) model_routing_matrix._override_provenance зовёт load_project_config() БЕЗ аргумента (ambient cwd) — нарушает конвенцию #265, ту самую, что сосед по диффу (service_doctor_drift) насаждал. Фикс: elimination — проверять машинно-скоупленные user/managed raw-слои, проект-тир по исключению, БЕЗ чтения проект-конфига из cwd. (MEDIUM-2) backend_queries_metrics: LIKE 'bypass_%'/'fail_open_%' — '_' в SQLite это wildcard; экранировать (ESCAPE) либо GLOB, чтобы 3-корзинное разбиение было строгим. (LOW-2) _common ре-экспортирует приватный _emit_supervision без внешних потребителей — убрать из ре-экспорта.

## Acceptance Criteria

1. emit_supervision_bypass/degradation/_emit_supervision возвращают bool (True=строка записана, False=best-effort провал); поведение best-effort сохранено (не бросают, не блокируют). 2. cmd_events_emit_supervision печатает WARNING в stderr при провале записи и НЕ утверждает «Recorded», exit-код сигналит провал (или явный WARNING) — провал отличим от успеха. 3. _override_provenance НЕ читает проект-конфиг из ambient cwd: источник определяется через user/managed raw-слои (машинно-скоуплены, читать ambient корректно) + проект-тир по исключению; #265 не нарушается. 4. Метрика: LIKE-предикаты экранируют '_' (ESCAPE) либо GLOB — 'bypassXfoo' НЕ попадает в bypass-корзину; тест доказывает строгость. 5. _emit_supervision убран из ре-экспорта _common (нет внешних потребителей). 6. Тесты: CLI-провал→WARNING+не-успех; provenance без cwd-зависимости (тест из чужого cwd/без monkeypatch load_project_config); LIKE строгость. Полный pytest затронутых областей зелёный. 7. 3 follow-up заведены: JS negative-cache, skip-emit ordering в 3 хуках, drift-гейт слеп к scripts/hooks/.

## Plan

## Rollback

git revert затронутых файлов + bootstrap --ide all. Все изменения аддитивны/точечны (bool-возврат обратно совместим — None-игнорирующие вызовы продолжают работать; ESCAPE — строже, не ломает текущие литеральные действия).

## Journal

- 2026-07-21T11:34:21Z [implementation] — Фиксы применены. HIGH-1: emit_supervision_bypass/degradation/_emit_supervision → bool (записано/провал); cmd_events_emit_supervision печатает WARNING в stderr + SystemExit(1) при провале (JS best-effort swallow'ит, человек/CI видят). HIGH-2: _override_provenance переписан на elimination — user/managed raw-слои (машинно-скоуплены, ambient корректно), проект-тир по исключению, БЕЗ load_project_config из cwd (#265 не нарушается). MEDIUM-2: LIKE-предикаты экранируют '_' (ESCAPE '\') — bypassXfoo не в bypass-корзине. LOW-2: _emit_supervision убран из ре-экспорта _common. Тесты: +CLI-провал→WARNING+exit1, +provenance не читает cwd (#265 regression guard) + neutral при нечитаемых тирах, +LIKE строгость. 123 зелёных. 3 follow-up заведены: opencode-qg0-negative-cache-broken-cli, hook-skip-emit-before-jurisdiction-check, bootstrap-drift-gate-blind-to-hooks-subdir. Все файлы <400.
- 2026-07-21T11:35:24Z [implementation] — AC verified: 1. ✓ emit_supervision_* → bool, best-effort preserved; test_shares_writer + no-raise tests 2. ✓ cmd_events_emit_supervision WARNING+SystemExit(1) on miss; test_cli_reports_failure_when_write_does_not_land 3. ✓ _override_provenance elimination, no cwd read; test_override_provenance_does_not_read_project_config_from_cwd 4. ✓ LIKE ESCAPE literal underscore; test_like_underscore_is_literal_not_wildcard 5. ✓ _emit_supervision removed from _common re-export; no external importers 6. ✓ 345 green incl telemetry/routing/hooks/metrics/verification; verify #1159 PASS 7. ✓ 3 follow-ups created: opencode-qg0-negative-cache-broken-cli, hook-skip-emit-before-jurisdiction-check, bootstrap-drift-gate-blind-to-hooks-subdir
