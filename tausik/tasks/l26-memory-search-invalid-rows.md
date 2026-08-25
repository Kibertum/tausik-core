---
slug: l26-memory-search-invalid-rows
title: "memory_search возвращает схемно-невалидные строки (type cq, id 0)"
status: done
epic: landscape-2026-h2
story: l26-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/service_knowledge.py"
  - "harness/claude/mcp/project/handlers.py"
  - "scripts/project_cli_extra.py"
  - "tests/test_memory_cq_rows.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-18T11:05:04Z"
---

## Goal

service_knowledge.py:75-83 подмешивает кросс-проектные cq-результаты в выдачу memory_search как ФАЛЬШИВЫЕ строки: type=cq нарушает закрытый список схемы (pattern|gotcha|convention|context|dead_end, backend_schema.py:87), а id=0 коллидирует для каждого cq-хита. Любой вызывающий, который прогонит результат поиска обратно в memory_show/memory_link, сломается. Нужно: отдельная секция для cq-результатов вместо подмешивания в тот же список, либо явная пометка с непересекающимся id-пространством. Тест: round-trip результата memory_search в memory_show не падает.

## Acceptance Criteria

1. cq-строки больше не несут коллидирующий id=0: идентификатор отсутствует как адрес (None), добавлено явное поле source=cq для провенансности. 2. Обе точки рендера (MCP handler _do_memory_search и CLI memory search) отображают cq-строки корректно и НЕ ПАДАЮТ на отсутствующем идентификаторе. 3. Форма локальных результатов не изменилась — существующие потребители продолжают работать. 4. Построение cq-строки вынесено в чистую функцию, тестируемую без сетевого клиента. 5. НЕГАТИВНЫЙ СЦЕНАРИЙ: cq-строку нельзя принять за адресуемую локальную запись — round-trip такой строки в memory_show невозможен, потому что адреса нет, вместо указания на несуществующую запись номер ноль. 6. ruff чист; тесты зелёные на 3.11 и 3.13.

## Plan

## Rollback

git revert; формат ответа возвращается к прежнему

## Journal

- 2026-07-18T11:05:03Z [implementation] — AC-1: ✓ id=None вместо коллидирующего 0, добавлено source=cq — tests/test_memory_cq_rows.py::TestCqRowShape::test_row_carries_no_address и ::test_provenance_is_explicit. AC-2: ✓ обе точки рендера не падают и опускают адрес — tests/test_memory_cq_rows.py::TestRenderersTolerateMissingAddress::test_mcp_formatter_omits_address_for_cq; CLI проверен вживую, локальная запись отрисовалась как #214 [convention]. AC-3: ✓ форма локальных результатов не изменилась — tests/test_memory_cq_rows.py::TestRenderersTolerateMissingAddress::test_mcp_formatter_keeps_address_for_local; 260 тестов памяти зелёные. AC-4: ✓ построение вынесено в чистую build_cq_row, тестируется без сетевого клиента. AC-5: см. Negative. AC-6: ✓ ruff чист; 7 passed на 3.11 И 3.13. Negative: cq-строку нельзя принять за адресуемую локальную запись — tests/test_memory_cq_rows.py::TestCqRowShape::test_row_carries_no_address (id is None, не 0) и ::test_type_is_not_a_local_memory_type (тип не входит в VALID_MEMORY_TYPES, то есть кросс-проектное знание не выдаёт себя за своё); малформед-юнит из сети деградирует без исключения — ::test_missing_fields_do_not_raise. Domain: раньше вызывающий, прогнавший результат поиска обратно в memory_show, получал промах по несуществующей записи номер ноль, одинаковый для ВСЕХ cq-хитов; теперь отсутствие адреса явное и типизированное через source. Отдельно исправлено качество: первая версия рендера была написана обфусцированно через chr() с мёртвой веткой — переписана в именованную функцию _format_memory_hit. Checklist: scope соблюдён (service_knowledge + оба рендера + новый тест-файл), покрыты форма/провенанс/негатив/малформед, security surface нет, rollback = git revert.
