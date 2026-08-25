---
slug: fix-templates
title: "Обновить шаблоны CLAUDE.md и .cursorrules в bootstrap_generate.py"
status: done
epic: docs-audit
story: templates-sync
complexity: simple
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
completed_at: "2026-03-14T12:46:52Z"
---

## Goal

Шаблоны generate_claude_md и generate_cursorrules должны использовать .frai/frai вместо python .claude/scripts/project.py

## Acceptance Criteria

1. generate_claude_md() использует .frai/frai во всех примерах
2. generate_cursorrules() использует .frai/frai во всех примерах
3. Full CLI ref ссылка обновлена на .frai/references/project-cli.md
4. Bootstrap прогон не ломает тесты

## Plan

## Rollback

## Journal
