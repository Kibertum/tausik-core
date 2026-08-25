---
slug: v15p-memory-lint
title: "[P1] T5: memory lint — противоречия и устаревшие факты"
status: done
epic: v15-polish
story: v15p-agent-ux
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/memory_cleanup.py (pure find_lint_candidates: contradicts/superseded/stale_file). scripts/service_knowledge_hygiene.py (lint_memory orchestration + apply=archive superseded). scripts/service_knowledge.py (делегатор memory_lint в KnowledgeMixin). scripts/project_cli_extra.py + project_parser.py (сабкоманда memory lint, dry-run default, --apply). harness/claude/mcp/project/{tools.py,handlers.py} (tausik_memory_lint). tests/test_memory_lint.py."
scope_exclude: "backend_graph.py edge_list (используем как есть), memory_dedupe/archive существующая логика, version-staleness эвристика (оставляем LLM-проходу — чистая эвристика по версиям шумит)"
relevant_files:
  - "scripts/memory_cleanup.py"
  - "scripts/service_knowledge_hygiene.py"
  - "scripts/backend_graph.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T09:56:22Z"
---

## Goal

Команда `tausik memory lint` (+MCP): поиск противоречий и устаревших записей в памяти (паттерн Karpathy second brain — лёгкий LLM-линтинг вместо тяжёлого RAG; отчёт T5). Использует существующий граф (contradicts/supersedes) + эвристики (упоминание несуществующих файлов/версий) + опциональный LLM-проход. AC: lint выдаёт список кандидатов с причиной; dry-run по умолчанию; интеграция с memory archive; тесты на фикстурах.

## Acceptance Criteria

1. find_lint_candidates выдаёт список кандидатов с reason+kind: contradicts (пара по графу), superseded (target активен), stale_file (упоминание несуществующего пути). 2. Dry-run по умолчанию (lint только репортит); --apply архивирует только superseded-кандидатов через memory archive. 3. CLI `tausik memory lint` работает; MCP tausik_memory_lint паритет. 4. Ошибка/boundary: пустая память -> []; путь, который существует -> не флагается; archived записи исключены; битый edge (несуществующий узел) не падает. 5. pytest на фикстурах: каждый детектор + dry-run/apply + пустой кейс.

## Plan

## Rollback

git revert коммита; удалить memory_lint-функции + CLI/MCP сабкоманды. Существующие memory-команды не менялись, миграций нет.

## Journal

- 2026-06-13T09:54:16Z [implementation] — find_lint_candidates: contradicts/superseded (граф edges) + stale_file (regex путей vs file_exists). lint_memory оркестрация: dry-run default, --apply архивит ТОЛЬКО superseded (memory_archive_ids). CLI memory lint + MCP tausik_memory_lint (счётчик 96->97, регенерация + починка 11 doc-ссылок 103->104/96->97/110->111). version-staleness -> LLM-проходу (шумит). 12 lint-тестов + doc/mcp тесты зелёные.
- 2026-06-13T09:54:25Z [implementation] — AC verified: 1. ✓ contradicts/superseded/stale_file (TestPureDetectors). 2. ✓ dry-run не архивит, --apply только superseded (TestServiceLint::test_dry_run/test_apply_archives_superseded_only). 3. ✓ CLI memory lint + MCP tausik_memory_lint (паритет, mirror_in_sync зелёный). 4. ✓ negative: пустая память, существующий путь, archived, битый edge (test_broken_edge/test_non_memory_edge/test_empty). 5. ✓ pytest 12 lint + 6 mcp-doc passed.
