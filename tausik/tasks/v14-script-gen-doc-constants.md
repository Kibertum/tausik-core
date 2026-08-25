---
slug: v14-script-gen-doc-constants
title: "Скрипт генерации констант (версия, tool counts) в docs/_generated"
status: done
epic: v14-doc-automation
story: v14-doc-generated-constants
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gen_doc_constants.py"
  - "scripts/mcp_tool_counts.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser.py"
  - "tests/test_gen_doc_constants.py"
  - "tests/test_mcp_doc_tool_counts.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T13:23:44Z"
---

## Goal

Exit 1 при рассинхроне с кодом.

## Acceptance Criteria

1. Скрипт в scripts/ или bootstrap. 2. Выходной файл под версионированием. 3. Negative: рассинхрон с pyproject/tools → exit 1.

## Plan

## Rollback

## Journal

- 2026-05-01T13:22:24Z [implementation] — AC: (1) scripts/gen_doc_constants.py + mcp_tool_counts.py (2) docs/_generated/constants.json versioned (3) --check exit 1 on drift — pytest test_gen_doc_constants + tausik doc constants wired
- 2026-05-01T13:22:32Z [implementation] — AC verified: 1. ✓ scripts/gen_doc_constants.py, mcp_tool_counts.py 2. ✓ docs/_generated/constants.json + README 3. ✓ --check exit 1 (test_run_main_check_fails_on_payload_drift)
