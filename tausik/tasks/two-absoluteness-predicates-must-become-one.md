---
slug: two-absoluteness-predicates-must-become-one
title: "Два предиката абсолютности пути живут в двух модулях и обязаны стать одним"
status: planning
epic: arch-debt-post-18
story: adp18-module-boundaries
complexity: simple
role: backend
stack: null
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/path_glob.py"
  - "scripts/knowledge_origin.py"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Один предикат о форме пути на весь репозиторий: path_glob.is_absolute и knowledge_origin._ABSOLUTE_RE перестают быть двумя копиями одной идеи.

## Acceptance Criteria

## Plan

## Rollback

git revert коммита

## Journal
