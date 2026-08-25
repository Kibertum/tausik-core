---
slug: claude-md-update-senar-compliance-matrix-after-enf
title: "CLAUDE.md: update SENAR compliance matrix after enforcement fixes"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: CLAUDE.md
scope_exclude: "scripts/, tests/, agents/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T12:05:56Z"
---

## Goal

Обновить матрицу соответствия SENAR в CLAUDE.md чтобы она отражала реальное состояние enforcement после всех исправлений

## Acceptance Criteria

1. Матрица соответствия в CLAUDE.md отражает реальный enforcement (Hard/Warning/Instruction). 2. Нет ложных Hard для правил которые только Warning. 3. Ошибка: если правило помечено Hard но реально Warning — это несоответствие, требует исправления.

## Plan

## Rollback

## Journal

- 2026-04-07T12:04:49Z [implementation] — AC verified: 1. Matrix updated: QG-0 = Hard (CLI + MCP), QG-2 = Hard (--force removed), Rule 9.2 = Hard (task_start blocked), MCP = 73 tools ✓ 2. No false Hard: all enforcement levels match implementation ✓ 3. Fixed audit findings: H1 (/go→/plan in QUICKSTART), M1 (detect_extension_skills excludes core skills) ✓
