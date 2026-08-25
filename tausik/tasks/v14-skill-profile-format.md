---
slug: v14-skill-profile-format
title: "Спецификация профилей skills (frontmatter / variants/)"
status: done
epic: v14-model-prompts
story: v14-model-prompts-schema
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/skill_profile.py"
  - "bootstrap/bootstrap_copy.py"
  - "tests/test_skill_profile.py"
  - "tests/test_bootstrap_skills_coverage.py"
  - "docs/en/skill-profiles.md"
  - "docs/ru/skill-profiles.md"
  - "docs/en/skills.md"
  - "docs/ru/skills.md"
  - "agents/skills/_profile-demo/SKILL.md"
  - "agents/skills/_profile-demo/variants/claude.md"
  - "agents/skills/_profile-demo/variants/codex.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T13:48:28Z"
---

## Goal

Единый формат для мульти-модельных вариантов без дублирования всего SKILL.

## Acceptance Criteria

1. Спецификация в docs и пример. 2. Один демо-skill или фрагмент. 3. Negative: неизвестный профиль даёт fallback без crash.

## Plan

## Rollback

## Journal

- 2026-05-01T13:44:26Z [implementation] — AC verified: 1. ✓ docs/en|ru/skill-profiles.md + skills.md links 2. ✓ agents/skills/_profile-demo + variants 3. ✓ tests/test_skill_profile.py unknown+fallback; scripts/skill_profile.py 4. ✓ bootstrap skips _ prefix dirs
