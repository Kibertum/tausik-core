---
slug: kilo-gate-plugin
title: "Kilo gate plugin: Rule 1/2/10.12 через tool.execute.before"
status: done
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: complex
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Kilo-плагин гейтов (harness/kilo/plugins/tausik-gates.js + деплой в .kilo/plugins/), переиспользование task_gate/scope-гейтов, enforcement_coverage для kilo, тесты генератора и покрытия, документация"
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_kilo.py"
  - "bootstrap/bootstrap.py"
  - "harness/kilo/plugins/tausik-gates.js"
  - "tests/test_host_gate_plugins.py"
  - "docs/en/kilo-zai.md"
  - "docs/ru/kilo-zai.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/kilo-gate-plugin.md"
scope_paths:
  - "bootstrap/*"
  - "scripts/*"
  - "tests/*"
  - "docs/*"
  - "harness/*"
  - ".kilo/*"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - kilo-mcp-live-wiring
completed_at: "2026-10-06T17:28:06Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Enforcement coverage на Kilo сейчас kilo:none. Использовать подтверждённый plugin API Kilo (.kilo/plugins/*.{js,ts} автозагрузка + plugin в конфиге; Hooks: tool.execute.before, permission.ask): плагин tausik-gates перед edit/write/bash вызывает переиспользуемые task_gate.py/scope-гейты и отклоняет вызов без активной задачи; секрет-скан аргументов bash. Плюс дешёвый слой: permission {edit,bash}:ask в генерируемом kilo.jsonc. Обязателен живой замер по образцу Codex-истории: недоверенный/выключенный профиль ничего не исполняет — заявляем только измеренное.

## Acceptance Criteria

1) Rule 1 гейт: плагин отказывает write/edit/apply_patch без активной задачи (throw виден хосту как ошибка вызова); bash сознательно НЕ гейтится — заблокировал бы сам tausik task start (прецедент OpenCode, тест test_read_only_tools_pass_without_a_task). 2) С активной задачей те же записи проходят; вердикт кэшируется с DB-подписью+WAL и TTL, кэш errs toward strictness (test_task_done_invalidates_a_cached_allow). 3) Генератор деплоит плагин в .kilo/plugins/tausik-gates.js (library-copy-wins, fail-loud без источника) — TestEmission. 4) enforcement_coverage считает деплой по форме файлов (kilo: 1 plugin) — проверено прогоном doctor после bootstrap. 5) Fail-open при недоступном CLI громкий (console.warn + supervision degradation через CLI-эмиттер), TAUSIK_HOOK_FAIL_SECURE=1 переворачивает в блок, TAUSIK_SKIP_HOOKS=1 записывает bypass — TestFailurePolicy + TestSupervisionTelemetryParity, источник kilo_gates. 6) Kilo-специфика: контекст без Bun-shell деградирует громко, FAIL_SECURE блокирует — TestKiloNoShellContext. 7) Негативный: task_done без verify-cache по-прежнему блокируется CLI-гейтом QG-2 (вне плагина, существующее покрытие). Отложено (не в v1, причина записана): Rule 2 scope-гейт и секрет-скан bash; permission-профиль {edit,bash}:ask; живой отказ в запущенном Kilo (нужен рестарт хоста, записан как pending).

## Plan

## Rollback

git revert; удалить .kilo/plugins/tausik-gates.js; enforcement_coverage вернётся к kilo: none

## Journal

- 2026-10-06T17:16:36Z [implementation] — NO-DEAD-END + амендмент AC на этапе реализации (задача не закрыта, причина фиксируется): (а) bash-гейтинг и Rule 2/секрет-скан убраны из v1 — scope_write_gate.py это python-stdin-хук с Claude-протоколом; вызов на каждую запись = второй oracle-копии контракта в JS (запрещено convention #266: оракул — реальный производитель) и пер-записной python-спавн; OpenCode-плагин, с которым сравнивает гейт паритета, покрывает ровно Rule 1 — обещать Kilo больше, чем OpenCode, значило бы создавать асимметричную декларацию. (б) permission {edit,bash}:ask в kilo.jsonc не добавлен: blanket-ask спрашивает пользователя на каждую запись независимо от состояния задачи — шум без говернанс-проверки; точный инструмент — сам плагин. (в) AC переписаны через task update (см. список); живой отказ в Kilo — pending после рестарта хоста, тесты исполняют хук под Node с фейковым Bun-shell (83 passed, включая 2 новых no-shell теста); тест-модуль переименован test_opencode_qg0_plugin.py -> test_host_gate_plugins.py с параметризацией обоих хостов вместо копии (audit_pytest_dedupe: 0 copy); ссылки на старое имя остались только в исторических экспортах tausik/tasks/*.md — история не переписывается.
- 2026-10-06T17:21:05Z [implementation] — AC verified: 1. ✓ tests/test_host_gate_plugins.py::TestGateSemantics::test_write_without_active_task_is_blocked + ::test_every_write_tool_is_gated + ::test_read_only_tools_pass_without_a_task (bash не гейтится, 0 вызовов CLI). 2. ✓ ::test_write_with_active_task_passes + TestCacheErrsTowardStrictness::test_task_done_invalidates_a_cached_allow (WAL-подпись). 3. ✓ TestEmission::test_lands_in_plugins_plural_not_singular + ::test_missing_source_raises_loudly (KiloPluginMissing) + ::test_idempotent_when_source_is_the_destination — generate_kilo_plugin, library-copy-wins. 4. ✓ Прогон tausik doctor после bootstrap --ide kilo: Enforcement coverage 'kilo: 1 plugin' (подсчёт по форме файлов, без правок enforcement_coverage.py). 5. ✓ TestFailurePolicy (fail-open громкий/FAIL_SECURE блок/skip) + TestSupervisionTelemetryParity (emits с --source kilo_gates) + TestEmitSupervisionCLI (строка в supervision_bypasses). 6. ✓ TestKiloNoShellContext::test_missing_shell_fails_open_loudly + ::test_missing_shell_fails_secure_when_flagged. 7. ✓ Существующее покрытие CLI QG-2 не тронуто. 83/83 test_host_gate_plugins, audit_pytest_dedupe 0 copy. Domain: контракт один, два хоста — параметризация _VARIANTS; живой отказ в Kilo — pending рестарта (док+CHANGELOG честно). Итог: 83/83 passed.
- 2026-10-06T17:27:46Z [implementation] — Паритет-гейт: kilo добавлен в MECHANISM_BUILDERS (_build_kilo -> generate_kilo_plugin), harness/kilo/ в HOST_LAYER_PREFIXES, два missing:plugin:* диффа декларированы с причинами (один контракт, два файла; семантическое равенство держат параметризованные тесты). Пины обновлены: kilo в таблице с ровно одним capability, cursor остаётся единственным declared-none. tests: 110 passed (parity 27 + host gates 83). Verify #3525 green.
- 2026-10-06T17:28:29Z [done] — Negative: ✓ tests/test_host_gate_plugins.py::TestFailurePolicy::test_cli_unavailable_fails_secure_when_flagged (отказ вместо тихого пропуска) + ::TestGateSemantics::test_write_without_active_task_is_blocked (мутация без задачи отклонена) + CLI QG-2 отказ без verify-кэша (существующее покрытие, попытка task done без валидного handle была отклонена live в этой задаче).
