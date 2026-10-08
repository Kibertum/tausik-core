---
slug: dobavlenie-mcp-tula-odno-kanonicheskoe-derevo-ne-tri
title: "Добавление MCP-тула: ОДНО каноническое дерево (не три зеркала) + 6 doc-count сайтов"
type: convention
tags:
  - bootstrap
  - harness
  - mcp
  - mirrors
task: list-prompts-list-resources-harness-claude-cursor-
edges: []
---

ЗАМЕНЯЕТ устаревшую конвенцию #146, которая предписывала «байт-копировать в harness/cursor/mcp». Зеркала harness/cursor/mcp БОЛЬШЕ НЕ СУЩЕСТВУЕТ — удалено в v1.7.0 (решение #134). Не воспроизводи его: гард tests/test_mcp_single_canonical_tree.py уронит сборку, если в harness/<ide>/mcp появится побайтовая копия файла из harness/claude/mcp.

Новый MCP-тул:
1. Правится ТОЛЬКО harness/claude/mcp/project (tools*.py + handlers*.py) — это единственный источник. copy_mcp раздаёт его всем IDE через фолбэк (`if not isdir(harness/<ide>/mcp): use harness/claude/mcp`); cursor, qwen, kilo и opencode все ходят по нему.
2. .claude/scripts и .claude/mcp — gitignored runtime-копии. После правки — `python bootstrap/bootstrap.py --ide all --no-detect`, иначе живой MCP после рестарта IDE поднимется на старом коде. Enforced: test_med_findings_fix::test_deployed_mcp_matches_the_canonical_source.
3. После gen_doc_constants.py счётчики mcp_project_tools/mcp_main_tools обязаны отразиться в README.md, README.ru.md, AGENTS.md (2 строки: дерево + таблица), docs/README.md, docs/en/mcp.md, docs/ru/mcp.md, docs/en/architecture.md — enforced test_mcp_doc_tool_counts + doc_drift_scanners (паттерны: пара 'N project + M brain', жирное '**N MCP tools**', 'N project tools').

ПОРЯДОК ВАЖЕН при бампе версии: бамп → gen_doc_constants.py --write → bootstrap --ide all. Наоборот — зеркала унесут старые константы, и аудит поймает дрейф.
