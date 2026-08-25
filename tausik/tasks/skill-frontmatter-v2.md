---
slug: skill-frontmatter-v2
title: "Skill frontmatter v2: context, effort, paths"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_copy.py"
  - "agents/claude/skills/review/SKILL.md"
  - "agents/claude/skills/explore/SKILL.md"
  - "agents/claude/skills/commit/SKILL.md"
  - "tests/test_bootstrap_frontmatter.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-31T19:19:18Z"
---

## Goal

Расширить формат SKILL.md полями context/effort/paths из Claude Code. Bootstrap парсит новые поля и пробрасывает их в .claude/skills/ frontmatter

## Acceptance Criteria

1. SKILL.md поддерживает поле context: inline|fork (default: inline). 2. SKILL.md поддерживает поле effort: fast|medium|slow. 3. SKILL.md поддерживает поле paths: glob-паттерны для auto-активации. 4. bootstrap.py парсит все 3 новых поля из frontmatter и копирует их в .claude/skills/ без потерь. 5. Существующие skills без новых полей продолжают работать (backward compatible). 6. Хотя бы 2 существующих skill дополнены новыми полями как пример. 7. SKILL.md с невалидным context (не inline/fork) вызывает warning при bootstrap.

## Plan

[{"step": "\u0418\u0437\u0443\u0447\u0438\u0442\u044c \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u043f\u0430\u0440\u0441\u0438\u043d\u0433 frontmatter \u0432 bootstrap.py", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u0430\u0440\u0441\u0438\u043d\u0433 context/effort/paths \u0432 bootstrap.py", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 skills \u2014 \u043f\u0440\u043e\u0431\u0440\u043e\u0441\u0438\u0442\u044c \u043d\u043e\u0432\u044b\u0435 \u043f\u043e\u043b\u044f", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u043e\u043b\u044f \u0432 2-3 \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0445 SKILL.md (review, explore, commit)", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b: \u043f\u0430\u0440\u0441\u0438\u043d\u0433 \u043d\u043e\u0432\u044b\u0445 \u043f\u043e\u043b\u0435\u0439 + backward compatibility", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c bootstrap \u0438 \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 \u0432 .claude/skills/", "done": true}]

## Rollback

## Journal
