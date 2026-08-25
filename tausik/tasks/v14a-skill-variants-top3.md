---
slug: v14a-skill-variants-top3
title: "A3: variants/{haiku,sonnet}.md для /plan, /task, /ship"
status: done
epic: v14-polish-critical
story: v14-polish-a-pre-push
complexity: null
role: tech-writer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T10:24:38Z"
---

## Goal

Сейчас только _profile-demo/ — нет реальных variants для core skills. Создать variants/{haiku,sonnet}.md для /plan, /task, /ship. Haiku — компактные (≈40% токенов от Opus), Sonnet — middle (70%), Opus — full default SKILL.md. Делает multi-model profiles реально работающим.

## Acceptance Criteria

1. agents/skills/plan/variants/haiku.md создан — компактные подсказки (~40% токенов от full SKILL.md).
2. agents/skills/plan/variants/sonnet.md создан — middle (~70%).
3. agents/skills/task/variants/haiku.md + sonnet.md созданы.
4. agents/skills/ship/variants/haiku.md + sonnet.md созданы.
5. Variants — overlay фрагменты (no required frontmatter, see _profile-demo/variants/claude.md format).
6. Содержимое variants compact: для Haiku — bullet shorthand, для Sonnet — sentences without examples.
7. Negative: основные SKILL.md не тронуты (variants — overlay только).
relevant_files: agents/skills/plan/variants/haiku.md, agents/skills/plan/variants/sonnet.md, agents/skills/task/variants/haiku.md, agents/skills/task/variants/sonnet.md, agents/skills/ship/variants/haiku.md, agents/skills/ship/variants/sonnet.md

## Plan

## Rollback

## Journal

- 2026-05-03T10:24:38Z [implementation] — AC verified: 1. ✓ plan/variants/haiku.md 66 lines (44.6% of base 148). 2. ✓ plan/variants/sonnet.md 117 lines (79.1%). 3. ✓ task/variants/haiku.md 64 lines (38.3%) + sonnet.md 104 lines (62.3%). 4. ✓ ship/variants/haiku.md 56 lines (35.7%) + sonnet.md 117 lines (74.5%). 5. ✓ Overlay markdown — no YAML frontmatter (per _profile-demo format). 6. ✓ Compact: bullet/numbered imperatives для haiku, sentences без examples для sonnet. 7. ✓ Negative: основные SKILL.md не тронуты, новые директории plan/variants/, task/variants/, ship/variants/ созданы.
