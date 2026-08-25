---
slug: l26-bypass-telemetry-opencode-parity
title: "Паритет телеметрии обходов в opencode JS-плагине (кросс-харнесс)"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_parser.py (подкоманда), scripts/project_cli_events.py (handler), harness/opencode/plugins/tausik-qg0.js (emit-вызовы + reorder), tests/test_opencode_qg0_plugin.py (driver fake + assertions), возможно новый Python-тест CLI-команды"
scope_exclude: "scripts/hooks/hook_supervision.py (переиспользуется как оракул, не трогаем), Python-хуки"
relevant_files:
  - "scripts/project_parser.py"
  - "scripts/project_cli_events.py"
  - "harness/opencode/plugins/tausik-qg0.js"
  - "tests/test_opencode_qg0_plugin.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-21T10:46:52Z"
---

## Goal

Follow-up к l26-bypass-telemetry (эмиссия supervision-событий на обход в Python-хуках). Тот же обход живёт в ДРУГОМ харнессе: harness/opencode/plugins/tausik-qg0.js:133 `if (process.env.TAUSIK_SKIP_HOOKS) return;` и :136 TAUSIK_HOOK_FAIL_SECURE. Node-процесс, не Python — Python-хелпер emit_supervision_bypass туда не достаёт. Задача: инструментировать JS-плагин так, чтобы обход TAUSIK_SKIP_HOOKS (и fail-open ветки) писал строку events(entity_type='supervision', action='bypass_skip_hooks') того же формата, что Python-сторона, — иначе телеметрия обходов слепа на opencode-харнессе и метрика supervision_bypasses врёт по составу. Проверить: контракт строки (entity_type/action) идентичен Python-эмиттеру; chain-safe raw INSERT (entry_hash NULL). Стек JS — вне docker/python проекта, вести без stack-тега.

## Acceptance Criteria

1. Новая CLI-подкоманда `tausik events emit-supervision --kind {bypass|degradation} --vector V --source ENTITY [--details D]` пишет supervision-строку через ТОТ ЖЕ Python-эмиттер (hook_supervision), гарантируя идентичный контракт (entity_type='supervision', action='bypass_V'/'fail_open_V', chain-safe raw INSERT, entry_hash NULL). 2. JS-плагин tausik-qg0.js в ветке TAUSIK_SKIP_HOOKS эмитит bypass_skip_hooks (source=opencode_qg0) через CLI; в fail-open ветке (CLI недостижим, не fail-secure) эмитит degradation. 3. Паритет области: emit ТОЛЬКО для write-инструментов (WRITE_TOOLS-фильтр ПЕРЕД skip-проверкой), read-инструменты не эмитят — как matcher Python. 4. Best-effort: emit не блокирует и не роняет плагин (провал CLI → нет строки, не throw). 5. Python-тест: CLI-команда пишет корректную строку-оракул. 6. Node-тест: плагин реально вызывает emit в skip и fail-open ветках; существующие calls-ассерты не сломаны (emit отделён от status в фейке); read-инструменты не эмитят. 7. Bootstrap redeploy opencode; drift чист. Зелёный pytest.

## Plan

## Rollback

git revert затронутых файлов (project_parser.py, project_cli_events.py, harness/opencode/plugins/tausik-qg0.js, tests) + повторный bootstrap --ide all для отката развёрнутых копий. CLI-подкоманда аддитивна (новый парсер-узел) — снятие не ломает существующие команды.

## Journal

- 2026-07-21T10:46:27Z [implementation] — Impl: CLI-подкоманда `events emit-supervision --kind/--vector/--source/--details` (project_parser.py + handler cmd_events_emit_supervision в project_cli_events.py) зовёт тот же hook_supervision-эмиттер (оракул, project_dir от svc.tausik_dir() не cwd). JS-плагин tausik-qg0.js: хелпер _recordSupervision (best-effort, awaited, swallow), reorder WRITE_TOOLS-фильтр ПЕРЕД skip (паритет области с Python matcher), эмиссия bypass_skip_hooks в skip-ветке + degradation cli_unreachable в fail-open. Тесты: driver-фейк отделяет emit от status (calls vs emits); +TestSupervisionTelemetryParity (skip эмитит bypass, read НЕ эмитят, fail-open эмитит degradation, healthy/fail-secure не эмитят) + TestEmitSupervisionCLI (оракул: bypass/degradation action, entry_hash NULL chain-safe, попадает в bypasses-метрику не detections). E2E смоук реального CLI: строка ('supervision','opencode_qg0','bypass_skip_hooks',NULL). Bootstrap --ide all, drift чист, deployed-плагин содержит новый код. 130 тестов зелёные.
- 2026-07-21T10:46:50Z [implementation] — AC verified: 1. ✓ CLI events emit-supervision via hook_supervision oracle; TestEmitSupervisionCLI + e2e smoke row entry_hash NULL 2. ✓ JS skip->bypass_skip_hooks, fail-open->degradation; test_skip_hooks_emits_bypass, test_fail_open_emits_degradation 3. ✓ WRITE_TOOLS before skip; test_read_only_tools_never_emit_under_skip 4. ✓ best-effort awaited swallow; test_healthy_write_emits_nothing, test_fail_secure_blocks_without_emitting 5. ✓ TestEmitSupervisionCLI oracle contract + chain-safe + bypasses-metric-not-detections 6. ✓ 37 node+python plugin tests; existing calls-asserts intact 7. ✓ bootstrap --ide all, drift clean, deployed plugin has code; verify #1155 pytest PASS; 130 green
