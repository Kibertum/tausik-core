---
slug: v15-nosdk-verify-endpoint
title: "[P2] Тонкий stateless HTTP verify-endpoint"
status: done
epic: v15-evidence-attestation
story: v15-nosdk-endpoint
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "verify_endpoint.py (stdlib http.server) + CLI serve + тесты"
scope_exclude: "crypto_*/risk_* модули (read-only использование), MCP-сервер"
relevant_files:
  - "scripts/verify_endpoint.py"
  - "scripts/project_cli_serve.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "tests/test_verify_endpoint.py"
scope_paths:
  - "scripts/verify_endpoint.py"
  - "scripts/project_cli_serve.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_errors.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T02:09:10Z"
---

## Goal

Stateless HTTP-endpoint: POST с контекстом задачи/гейтов → вердикт pass/fail + подписанный receipt, без MCP/хуков/SDK. Делает верификацию TAUSIK доступной из любого агента/CI. Заимствует Sift Lite.

## Acceptance Criteria

1. POST /verify c JSON {task_slug, gates[...]} -> 200 {passed, envelope tausik-signed/v1}: вердикт = все non-skipped block-гейты прошли И есть хотя бы один реальный PASS; receipt подписан проектным ключом, проверяем verify_receipt. 2. POST /receipt/verify c envelope или export-артефактом -> {valid: true/false}; GET /key -> публичный ключ + fingerprint; GET /healthz -> ok. Всё stateless, БД не трогается. 3. Негативный: битый JSON/не тот schema/пустые gates -> 400 с ошибкой; нет проектного ключа -> 503 c подсказкой tausik key init; неизвестный путь -> 404. 4. Безопасность: bind 127.0.0.1 по умолчанию, --host для override; приватный ключ в ответах не фигурирует. 5. pytest: end-to-end через http.client (verdict/sign/verify/tamper/400/503/404) + запуск tausik serve --help.

## Plan

## Rollback

git revert: endpoint - отдельный модуль + новая CLI-команда serve, ничего не пишет в БД (stateless), существующие флоу не зависят от него; откат без миграций

## Journal

- 2026-06-12T02:09:09Z [implementation] — AC-1: ✓ tests/test_verify_endpoint.py::TestVerify (verdict block-семантика + all-skipped-not-pass + receipt только ran-гейты, подпись verify_receipt); AC-2: ✓ test_receipt_verify_roundtrip + tamper + GET /key + /healthz, stateless (БД не используется в модуле); AC-3 Negative: ✓ TestNegatives (400 x5 параметров, invalid JSON 400, 404, no-key 503 c подсказкой); AC-4: ✓ bind 127.0.0.1 default, live smoke отказ 0.0.0.0 rc=2 без --yes-expose, test_key_is_public_only (seed отсутствует в ответах); AC-5: ✓ 15 http.client-тестов + live tausik serve --help
- 2026-06-12T02:09:10Z [implementation] — AC verified: 1-5 OK см. лог (15 e2e тестов, live CLI smoke).
