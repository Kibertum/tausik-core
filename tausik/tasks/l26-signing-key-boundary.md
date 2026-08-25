---
slug: l26-signing-key-boundary
title: "Ключ подписи лежит рядом с агентом, которого он аудирует"
status: done
epic: landscape-2026-h2
story: l26-trust-boundary
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/en/receipts.md"
  - "docs/ru/agent-contract.md"
  - "docs/ru/receipts.md"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_task.py"
  - "scripts/service_gates.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "tests/conftest.py"
  - "tests/test_cli_verify_guards.py"
  - "tests/test_tausik_service.py"
  - "scripts/gate_changelog.py"
  - "tests/test_changelog_gate.py"
scope_paths:
  - "scripts/project_cli_verify.py"
  - "scripts/verify_receipt_emit.py"
  - "docs/ru/receipts.md"
  - "docs/ru/agent-contract.md"
  - "docs/en/receipts.md"
  - "tests/test_cli_verify_guards.py"
  - "tests/test_verify_receipt_emit.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-22T19:05:15Z"
---

## Goal

Приватный seed лежит в .tausik/keys/project.key в рабочем дереве, mode 0600 best-effort на POSIX и no-op на Windows (crypto_keys.py:79-84). Агент, чью отчётность подписывает ключ, имеет к нему доступ на чтение. Значит receipt доказывает someone with filesystem access produced this — то есть tamper-evidence против ВНЕШНИХ правок tausik.db, но НЕ attestation против агента. То же касается подписи events_anchor. С учётом EU AI Act (обязательства по логированию для high-risk вступают в силу в августе 2026) формулировка того, что именно доказывает подпись, становится юридически значимой. Варианты: ключ вне рабочего дерева и вне зоны записи агента (managed-путь, keychain, отдельный процесс-подписант) либо честная документация границы. Смежно: emit_signed_receipt глотает любое исключение в STATUS_ERROR (verify_receipt_emit.py:98-100) — проект, где подпись всегда молча падает, деградирует до неподписанных прогонов.

## Acceptance Criteria

AC1. В docs (architecture/agent-contract) явно задокументировано, что именно доказывает подпись receipt и events_anchor: tamper-evidence против ВНЕШНИХ правок tausik.db, но НЕ attestation против агента, имеющего доступ на чтение рабочего дерева. Формулировка не оставляет двусмысленности с учётом обязательств EU AI Act (август 2026).
AC2. Реализован ЛИБО вынос приватного seed за пределы зоны записи агента (managed-путь / keychain / отдельный процесс-подписант), ЛИБО задокументирована граница с обоснованием, почему вынос отложен. Выбранный вариант зафиксирован через tausik decide.
AC3. emit_signed_receipt больше не глотает исключение молча в STATUS_ERROR (verify_receipt_emit.py:98-100): при сбое подписи прогон помечается наблюдаемым предупреждением/метрикой, а не тихо деградирует до неподписанного. Тест fails-then-passes: смоделированный сбой подписи фиксируется видимо.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; ключ снова только в .tausik/keys/project.key

## Journal

- 2026-07-22T19:01:42Z [implementation] — Noted pre-existing (in HEAD) mypy error: project_cli_verify.py _emit_cache_hit arg2 task_slug str|None vs str — out of this task's scope (signing boundary), left for a typing-cleanup task; mypy not in verify gate set so non-blocking.
- 2026-07-22T19:05:13Z [implementation] — AC1 ✓ docs/{ru,en}/receipts.md новый раздел «граница ключа»: подпись = tamper-evidence против ВНЕШНИХ правок tausik.db, НЕ attestation против агента (seed в рабочем дереве, читаем агентом); EU AI Act авг.2026 framing; agent-contract.md кросс-ссылка. AC2 ✓ Decision #163 — вынос ключа отложен как отдельный key-custody дизайн, граница задокументирована с обоснованием. AC3 ✓ сбой подписи наблюдаем: _emit_receipt различает 'ключ есть но подпись упала' (Receipt: WARNING + счётное событие receipt_sign_failed) от 'нет ключа' (безобидно); тесты fails-then-passes TestReceiptSignFailureIsObservable + TestProjectHasKeyDetection (6 новых, 28 в файле passed). CHANGELOG.md + CHANGELOG.ru.md обновлены прозой.
