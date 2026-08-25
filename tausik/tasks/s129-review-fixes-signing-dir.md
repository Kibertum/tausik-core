---
slug: s129-review-fixes-signing-dir
title: "Review-фиксы #129: signing project_dir из cwd вместо root + gate_changelog bool-коэрция"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: l26-signing-key-boundary
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
  - "docs/ru/architecture.md"
  - "docs/ru/receipts.md"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_task.py"
  - "scripts/service_gates.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "scripts/verify_run_record.py"
  - "tests/conftest.py"
  - "tests/test_cli_verify_guards.py"
  - "tests/test_tausik_service.py"
  - "tests/test_verify_receipt_emit.py"
  - "scripts/gate_changelog.py"
  - "tests/test_changelog_gate.py"
scope_paths:
  - "scripts/verify_run_record.py"
  - "scripts/gate_changelog.py"
  - "tests/test_verify_receipt_emit.py"
  - "tests/test_changelog_gate.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-22T19:58:28Z"
---

## Goal

Адверсариал-ревью фиксов сессии #129 (convention #276) нашёл HIGH: _project_has_key (project_cli_verify.py) резолвит project_dir через svc.tausik_dir() (от пути БД, cwd-independent), а реальный путь подписи emit_signed_receipt через record_run (verify_run_record.py:116) зовётся с project_dir='.' (cwd-relative — _record_verification не пробрасывает project_dir). Запуск verify|task done из ПОДКАТАЛОГА: подпись не находит ключ по './.tausik/keys' → тихо STATUS_NO_KEY (receipt не пишется), НО _project_has_key смотрит реальный root, находит ключ → ЛОЖНОЕ 'Receipt: WARNING signing failed' + ложное событие receipt_sign_failed. Ломает цель l26-signing-key-boundary в alt-cwd. Плюс латентный баг: подпись из подкаталога вообще не пишет receipt. Фикс: record_run резолвит project_dir от файла БД соединения (root=dirname(dirname(db_file)), как tausik_dir()). Бонус LOW: gate_changelog.py:64 bool(raw.get('enabled',False)) — строка 'false' коэрцится в True; читать через is True.

## Acceptance Criteria

AC1. record_run (verify_run_record.py) резолвит project_dir от файла БД соединения (project root = dirname(dirname(abspath(db_file))), как ProjectService.tausik_dir()), когда явный project_dir не передан — вместо cwd-relative '.'. Тест: _project_dir_from_conn(conn) для БД по пути <root>/.tausik/tausik.db возвращает <root>.
AC2 (негативный / устранение ложного срабатывания). При наличии ключа подпись больше НЕ зависит от cwd: emit_signed_receipt получает реальный root, поэтому verify из подкаталога пишет receipt (а не тихий no-key), и _emit_receipt печатает 'signed', НЕ ложное 'Receipt: WARNING'/событие receipt_sign_failed. Тест fails-then-passes: record_run зовёт emit_signed_receipt с project_dir=<derived-root>, не '.'.
AC3. gate_changelog enabled читается типобезопасно: config '"enabled": "false"' (JSON-строка) НЕ включает гейт (ловушка bool('false')==True). Тест: строка 'false' → (False, ...); не-bool значение не включает.
AC4 (fail-closed сохранён). Неразрешимый путь БД (in-memory/detached conn) → project_dir падает обратно на '.', emission остаётся best-effort (не падает).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert; record_run снова project_dir or '.'; gate_changelog снова bool(...)

## Journal

- 2026-07-22T19:58:26Z [implementation] — ROOT CAUSE (Rule 7): дефект read-path-divergence (класс mcp-config-read-paths) — два пути резолвили project_dir по-разному: _project_has_key от пути БД (tausik_dir, cwd-independent), а emit_signed_receipt через record_run — cwd-relative '.'. Расхождение проявлялось только при cwd != root (запуск из подкаталога). Причина: не единый источник резолва project-dir. PREVENTION: record_run теперь выводит root из файла соединения БД — тот же источник, что и tausik_dir; тест закрепляет. AC1 ✓ _project_dir_from_conn(conn) для <root>/.tausik/tausik.db → <root> (test_derives_root_from_db_file); record_run без project_dir передаёт derived root в emit (test_record_run_without_project_dir_uses_derived_root). AC2 ✓ end-to-end: keys в root, record_run без project_dir → receipt подписан и verify_receipt против root проходит (test_signs_against_db_root_end_to_end) — ложное WARNING устранено структурно. AC3 ✓ enabled='false' (строка) не включает гейт (test_string_false_does_not_enable, test_nonbool_truthy_does_not_enable); is True. AC4 ✓ in-memory conn → fallback '.' (test_inmemory_conn_falls_back_to_dot). Full suite 5374 passed. CHANGELOG.md+ru обновлены. Domain: подпись теперь находит ключ из любого cwd внутри проекта — реальный сценарий запуска CLI из подкаталога.
- 2026-07-22T19:58:56Z [done] — Root cause (integration-mismatch): новый observability-код (_project_has_key, DB-derived root) и старый signing-путь (record_run→emit, cwd-relative '.') резолвили project_dir из разных источников; расходились только при cwd≠root. Prevention: record_run выводит root из файла соединения БД — единый источник с tausik_dir; unit+e2e тесты закрепляют.
