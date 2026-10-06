---
slug: provider-agnostic-model-observation
title: "Провайдеро-независимое наблюдение модели (z.ai, локальные, любые)"
status: planning
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - kilo-mcp-live-wiring
completed_at: null
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

## Journal
