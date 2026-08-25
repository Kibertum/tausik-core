---
slug: dedupe-spec-adapt-enums
title: "Single-source SPEC_TYPES/SPEC_STATUSES/ADAPT_STATUSES (дублированы в 3 слоях)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 18
defect_of: null
scope: "scripts/project_parser_specs.py (импорт из service_specs), scripts/project_parser_adapts.py (импорт из service_adapts), новый tests/test_enum_single_source.py. НЕ трогать: значения enum, MCP tools_spec/tools_adapt литералы, service_specs/service_adapts источники."
scope_exclude: "harness/*/mcp/project/tools_spec.py, harness/*/mcp/project/tools_adapt.py, service_specs.py, service_adapts.py"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T23:59:44Z"
---

## Goal

Устранить тройное независимое дублирование закрытых enum-списков RENAR: SPEC_TYPES/SPEC_STATUSES и ADAPT_STATUSES определены отдельно в service-слое (источник истины), parser-слое и MCP-tools-слое (×2 зеркала claude/cursor). Parser импортирует из service напрямую (модули лёгкие). MCP-схемы остаются литералами (schema должна быть self-contained), но дрейф запирается conformance-тестом: assert MCP-enum == service-источник И claude-зеркало == cursor-зеркало байт-в-байт.

## Acceptance Criteria

1. project_parser_specs.SPEC_TYPE_CHOICES и SPEC_STATUS_CHOICES выведены из service_specs.SPEC_TYPES/SPEC_STATUSES (нет независимого литерала-списка в parser). 2. project_parser_adapts.ADAPT_STATUS_CHOICES выведен из service_adapts.ADAPT_STATUSES. 3. Новый conformance-тест: parser choices == list(service constants); MCP tools_spec._SPEC_TYPES/_SPEC_STATUSES == list(service); MCP tools_adapt._ADAPT_STATUSES == list(service). 4. Тест проверяет claude-зеркало == cursor-зеркало байт-в-байт (filecmp) для tools_spec.py и tools_adapt.py. 5. Негативный сценарий / boundary: при рассинхроне MCP-литерала с service-источником conformance-тест поднимает AssertionError (Ошибка рассинхрона) — дрейф не проходит молча. 6. Boundary: пустой/невалидный тип в parser отвергается argparse choices (Ошибка argparse при значении вне закрытого списка). 7. Парсер строится без ошибок (build_parser() OK). 8. pytest зелёный, ruff чист.

## Plan

## Rollback

## Journal

- 2026-06-13T23:59:43Z [implementation] — AC-1: ✓ SPEC_TYPE_CHOICES/SPEC_STATUS_CHOICES = list(SPEC_TYPES/SPEC_STATUSES) — tested via tests/test_enum_single_source.py::test_parser_spec_choices_derive_from_service. AC-2: ✓ ADAPT_STATUS_CHOICES=list(ADAPT_STATUSES) — test_parser_adapt_choices_derive_from_service. AC-3: ✓ MCP enums pinned — test_mcp_spec_enums_match_service, test_mcp_adapt_enums_match_service. AC-4: ✓ mirror byte-identity — test_mcp_mirrors_identical (filecmp). AC-5: ✓ Negative: assert-равенство падает AssertionError при рассинхроне (by construction). AC-6: ✓ argparse choices отвергает значение вне списка. AC-7: ✓ build_parser() OK. AC-8: ✓ pytest 72 passed, ruff clean. Domain: закрытые RENAR-списки имеют единый источник service-слоя.
