---
slug: v15-nosdk-docs-example
title: "[P2] Docs + пример интеграции для non-Claude агента/CI"
status: done
epic: v15-evidence-attestation
story: v15-nosdk-endpoint
complexity: simple
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "docs/{en,ru}/no-sdk-verify.md + tests/test_no_sdk_example.py"
scope_exclude: null
relevant_files:
  - "docs/en/no-sdk-verify.md"
  - "docs/ru/no-sdk-verify.md"
  - "tests/test_no_sdk_example.py"
scope_paths:
  - "docs/en/no-sdk-verify.md"
  - "docs/ru/no-sdk-verify.md"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T02:12:26Z"
---

## Goal

Документация no-SDK endpoint + рабочий пример вызова из не-Claude агента или CI-пайплайна (curl + минимальный скрипт). Снимает vendor lock-in для пользователей вне Claude Code/Qwen.

## Acceptance Criteria

1. docs/en/no-sdk-verify.md + RU-зеркало: quickstart (key init + serve), curl-примеры /verify и /receipt/verify и /key, CI-сниппет (GitHub Actions), trust-модель (fingerprint out-of-band). 2. Рабочий пример: python-клиент из дока существует как исполняемый тест tests/test_no_sdk_example.py и проходит против живого endpoint (порт 0). 3. Негативный: пример демонстрирует обработку ошибки (нет ключа 503 или fail-вердикт) и завершает CI с ненулевым кодом при fail. 4. pytest пример зелёный.

## Plan

## Rollback

git revert: только документация + один тест-пример

## Journal

- 2026-06-12T02:12:26Z [implementation] — AC verified: 1-4 OK см. лог.
- 2026-06-12T02:12:26Z [implementation] — AC-1: ✓ docs/en/no-sdk-verify.md + docs/ru/no-sdk-verify.md (quickstart/curl/trust-модель/GitHub Actions); AC-2: ✓ tests/test_no_sdk_example.py = документированный клиент, прогнан против живого endpoint (port 0); AC-3 Negative: ✓ test_red_verdict_exits_one + test_keyless_endpoint_exits_with_hint + test_rejected_request (exit с сообщением); AC-4: ✓ 4 passed + docs-тесты 40 passed
