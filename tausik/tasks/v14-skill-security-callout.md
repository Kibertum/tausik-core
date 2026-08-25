---
slug: v14-skill-security-callout
title: "Bootstrap: явный security callout для внешних скиллов"
status: done
epic: v14-skill-store
story: v14-skill-store-trust
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/skill_repos.py"
  - "tests/test_skill_manager.py"
  - "bootstrap/bootstrap_templates.py"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - "docs/en/vendor-skills.md"
  - "docs/ru/vendor-skills.md"
  - "docs/en/skill-ecosystem.md"
  - "docs/ru/skill-ecosystem.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T17:38:31Z"
---

## Goal

Пользователь видит риск произвольного кода.

## Acceptance Criteria

1. Текст в шаблоне bootstrap. 2. Документация. 3. Negative: опасная операция без --force где требуется не выполняется.

## Plan

## Rollback

## Journal

- 2026-05-01T17:38:15Z [implementation] — AC verified: 1. Bootstrap build_skills_section — блок Security про внешние репо и --force. 2. docs: cli EN/RU, vendor-skills, skill-ecosystem, mcp EN/RU. 3. Negative: repo_add для стороннего URL без force не клонирует — SkillManagerError; официальный tausik-skills без force ок — тесты test_skill_manager.py.
