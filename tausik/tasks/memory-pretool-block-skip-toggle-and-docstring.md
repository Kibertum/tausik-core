---
slug: memory-pretool-block-skip-toggle-and-docstring
title: "memory_pretool_block: docstring врёт про TAUSIK_SKIP_HOOKS + инструментировать TAUSIK_SKIP_MEMORY_HOOK"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/memory_pretool_block.py (docstring + main skip-path), tests/ (новый тест-файл)"
scope_exclude: "scripts/hooks/_common.py::emit_supervision_bypass (переиспользуем как есть), прочие хуки"
relevant_files:
  - "scripts/hooks/memory_pretool_block.py"
  - "tests/test_memory_hook_skip_telemetry.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-21T10:25:46Z"
---

## Goal

Найдено разведкой l26-bypass-telemetry. scripts/hooks/memory_pretool_block.py: докстринг (:15) заявляет «Skipped via TAUSIK_SKIP_HOOKS=1», но код (:86) honors ТОЛЬКО TAUSIK_SKIP_MEMORY_HOOK — зонтичный TAUSIK_SKIP_HOOKS его НЕ выключает. Два дефекта: (1) docstring рассинхронизирован с кодом (нарратив != код, класс l26-narrative-honesty); (2) TAUSIK_SKIP_MEMORY_HOOK — это способ обойти защиту кросс-проектной памяти, и он НЕ инструментирован телеметрией обходов. Задача: привести докстринг в соответствие с кодом (либо реально honor TAUSIK_SKIP_HOOKS — решить осознанно, это гвард кросс-проектной памяти) И эмитить supervision-событие bypass_skip_memory_hook при срабатывании, симметрично l26-bypass-telemetry.

## Acceptance Criteria

1. Docstring memory_pretool_block.py точно описывает реальный skip-контракт (какие env-флаги honored). 2. main() honors И зонтичный TAUSIK_SKIP_HOOKS, И специфичный TAUSIK_SKIP_MEMORY_HOOK — симметрично остальным хукам suite. 3. Каждый skip-путь эмитит supervision-событие через emit_supervision_bypass с различимым vector (skip_hooks vs skip_memory_hook), entity_id='memory_pretool_block'. 4. Телеметрия best-effort: не роняет hook при ошибке БД (exit 0 сохраняется). 5. Тесты покрывают: docstring-код паритет не регрессирует, оба флага пропускают запись, оба эмитят различимое событие, отсутствие флагов не эмитит. Все тесты зелёные (pytest).

## Plan

## Rollback

## Journal

- 2026-07-21T10:19:46Z [implementation] — Impl: docstring переписан (оба флага honored при любом non-empty значении, симметрия suite, каждый эмитит bypass-трейс). main() теперь honorит TAUSIK_SKIP_HOOKS (vector=skip_hooks) И TAUSIK_SKIP_MEMORY_HOOK (vector=skip_memory_hook), оба entity_id=memory_pretool_block, через best-effort emit_supervision_bypass. Проверка truthy (не ==1) — паритет с 20 прочими хуками suite. Decision #159.
- 2026-07-21T10:22:34Z [implementation] — Тесты: новый tests/test_memory_hook_skip_telemetry.py (11 тестов): оба флага пропускают+эмитят различимый vector на реальном db, umbrella>specific (один row), no-flag блокирует+0 rows, любой truthy honored, corrupt-db не роняет skip, docstring↔код паритет по regex (анти-дрейф). Рефактор: один локальный импорт emit. Регрессий нет: 47 (memory) + 99 (bypass+hooks+parity) зелёные.
- 2026-07-21T10:22:47Z [implementation] — AC verified: 1. ✓ docstring переписан: перечисляет оба флага с семантикой 'any non-empty value'; test_docstring_flags_equal_honored_flags пинует множество флагов docstring == honored в main() 2. ✓ main() honorит TAUSIK_SKIP_HOOKS и TAUSIK_SKIP_MEMORY_HOOK (truthy, паритет suite); test_both_flags_present, test_arbitrary_truthy_value_honored 3. ✓ emit_supervision_bypass vector=skip_hooks|skip_memory_hook, entity_id=memory_pretool_block; test_umbrella_skip_hooks_passes_and_emits, test_specific_skip_memory_hook_passes_and_emits, test_umbrella_wins_over_specific_and_emits_once 4. ✓ corrupt db → skip остаётся exit 0; test_telemetry_failure_never_blocks 5. ✓ pytest: 47 (memory) + 99 (bypass+hooks+parity) зелёные; verify passed gates=[hadolint,pytest]
- 2026-07-21T10:23:04Z [implementation] — AC verified: 1. ✓ docstring перечисляет оба флага (any non-empty value); test_docstring_flags_equal_honored_flags: множество флагов docstring == honored в main() 2. ✓ main() honorит оба флага truthy (паритет suite); test_both_flags_present, test_arbitrary_truthy_value_honored 3. ✓ emit vector=skip_hooks|skip_memory_hook entity_id=memory_pretool_block; test_umbrella/specific/umbrella_wins 4. ✓ corrupt db → exit 0; test_telemetry_failure_never_blocks 5. ✓ 47+99 зелёные; verify passed gates=[hadolint,pytest]
- 2026-07-21T10:25:45Z [implementation] — AC verified: 1. ✓ docstring<->code parity test 2. ✓ both flags honored truthy, suite parity 3. ✓ distinct vectors skip_hooks/skip_memory_hook emitted 4. ✓ corrupt db -> exit 0 test 5. ✓ verify run #1148 pytest PASS; 47+99 green
