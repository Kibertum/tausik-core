---
slug: v14b-doc-gen-mcp-tool-counts
title: "B6 follow-up: gen_doc_constants extension — MCP tool count cross-file consistency"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/gen_doc_constants.py, tests/test_gen_doc_constants.py, docs/_generated/constants.json, README.md, AGENTS.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/audit_translation_drift.py, scripts/docs_lint.py, agents/claude/mcp/project/tools*.py, agents/claude/mcp/brain/tools.py, .claude/* (generated)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T21:57:47Z"
---

## Goal

Расширить scripts/gen_doc_constants.py: посчитать реальное число MCP tools (project + brain) через импорт TOOLS/TOOLS_EXTRA, записать в constants.json, добавить cross-file scanner проверяющий упоминания "(N) tools" / "project: N tools" / "N project tools" / "N brain tools" в README/AGENTS/CLAUDE/docs/architecture.md/docs/mcp.md против constants. Исправить найденные дрифты (README:106, AGENTS:96 → consistent). Закрывает deferred TODO из v14b-doc-gen-cross-files.

## Acceptance Criteria

1. scripts/gen_doc_constants.py при --check (а также при --update) считает реальное число MCP tools: project = len(tools.TOOLS) + len(tools_extra.TOOLS_EXTRA) (+ admin_tools если применимо); brain = len(tools.TOOLS) из brain MCP. Импорт через sys.path добавление agents/claude/mcp/project и agents/claude/mcp/brain (паттерн как в tests/test_mcp_integration.py).
2. constants.json получает 3 новых ключа: `mcp_project_tools`, `mcp_brain_tools`, `mcp_total_tools = project + brain`. Существующая схема (tausik_version, ...) сохраняется.
3. Cross-file scanner расширен: ищет паттерны `(\d+)\s+(?:MCP\s+)?(?:project\s+)?tools?` и `project:\s*(\d+)\s+tools` и `(\d+)\s+tools\s+for\s+AI\s+agents` в 6+ doc файлах (README.md, README.ru.md, AGENTS.md, CLAUDE.md, docs/en/architecture.md, docs/ru/architecture.md, docs/en/mcp.md, docs/ru/mcp.md). При drift report file:line + found vs expected.
4. False-positive guard: skip fenced code blocks (как в version-ref scanner и audit_translation_drift). Skip контексты не относящиеся к MCP tools (например "TOOL CALLS" budget, тестовые "26+ tools").
5. Новый CLI флаг `--skip-mcp-counts` опт-аут (preserves существующий version-ref check + single-file constants check).
6. tests/test_gen_doc_constants.py: +5 новых тестов: (a) scanner находит drift project count; (b) scanner находит drift brain count; (c) scanner clean при match; (d) скип fenced code; (e) `--skip-mcp-counts` отключает только этот check.
7. Драйфы исправлены: README.md:158 "106 tools" → корректное значение; AGENTS.md:93 "96 tools" → корректное; tests/test_mcp_integration.py "26+" → актуальное minimum (или удалить устаревшую проверку — на ваше усмотрение).
8. CHANGELOG.md + CHANGELOG.ru.md entry под Unreleased v1.4.0 polish Phase B.
9. Negative: pytest full suite green; ruff + mypy clean; pre-commit gates pass; existing v14b-doc-gen-cross-files behavior сохраняется (старые тесты untouched).
10. NOT in scope: `test_count` через `pytest --collect-only` (отдельный TODO #4); skill count cross-check; hooks count cross-check.

## Plan

## Rollback

## Journal

- 2026-05-06T21:57:47Z [implementation] — AC verified: 1+2 already in place (mcp_tool_counts.py + constants.json keys mcp_project_tools=93/mcp_brain_tools=7/mcp_main_tools=100 from prior task). 3. scan_mcp_tool_counts: walks 8 targets (added docs/en/mcp.md + docs/ru/mcp.md), 4 single-key patterns + pair pattern, RU/EN-aware via tools?|инструмент(а|ов)?, fenced-code stripped. 4. False-positive guard: brain-header tightly anchored to backtick-wrapped tausik-brain server name; project/brain count requires literal token; bold-main pattern requires both ** delimiters with optional MCP[-\s]+ prefix. 5. CLI --skip-mcp-counts isolates the new check (preserves version-ref scan); --skip-cross-files still skips both. 6. Tests: +6 cases all PASSED (clean-when-all-match, brain-header drift, project drift, project+brain pair drift, fenced-code skip, --skip-mcp-counts isolation). 7. Real drift fixed: docs/en/mcp.md:226 6 tools→7, docs/ru/mcp.md:226 6 инструментов→7, brain_draft_artifact row added to both tables, trailing 'is 6'→'is 7' prose corrected; +2 legacy 'as in v1.3' refs neutralized to 'pre-v1.4 releases'/'релизах до v1.4'. 8. CHANGELOG.md + CHANGELOG.ru.md entries added at top of Unreleased v1.4.0 polish Phase B Added section. 9. Verify: pytest 16/16 gen_doc + 21/21 audit_drift PASSED; ruff All checks passed; mypy Success no issues. translation_drift_audit: 'No structural drift detected on paired mirrors'; gen_doc_constants --check: OK. 10. NOT in scope respected: test_count + skill/hooks counts остаются follow-up.
