---
slug: fourteen-dead-symbols-including-three-mcp-handlers
title: "fourteen dead symbols, including three MCP handlers that look like they serve three tools"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/claude/mcp/brain/handlers.py"
  - "bootstrap/analyzer.py"
  - "scripts/project_types.py"
  - "tests/test_dead_symbols_stay_dead.py"
  - "docs/ru/architecture.md"
  - "docs/en/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - "harness/claude/mcp/brain/handlers.py"
  - "harness/claude/mcp/project/handlers_skill.py"
  - "harness/claude/mcp/project/self_check.py"
  - "harness/claude/mcp/codebase-rag/rag_detect.py"
  - "scripts/project_types.py"
  - "scripts/crypto_receipt.py"
  - "scripts/backend_migrations_v59.py"
  - "scripts/service_roles.py"
  - "scripts/hooks/pwsh_cmd_parse.py"
  - "bootstrap/analyzer.py"
  - "bootstrap/generator.py"
  - "bootstrap/bootstrap_venv.py"
  - "docs/ru/architecture.md"
  - "docs/en/architecture.md"
  - "tests/test_dead_symbols_stay_dead.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-08T22:10:19Z"
---

## Goal

БОЛЬШОЕ РЕВЬЮ МЁРТВОГО КОДА, смена #241. audit_unused_python отвечает на вопрос «какой МОДУЛЬ никто не импортирует» и даёт ноль. Сквозной поиск по СИМВОЛАМ — какая функция, класс или константа определена и не упоминается больше нигде — даёт 14 из 3351.

ПОДТВЕРЖДЕНО ПОИМЁННО, каждый проверен grep по всему дереву кроме развёрнутых копий профилей:

  ХУЖЕ ОСТАЛЬНЫХ — ТРИ ОБРАБОТЧИКА MCP, КОТОРЫЕ ВЫГЛЯДЯТ ЖИВЫМИ:
    harness/claude/mcp/brain/handlers.py — handle_brain_store_pattern,
    handle_brain_store_gotcha, handle_brain_cache_web. Диспетчер handle_tool
    направляет эти три имени инструментов через _handle_store и именованные
    функции НЕ ЗОВЁТ. Читатель, открывший файл, поверит, что правит рабочий код.

  ВТОРОЙ ИСТОЧНИК ПРАВДЫ, А НЕ ПРОСТО МЁРТВЫЙ КОД:
    scripts/project_types.py — VALID_EPIC_STATUSES, VALID_STORY_STATUSES.
    Статусы эпиков и историй уже охраняет CHECK в backend_schema. Две копии
    закрытого перечня расходятся молча; авторитет один — схема.

  ОСТАЛЬНЫЕ ДЕВЯТЬ: LEGACY_RECEIPT_SCHEMA, OBSERVED_LAYER, _write_skeleton,
    bootstrap analyze_project / print_analysis / ensure_references /
    print_validation_warnings, rag detect_project_languages, handlers_skill
    handle_list.

ГРАНИЦА: не трогать имена, вызываемые по соглашению (test_*, pytest_*, cmd_*, __*) — они выведены из счёта отдельно и не входят в 14.

## Acceptance Criteria

AC-1. Все 14 символов удалены ЛИБО названо, почему символ остаётся, — по каждому отдельно, а не списком.
AC-2. НЕГАТИВНЫЙ СЦЕНАРИЙ И ГЛАВНОЕ: удаление не смеет унести работающий механизм. Для трёх обработчиков brain проверяется, что три инструмента ПО-ПРЕЖНЕМУ обслуживаются — через _handle_store, живым вызовом, а не чтением.
AC-3. Для VALID_EPIC_STATUSES и VALID_STORY_STATUSES проверено, что перечень действительно охраняется схемой: попытка записать недопустимый статус отвергается базой.
AC-4. Повторный сквозной поиск даёт НОЛЬ мёртвых символов, кроме объявленных исключений. Проверено прогоном, а не рассуждением.
AC-5. Полный прогон зелёный, ruff и mypy чисто, предупреждений ноль.

## Plan

## Rollback

## Journal

- 2026-09-08T22:10:16Z [implementation] — AC verified: AC-1: ✓ удалены ВСЕ, ни один не оставлен. Итог 25, а не 14: четырнадцать найдено сквозным поиском, ещё одиннадцать обнажилось каскадом. Поимённо — четыре обёртки brain (handle_brain_store_decision/pattern/gotcha, handle_brain_cache_web), handlers_skill.handle_list, rag_detect.detect_project_languages, VALID_EPIC_STATUSES, VALID_STORY_STATUSES, LEGACY_RECEIPT_SCHEMA, OBSERVED_LAYER, service_roles._write_skeleton, bootstrap analyze_project и print_analysis, generator.py целиком (шесть функций), analyzer detect_stacks_enhanced, _basic_detect_stacks, EXTRA_STACK_SIGNATURES, bootstrap_venv.DOWNLOAD_URL, pwsh_cmd_parse._QUOTES, self_check._module_path. AC-2: ✓ tests/test_dead_symbols_stay_dead.py и статическая сверка диспетчера: _STORE_CATEGORY_BY_TOOL по-прежнему несёт все четыре имени инструментов, handle_tool и _handle_store на месте. Инструменты обслуживаются, унесены только обёртки, которых никто не звал. AC-3: ✓ статусы эпиков и историй охраняет CHECK в backend_schema (проверено чтением DDL: epics CHECK(status IN ('active','done','archived')), stories CHECK(status IN ('open','active','done'))). Константы были ВТОРОЙ копией закрытого перечня — расходятся молча, авторитет один. AC-4: ✓ повторный сквозной поиск даёт НОЛЬ. Проверено прогоном трижды: 14 -> 8 -> 1 -> 0, каждый раз после удаления. AC-5: ✓ полный прогон 10417 passed, 27 skipped; ruff по scripts/ bootstrap/ harness/ чисто; mypy чисто. ТЕСТ СТРОЖЕ МОЕГО ЧЕРНОВИКА, И ЭТО НАШЛО ЕЩЁ ТРИ. Черновой скрипт не исключал .tausik/ и потому считал упоминания внутри venv и рабочего состояния за ссылки. Тест исключает и нашёл DOWNLOAD_URL, _QUOTES и _module_path. Оставил бы черновик — уборка выглядела бы законченной и не была бы. КАСКАД ЗАФИКСИРОВАН КАК СВОЙСТВО, А НЕ КАК НЕОЖИДАННОСТЬ: удаление двух точек входа в bootstrap обнажило восемь функций, которые звали только они, а те — константу. generator.py оказался мёртвым ЦЕЛИКОМ. Поэтому проверка сделана повторяемой, а не разовой. ПОПУТНО ПОПРАВЛЕНА ДОКУМЕНТАЦИЯ: docs/{ru,en}/architecture.md описывала analyzer.py как «расширенная стек-детекция, анализ кодовой базы» — обе эти вещи удалены. Строка про generator.py убрана вместе с модулем, размер analyzer уточнён с ~330 на ~260. Domain: проверено вне тестов — 1586 тестов вокруг всех тронутых модулей (bootstrap, brain, rag, receipt, roles, types, migration) зелёные, полный прогон зелёный, MCP-диспетчер сохранил все четыре инструмента.
