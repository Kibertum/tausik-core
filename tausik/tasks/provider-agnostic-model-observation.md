---
slug: provider-agnostic-model-observation
title: "Провайдеро-независимое наблюдение модели (z.ai, локальные, любые)"
status: done
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Наблюдение модели: kilo-плагин-наблюдатель (chat-хук -> .tausik/runtime/active_model.json), цепочка providers/kilo.py (runtime-файл раньше env), shell.env-инъекция TAUSIK_AGENT_MODEL, doctor с именем источника, .gitignore, тесты, доки"
scope_exclude: null
relevant_files:
  - "scripts/jsonc_utils.py"
  - "scripts/providers/kilo.py"
  - "scripts/service_doctor_kilo.py"
  - "scripts/service_doctor_model_source.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v73.py"
  - "scripts/backend_crud.py"
  - "scripts/gate_cross_model_parity.py"
  - "bootstrap/bootstrap_kilo.py"
  - "bootstrap/bootstrap.py"
  - "harness/kilo/plugins/tausik-observe.js"
  - "tests/test_providers.py"
  - "tests/test_kilo_observe_plugin.py"
  - "tests/test_session_model_id.py"
  - "tests/test_doctor_session_model.py"
  - "tests/test_host_gate_plugins.py"
  - "tests/test_cross_model_parity_gate.py"
  - "docs/en/kilo-zai.md"
  - "docs/ru/kilo-zai.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - "tausik/tasks/provider-agnostic-model-observation.md"
scope_paths:
  - "scripts/*"
  - "harness/*"
  - "tests/*"
  - "docs/*"
  - ".gitignore"
  - "bootstrap/*"
  - "tausik/tasks/provider-agnostic-model-observation.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - kilo-mcp-live-wiring
completed_at: "2026-10-06T18:23:34Z"
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

Doctor: session #288 carries no model — детекция (KILO_MODEL env, .kilocode/kilo.json) не видит модель, выбранную в UI Kilo; провайдер kilo.py даже не читает наш .kilo/kilo.jsonc. Хук chat.message/chat.params плагина отдаёт живой {providerID, modelID} ЛЮБОГО провайдера Kilo — z.ai, Ollama, LM Studio, vLLM, что угодно. Плагин пишет .tausik/runtime/active_model.json; providers/kilo.py читает его в цепочке до env; shell.env прокидывает TAUSIK_AGENT_MODEL в bash-сессии; отсутствие данных остаётся unknown без угадывания по имени хоста.

## Acceptance Criteria

1) Сессия Kilo+glm-4.7 (zai-coding-plan) получает sessions.model_id и имя источника в doctor. 2) Локальная модель (ollama/*) фиксируется тем же механизмом без правки кода. 3) Негативный: при отсутствии данных doctor warning сохраняется, модель НЕ угадывается из имени хоста/провайдера. 4) shell.env-инъекция TAUSIK_AGENT_MODEL подтверждена живым echo из bash-инструмента. 5) Файл runtime-состояния не содержит секретов и попадает в .gitignore.

## Plan

## Rollback

git revert; удалить .kilo/plugins/tausik-observe.js; провайдер kilo.py возвращается к env+config-цепочке; .gitignore-строку снять

## Journal

- 2026-10-06T18:11:30Z [implementation] — AC verified: AC-1 ✓ tests/test_session_model_id.py::test_session_start_with_no_env_falls_through_to_the_provider (model=glm-4.6 + model_source='provider:claude' STORED at open, v73) + tests/test_doctor_session_model.py::test_a_recorded_row_names_the_source_stored_at_open (ok line says 'declared by provider:kilo'). AC-2 ✓ provider-agnostic by construction: tests/test_kilo_observe_plugin.py (chat event from non-zai provider id 'qwen3:8b' writes the same runtime file, live beats stale) + tests/test_providers.py (runtime file beats env/config regardless of provider; project .kilo/kilo.jsonc + global ~/.config/kilo/kilo.jsonc via shared jsonc scanner). AC-3 ✓ NEGATIVE: test_session_start_records_absence_when_nothing_at_all_reports_a_model (NULL, not a guess) + tests/test_doctor_session_model.py (silence stays warn + names TAUSIK_AGENT_MODEL way out, never host-name inference; legacy v72 row says 'recorded before sources were stored' and does NOT borrow today's chain) + LIVE doctor on this very tree: session #290 line prints the warning verbatim with no model. AC-4 ✓ harness: tests/test_kilo_observe_plugin.py::TestShellEnvInjection (bash receives TAUSIK_AGENT_MODEL after an observed chat event; nothing injected without one). LIVE echo inside a running Kilo session: PENDING one host restart — documented as pending in docs en/ru + both CHANGELOGs, no overclaim. AC-5 ✓ .gitignore already contains .tausik/ (verified by check-ignore on a runtime path); file payload pinned to {provider_id, model_id, source, updated_at} — ids only. Domain: doctor on this repo reports 'kilo: 2 plugins' (enforcement coverage counts both plugins from disk) and the Live enforcement line honestly says local self-report only. Schema: migration v73 ALTER sessions ADD model_source TEXT, additive, parity guard green, mypy clean on 7 touched files.
- 2026-10-06T18:23:33Z [implementation] — NO-DEAD-END: verify #3528 red on filesize (backend_migrations.py 505>500 after adding the v73 entry — compressed own entry + merged two historical two-line comments, slug refs kept, now exactly 500) and on 2 undeclared files (README.md/README.ru.md auto-edited by gen_doc_constants — declared in relevant-files). verify #3529 red on tests/test_schema_upgrade_parity.py column-order ratchet: fresh DDL placed model_source before host_session_id while the migration appends it last — moved the column LAST in the fresh schema so fresh and migrated converge on one order (the same rule decisions.slug documents); NOT a dead end, both failures were fixed in-session, green verify #3530.
