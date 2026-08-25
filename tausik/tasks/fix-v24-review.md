---
slug: fix-v24-review
title: "Fix review findings from v2.4.0 review"
status: done
epic: frai-v24
story: vendor-skills-fix
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-26T14:59:46Z"
---

## Goal

Исправить все CRITICAL и HIGH findings из code review v2.4.0

## Acceptance Criteria

1. Symlink resolve отклоняет пути с .. или / prefix. 2. _read_plugin_json ограничен 1MB. 3. Gate commands работают с shell pipes (2>&1 | head). 4. Changelog v2.1.0 восстановлен. 5. STACK_GATE_MAP построен через функцию. 6. Config I/O не дублируется. 7. _write_plugin_meta использует ensure_ascii=False. 8. vendor_activated валидируется в bootstrap_copy. 9. Все тесты проходят.

## Plan

[{"step": "Fix all CRITICAL and HIGH review findings", "done": true}]

## Rollback

## Journal
