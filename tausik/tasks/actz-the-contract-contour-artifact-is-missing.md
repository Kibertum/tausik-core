---
slug: actz-the-contract-contour-artifact-is-missing
title: "ACTZ — протокол уточнения ТЗ: контрактного артефакта нет вовсе"
status: done
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: "Новая сущность ACTZ: schema (новая миграция backend_migrations_v52.py + backend_schema_actz.py), сервисный слой (service_actz.py, backend_crud_actz.py, actz_closed_lists.py), CLI parser wiring (правки в существующих project_parser*.py/project_cli*.py — только добавление actz-веток, не рефакторинг соседних), MCP (harness/claude/mcp/project/tools_actz.py + регистрация в существующем реестре инструментов), тесты (tests/test_actz.py), docs/ru/cli.md и docs/en/cli.md (новый раздел ACTZ), CHANGELOG.md и CHANGELOG.ru.md."
scope_exclude: "Существующая сущность adapt (schema/service/CLI/MCP/тесты) не меняется, кроме точки регистрации нового actz-подкоманды в общем парсере/реестре MCP. Схема ГРАФА артефактов (ag-*, artifact-graph эпик) не трогается — отдельная задача. Клиентская идентичность/аттестация (separation-of-duties) не решается здесь."
relevant_files:
  - "scripts/actz_closed_lists.py"
  - "scripts/backend_schema_actz.py"
  - "scripts/backend_migrations_v52.py"
  - "scripts/backend_crud_actz.py"
  - "scripts/service_actz.py"
  - "scripts/project_parser_actz.py"
  - "scripts/project_cli_actz.py"
  - "scripts/backend_init.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/project_backend.py"
  - "scripts/project_service.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "scripts/renar_tc_premise.py"
  - "harness/claude/mcp/project/tools_actz.py"
  - "harness/claude/mcp/project/handlers_actz.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/mcp/project/handlers.py"
  - "tests/test_actz.py"
  - "tests/test_mcp_tool_token_cost.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - pyproject.toml
  - "tausik/gates.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - AGENTS.md
  - README.md
  - README.ru.md
  - ROADMAP.md
  - "docs/README.md"
  - "docs/_generated/constants.json"
  - "docs/en/architecture.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/agent-contract.md"
  - "docs/ru/architecture.md"
  - "docs/ru/senar-compliance-matrix.md"
scope_paths: []
scope_tools: []
depends_on:
  - four-accepted-adrs-were-never-assessed
completed_at: "2026-09-06T17:15:35Z"
---

## Goal

RENAR §5A (ADR-011, accepted) вводит ACTZ — артефакт контрактного контура: протокол уточнения ТЗ с двусторонней подписью, контрактным весом и жизненным циклом draft → sent → signed → superseded. Кардинальность 0..N на ТЗ и 1..N на ADAPT. Поздний протокол, оформленный после демонстрации, есть ШТАТНЫЙ случай, а не исключение. Договорное имя — «Протокол уточнения ТЗ № N»; слово «акт» в корпусе запрещено и зарезервировано за документами сдачи-приёмки, значит наш вывод не имеет права его печатать. У нас этого артефакта нет ни в схеме, ни в CLI, ни в MCP. Задача: завести сущность с жизненным циклом и подписями по образцу существующего adapt (ed25519 уже есть, изобретать подпись не надо), плюс ребро decided-in от обратной находки ADAPT на пункт подписанного ACTZ. НЕГАТИВНОЕ ограничение: ADR-017 «односторонняя приёмка» имеет статус proposed и задевает именно двустороннюю подпись. Реализовать двусторонность так, чтобы односторонний случай позже добавлялся, а не ломал сделанное — но САМ односторонний случай сейчас НЕ реализовывать (решение #255).

## Acceptance Criteria

AC-1 Схема: новая сущность ACTZ (таблица(ы), отдельная от adapt) со статусами draft→sent→signed→superseded из ОДНОГО closed-list источника (actz_closed_lists.py, не литерал в 3 местах). Точки уточнения — actz_points (нумерованные пункты протокола), кардинальность 1..N ADAPT-находок на ОДИН пункт ACTZ через ребро decided-in с provenance (linked_by, created_at) — новая таблица, adapt_links провенанса не несёт. Связь ACTZ↔SPEC/ТЗ 0..N (actz_links, по образцу adapt_links). Имя записи в выводе строго "Протокол уточнения ТЗ № {id}"; слово "акт" не встречается нигде в CLI help/MCP docstrings/docs этой сущности (guard-тест на словоформы "акт/акта/акту/актом/акте/акты/актов/актам/актами/актах" с границей слова на КОНЦЕ, что естественно не задевает "актив"/"фактор"/"контракт" — без ручного allowlist).
AC-2 Подписи (один project-ключ на проект, не по ролям): role=architect подписывает РЕАЛЬНЫМ ed25519 (project.key, как adapt). role=client пишет ТОЛЬКО signed_by+signed_at, БЕЗ signature/key_fingerprint (честная запись согласия, не имитация независимой криптоподписи). Статус вычисляется по покрытию ролей: 0 подписей=draft, 1=sent, обе роли=signed — не пишется отдельным полем. Односторонний путь (ADR-017, proposed) СЕЙЧАС не реализуется и не достижим ни через CLI, ни через MCP.
AC-3 CLI+MCP, ПОЛНЫЙ паритет: `tausik actz {create,sign,verify,show,list,delta,link,unlink,delete,search,decided-in,decided-in-remove}` по образцу adapt (тонкий парсер → общий сервисный слой, delta обязателен — иначе parent_actz/delta_n/supersession_rationale в схеме мертвы); MCP tausik_actz_* — чистый транспорт.
AC-4 Позднее оформление: ACTZ, датированный позже других задач/ADAPT, штатный путь, не аномалия — тест это фиксирует явно.
AC-5 Качество: tests/test_actz.py по структуре test_adapts.py; mypy/ruff/filesize(≤500 на новый файл)/bootstrap --check зелёные; class_surface baseline (tausik/gates.json) обновлён под новый композитный размер ProjectService/SQLiteBackend решением, не тихо; мутации на статус-переходе и "акт"-страже убиты/эквивалентны; docs/{en,ru}/mcp.md получают раздел ACTZ (по прецеденту adapt, не cli.md); оба CHANGELOG обновлены; миграция v52 — единый источник statements, переиспользуемый и fresh-DB, и migration-путём.
AC-6 Негатив: одна подпись не даёт статус signed; client-подпись без signed_by отклоняется; повторная architect-подпись после signed отклоняется; decided-in на НЕподписанный (draft/sent) пункт ACTZ отклоняется явной ошибкой (§ смысл ребра — точка должна быть контрактно зафиксирована).
AC-7 Стожившийся дефект docs/{en,ru}/mcp.md (строка adapt_sign описывает withdrawn dual-signature) НЕ чинится здесь — заведён отдельной задачей mcp-doc-adapt-sign-row-still-describes-withdrawn-dual-signature.

## Plan

[{"step": "\u0414\u043e\u0436\u0434\u0430\u0442\u044c\u0441\u044f \u043a\u0430\u0440\u0442\u044b \u0440\u0435\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u0438 adapt (\u0441\u0445\u0435\u043c\u0430/\u0441\u0435\u0440\u0432\u0438\u0441/CLI/MCP/\u0442\u0435\u0441\u0442\u044b) \u043a\u0430\u043a \u043e\u0431\u0440\u0430\u0437\u0446\u0430", "done": true}, {"step": "\u0421\u043f\u0440\u043e\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0445\u0435\u043c\u0443 ACTZ: \u043c\u0438\u0433\u0440\u0430\u0446\u0438\u044f v52, closed lists (\u0441\u0442\u0430\u0442\u0443\u0441, \u0440\u043e\u043b\u0438 \u043f\u043e\u0434\u043f\u0438\u0441\u0430\u043d\u0442\u043e\u0432), \u0442\u0430\u0431\u043b\u0438\u0446\u0430 \u043f\u043e\u0434\u043f\u0438\u0441\u0435\u0439 N-of-M, \u0440\u0435\u0431\u0440\u043e decided-in \u0441 provenance, \u0441\u0432\u044f\u0437\u044c ACTZ<->SPEC/\u0422\u0417 (0..N)", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c backend_schema_actz.py + backend_migrations_v52.py + actz_closed_lists.py", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c backend_crud_actz.py + service_actz.py (create/sign/verify/show/list/link/unlink/delete/search, \u0441\u0442\u0430\u0442\u0443\u0441 signed \u0432\u044b\u0447\u0438\u0441\u043b\u044f\u0435\u0442\u0441\u044f)", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c CLI wiring (\u043f\u0430\u0440\u0441\u0435\u0440 + \u0434\u0438\u0441\u043f\u0435\u0442\u0447)", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c MCP harness/claude/mcp/project/tools_actz.py \u043a\u0430\u043a \u0442\u0440\u0430\u043d\u0441\u043f\u043e\u0440\u0442 \u043d\u0430\u0434 service_actz", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c '\u0430\u043a\u0442'-\u0441\u0442\u0440\u0430\u0436 (\u0441\u043a\u0430\u043d\u0438\u0440\u0443\u0435\u0442 CLI help/MCP docstrings/docs) \u0438 \u0442\u0435\u0441\u0442 AC-6 (\u043d\u0435\u0433\u0430\u0442\u0438\u0432: \u043e\u0434\u043d\u0430 \u043f\u043e\u0434\u043f\u0438\u0441\u044c \u043d\u0435 \u0434\u0430\u0451\u0442 signed)", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c tests/test_actz.py \u043f\u043e \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0435 test_adapts.py (lifecycle, \u043f\u043e\u0434\u043f\u0438\u0441\u0438, decided-in, \u043f\u043e\u0437\u0434\u043d\u0435\u0435 \u043e\u0444\u043e\u0440\u043c\u043b\u0435\u043d\u0438\u0435 AC-4)", "done": true}, {"step": "\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u044f: docs/ru/cli.md, docs/en/cli.md, CHANGELOG.md, CHANGELOG.ru.md", "done": true}, {"step": "\u041c\u0443\u0442\u0430\u0446\u0438\u043e\u043d\u043d\u043e\u0435 \u0442\u0435\u0441\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0441\u0442\u0430\u0442\u0443\u0441-\u043f\u0435\u0440\u0435\u0445\u043e\u0434\u0430 \u0438 '\u0430\u043a\u0442'-\u0441\u0442\u0440\u0430\u0436\u0430; \u0443\u0431\u0438\u0442\u044c \u043c\u0443\u0442\u0430\u043d\u0442\u043e\u0432 \u0438\u043b\u0438 \u043e\u0431\u044a\u044f\u0432\u0438\u0442\u044c \u044d\u043a\u0432\u0438\u0432\u0430\u043b\u0435\u043d\u0442\u043d\u044b\u043c\u0438 \u0432 \u0438\u0441\u0445\u043e\u0434\u043d\u0438\u043a\u0435", "done": true}, {"step": "\u041f\u043e\u043b\u043d\u044b\u0439 \u043f\u0440\u043e\u0433\u043e\u043d: mypy/ruff/filesize/bootstrap --check/\u043c\u0438\u0433\u0440\u0430\u0446\u0438\u044f fresh==migrated; verify --task; \u0437\u0430\u043a\u0440\u044b\u0442\u044c \u0437\u0430\u0434\u0430\u0447\u0443", "done": true}]

## Rollback

Новая сущность со своей таблицей и миграцией. Откат: обратная миграция плюс git revert; существующие ADAPT не затрагиваются, потому что ребро decided-in ДОБАВЛЯЕТСЯ, а не заменяет имеющиеся связи.

## Journal

- 2026-09-06T16:26:36Z [implementation] — QG-0 пройден: AC (6 пунктов), scope и scope_exclude записаны, план из 11 шагов установлен. Explore-агент запущен фоном для карты реализации adapt (схема/сервис/CLI/MCP/тесты) как образца.
- 2026-09-06T17:08:40Z [implementation] — AC verified: 1. ✓ Схема ACTZ+points+signatures+links+decided_in, closed lists в actz_closed_lists.py, "акт"-guard регекс без allowlist (test_forbidden_word_regex_*), 0..N ACTZ↔SPEC/task, 1..N ADAPT-находок на пункт. 2. ✓ architect=реальный ed25519 (test_architect_signature_is_real_ed25519_and_verifies), client=signed_by+signed_at без crypto (test_client_signature_has_no_signature_or_fingerprint), статус draft/sent/signed вычисляется (мутации M1-M3 убиты), односторонний путь недостижим. 3. ✓ CLI 13 подкоманд + MCP 13 инструментов, полный паритет (test_mcp_dispatch_registers_all_actz_tools_full_parity, test_mcp_tool_schema_matches_handler_set). 4. ✓ test_late_actz_after_other_work_is_not_flagged. 5. ✓ test_actz.py 54 теста; mypy 390 файлов Success; ruff чист; filesize все новые файлы <500 (max 383); class_surface baseline поднят (decision #327) и покрыт test_gate_class_surface.py; мутации M1-M6 объявлены и убиты (M6 вскрыл реальный пробел покрытия — суффикс "ов" — закрыт test_forbidden_word_regex_covers_every_declension_suffix, не объявлен эквивалентным); docs/{en,ru}/mcp.md получили раздел ACTZ (13); оба CHANGELOG обновлены; миграция v52 — единый источник ACTZ_STATEMENTS. 6. ✓ test_one_signature_does_not_reach_signed, test_client_signature_without_signed_by_rejected, test_resign_architect_after_signed_rejected, test_decided_in_requires_signed_actz. 7. ✓ Стожившийся дефект mcp.md (adapt_sign row) заведён отдельно: mcp-doc-adapt-sign-row-still-describes-withdrawn-dual-signature. Полный прогон 9242 passed/27 skipped, bootstrap --check чист.
- 2026-09-06T17:15:45Z [done] — Domain: signed=True valid=True on a real ed25519 keypair, verified end-to-end (sign→verify roundtrip against the canonical body, not a mocked crypto call) — the result is a real cryptographic signature usable outside the test harness, not a stub. Negative: AC-6 exercised directly — one signature does not reach signed (test_one_signature_does_not_reach_signed), client-sign without signed_by is refused (test_client_signature_without_signed_by_rejected), re-signing after signed is refused (test_resign_architect_after_signed_rejected), decided-in against a draft/sent point is refused (test_decided_in_requires_signed_actz) — plus 6 hand-run mutations (M1-M6) on the status-transition logic and the "акт" guard, all killed; M6 found and closed a real coverage gap (missing "-ов" suffix case) rather than being declared equivalent.
