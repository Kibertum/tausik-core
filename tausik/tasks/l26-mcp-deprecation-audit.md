---
slug: l26-mcp-deprecation-audit
title: "Аудит депрекаций MCP по всему дереву (sampling, logging, roots)"
status: done
epic: landscape-2026-h2
story: l26-mcp-spec
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_mcp_no_deprecated_primitives.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
scope_paths:
  - "tests/test_mcp_no_deprecated_primitives.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
scope_tools: []
depends_on: []
completed_at: "2026-07-20T13:02:23Z"
---

## Goal

Проверить, использует ли канонический MCP-тред harness/claude/mcp депрекируемые примитивы: sampling (sampling/createMessage — сервер занимает модель клиента), logging (заменяется на stderr либо OpenTelemetry), roots (roots/list). Для локальных stdio-серверов миграционная нагрузка по оценке спеки почти нулевая — вероятно, TAUSIK затронут мало, и задача закончится подтверждением. Но подтвердить нужно явно, а не предполагать. Дополнительно зафиксировать в памяти проекта: elicitation выживает только через Multi Round-Trip Requests (SEP-2322), новый цикл спеки не добавляет официальных транспортов, а Tasks понижен из экспериментального ядра в расширение.

## Acceptance Criteria

AC1. Поиск МЕХАНИЧЕСКИЙ, по всему дереву, с зафиксированным набором паттернов для трёх примитивов: sampling (sampling/createMessage, capability "sampling"), logging (logging/setLevel, notifications/message, capability "logging"), roots (roots/list, notifications/roots/list_changed, capability "roots"). Не «посмотрел глазами»: набор паттернов записан в коде проверки, иначе вывод невоспроизводим.
AC2. Каждое найденное вхождение КЛАССИФИЦИРОВАНО: объявление возможности нашим сервером / вызов, который мы делаем как клиент / упоминание в документации или комментарии. Это три разные миграционные нагрузки, и сводить их в одно число нельзя.
AC3. Вывод «не затронуто» закреплён ГЕЙТОМ, падающим при появлении депрекируемого примитива в нашем MCP-треде. Разовый вывод протухает на следующем коммите (конвенция #236); аудит без гейта — утверждение о вчерашнем дереве.
AC4. НЕГАТИВНЫЙ: гейт ПРОВЕРЕН внесённым вхождением, а не только написан. Гейт, никогда ничего не ловивший, — это гейт-гипотеза.
AC5. НЕГАТИВНЫЙ: гейт не выродился в пустышку — есть страховка, что он реально сканирует непустой набор файлов и что набор паттернов непуст.
AC6. Зафиксировано в памяти проекта: elicitation выживает только через Multi Round-Trip Requests (SEP-2322), новый цикл спеки не добавляет официальных транспортов, Tasks понижен из экспериментального ядра в расширение.
AC7. Результат записан так, чтобы l26-roots-premise-fix могла опереться на ЧИСЛО и список мест, а не на пересказ: сколько вхождений каждого класса и где именно.
AC8. ruff чист, полный pytest зелёный в обоих режимах, CHANGELOG EN+RU если добавлен гейт.

## Plan

## Rollback

git revert; отчёт и правки откатываются

## Journal

- 2026-07-20T12:43:53Z [implementation] — РЕЗУЛЬТАТ АУДИТА В ЧИСЛАХ (AC7 — чтобы l26-roots-premise-fix опиралась на замер, а не на пересказ). Область: 19 питоновских файлов MCP-треда в harness/ по трём серверам — project, brain, codebase-rag. Сканируется harness/, потому что это ИСТОЧНИК; профили .claude/.cursor/.kilo/.opencode из него генерируются, проверять их значило бы проверять копию. ЧИСЛА: - обращений к депрекируемому API (разбор AST): 0 - строк протокольного уровня в исходниках (sampling/createMessage, logging/setLevel, notifications/message, roots/list, notifications/roots/list_changed): 0 - объявляемых депрекируемых возможностей: 0 — проверено не текстом, а вызовом Server.get_capabilities(), который возвращает logging=None КЛАССИФИКАЦИЯ (AC2). Все три класса пусты в коде. Серверы регистрируют ровно четыре хендлера: list_tools, list_prompts, list_resources, call_tool. Возможности SDK выводит из зарегистрированных хендлеров, поэтому незарегистрированное и не объявляется — это и есть окончательный ответ, а не косвенный признак. Единственные текстовые вхождения слова roots по дереву — обычный английский, не протокол: «transcript roots» в docs/*/cli.md и ROOT_DOCS в scripts/audit_stale_docs.py. К MCP отношения не имеют. ВЫВОД ДЛЯ ПРЕМИСЫ. Оценка спеки («для локальных stdio-серверов нагрузка почти нулевая») подтверждена на нашем дереве: нагрузка РОВНО нулевая. Значит l26-roots-premise-fix — это работа по ТЗ будущих задач (gmcp-spike-roots, gmcp-project-resolver), а не миграция существующего кода. Мигрировать нечего. ЗАКРЕПЛЕНО ГЕЙТОМ (AC3), а не записано прозой: tests/test_mcp_no_deprecated_primitives.py, 12 тестов. Проверен внесённым использованием по всем трём примитивам (AC4) и отличает использование от УПОМИНАНИЯ в комментарии — иначе гейт падал бы на собственном докстринге и его отключили бы.
- 2026-07-20T13:02:22Z [implementation] — AC-1: ✓ Поиск механический, паттерны зафиксированы В КОДЕ проверки, а не выполнены глазами — tests/test_mcp_no_deprecated_primitives.py:_DEPRECATED_ATTRS (create_message/set_logging_level/send_log_message/list_roots) и :_DEPRECATED_WIRE (sampling/createMessage, logging/setLevel, notifications/message, roots/list, notifications/roots/list_changed). Имена API взяты ИНТРОСПЕКЦИЕЙ установленного пакета mcp (Server, ServerSession), а не выписаны из спеки по памяти. Проверено: ::TestTheGateIsNotHollow::test_the_pattern_sets_are_not_empty AC-2: ✓ Классификация трёх разных нагрузок разведена по разным проверкам: обращение к API (AST) — ::TestNoDeprecatedPrimitivesInUse::test_no_code_uses_a_deprecated_primitive; ручная сборка запроса строкой протокола — ::test_no_source_builds_a_deprecated_request_by_hand; ОБЪЯВЛЕНИЕ возможности сервером — ::test_the_server_advertises_none_of_them (проверяет не наш текст, а фактический Server.get_capabilities(), logging=None). Упоминание в комментарии/доке отделено от использования — ::TestTheGateActuallyCatchesUsage::test_a_mention_in_a_comment_is_not_a_usage AC-3: ✓ Вывод «не затронуто» закреплён гейтом tests/test_mcp_no_deprecated_primitives.py (12 тестов), а не записан прозой. Без него вывод протух бы на следующем коммите (конвенция #236). AC-4: ✓ НЕГАТИВНЫЙ: гейт проверен ВНЕСЁННЫМ использованием по всем трём примитивам и по обеим формам (вызов и декоратор) — ::TestTheGateActuallyCatchesUsage::test_a_planted_call_is_caught (4 параметра: create_message/sampling, list_roots/roots, send_log_message/logging, @server.set_logging_level/logging), ::test_a_planted_wire_string_is_caught AC-5: ✓ НЕГАТИВНЫЙ: гейт не пустышка — ::TestTheGateIsNotHollow::test_the_scan_finds_our_actual_servers (>=5 файлов, server.py на месте), ::test_the_pattern_sets_are_not_empty (множество примитивов ровно {sampling, logging, roots}), ::test_the_ast_scanner_parses_real_code (разбор находит заведомо присутствующее имя call_tool — страховка от обхода, молча возвращающего пустоту) AC-6: ✓ Зафиксировано в памяти проекта — memory #255 (context): elicitation выживает только через Multi Round-Trip Requests (SEP-2322), новый цикл спеки не добавляет официальных транспортов, Tasks понижен из экспериментального ядра в расширение, плюс stateless-ядро (SEP-2575/SEP-2567) как довод за мульти-тенантность. AC-7: ✓ Результат записан ЧИСЛАМИ и адресами, а не пересказом — журнал задачи: 19 питоновских файлов MCP-треда, три сервера (project, brain, codebase-rag), 0 обращений к депрекируемому API, 0 строк протокола, 0 объявляемых возможностей. Названы и единственные текстовые вхождения слова roots по дереву (docs/*/cli.md «transcript roots», scripts/audit_stale_docs.py ROOT_DOCS) — обычный английский, к протоколу отношения не имеет. l26-roots-premise-fix может опереться на это прямо. AC-8: ✓ ruff check — All checks passed; ruff format --check — 1 file already formatted. Полный pytest зелёный в ОБОИХ режимах: 5046 passed / 21 skipped / 0 failed обычный и 5046 passed / 21 skipped / 0 failed под -X utf8. CHANGELOG.md + CHANGELOG.ru.md обновлены. constants.json и README регенерированы (5193 -> 5205 тестов, сходится с 5046+21+138). Доказательство: verification_run #1088, receipt подписан, БЕЗ предупреждения о недекларированных файлах — объявленная область провабельно полная. Negative: упоминание депрекируемого имени в докстринге/комментарии НЕ считается использованием (иначе гейт падал бы на собственной документации, и его отключили бы — отключённый гейт хуже отсутствующего, потому что выглядит защитой); разбор AST проверен на заведомо присутствующем имени, чтобы «ничего не найдено» нельзя было спутать со «сломанным обходом». Domain: возможности MCP-сервера не пишутся руками — SDK выводит их из ЗАРЕГИСТРИРОВАННЫХ хендлеров. Поэтому окончательный ответ на вопрос «объявляем ли мы депрекируемое» даёт вызов get_capabilities(), а не чтение исходника. Депрекация SEP-2577 annotation-only с гарантией >=12 месяцев — это не миграция под срок. Checklist: сканируется harness/ как ИСТОЧНИК, а не сгенерированные профили .claude/.cursor/.kilo/.opencode — проверять копию значило бы повторить ровно тот класс дефекта, против которого написан соседний гейт паритета DDL; вывод аудита закреплён механически; предположение спеки («нагрузка почти нулевая») подтверждено замером, а не принято на веру.
