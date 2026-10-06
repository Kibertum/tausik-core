---
slug: kilo-mcp-live-wiring
title: "Kilo MCP: live wiring вместо parse-only"
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
depends_on: []
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

В живой сессии Kilo+GLM объявленные в .kilo/kilo.jsonc и .kilocode/mcp.json серверы tausik-project/codebase-rag не загружаются (инструментов tausik_* нет), хотя ручной initialize- handshake проходит (v1.27.0). Замерить на живом хосте, какой источник конфига и какая форма command реально читаются текущей версией Kilo (кандидат: нерасширение  в command), починить генератор bootstrap_kilo.py, и научить doctor отличать 'файл парсится' от 'сервер загружен' через живую initialize-пробу.

## Acceptance Criteria

1) В живой сессии Kilo доступны инструменты tausik_*; зафиксирован источник конфига, который хост реально прочитал. 2) doctor выполняет initialize-handshake пробу обоих серверов и НЕ ставит галку по одному лишь парсингу файла. 3) Негативный: намеренно сломанная станза (несуществующий python/путь) даёт doctor warning/FAIL и явное remediation, а не молчаливую галку. 4) Ре-рангенерация идемпотентна, существующие ключи kilo.jsonc не затираются.

## Plan

## Rollback

## Journal
