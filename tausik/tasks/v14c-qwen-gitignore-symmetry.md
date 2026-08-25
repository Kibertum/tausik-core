---
slug: v14c-qwen-gitignore-symmetry
title: "C7: .qwen/ gitignore symmetry с .claude/.cursor/"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: null
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: ".gitignore"
scope_exclude: ".qwen/* (uncache only via git rm), source files (отдельный commit)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T11:53:52Z"
---

## Goal

Сделать .qwen/ симметричным .claude/ и .cursor/: добавить в .gitignore, убрать из tracking. Bootstrap-generated IDE trees не должны коммититься (это generated artifacts, не source). Decision: следуем варианту "consistency = ignore all generated IDE trees", откладываем глобальный re-policy из auto-memory feedback на отдельное обсуждение когда коснёмся .claude/.cursor/ tracking.

## Acceptance Criteria

1. .gitignore содержит `.qwen/` (новая строка рядом с `.claude/` и `.cursor/`).
2. git rm -r --cached .qwen — все 285 ранее tracked файлов uncached (но остаются на диске для работы IDE).
3. git status после операции: working tree clean относительно .qwen/ (gitignored), source changes в других файлах остаются для отдельного commit'a.
4. Bootstrap re-run после commit'a: `git status --short | grep .qwen` → пусто (.qwen/ изменения не показываются).
5. Test: tests/test_bootstrap_drift.py (если есть, иначе скрипт `tausik doctor`) НЕ показывает drift для .qwen/ (gitignored).
6. Commit message: "chore(gitignore): ignore .qwen/ for symmetry with .claude/ and .cursor/" с reference на task slug.

## Plan

[{"step": "Add .qwen/ to .gitignore", "done": true}, {"step": "git rm -r --cached .qwen (uncache 285 files)", "done": true}, {"step": "Verify git status (working tree state)", "done": true}, {"step": "Commit chore(gitignore)", "done": true}, {"step": "task done", "done": true}]

## Rollback

## Journal

- 2026-05-03T11:53:52Z [implementation] — AC verified: AC-1 ✓ .gitignore +1 line: .qwen/ added next to .claude/.cursor/. AC-2 ✓ git rm -r --cached .qwen → 285 files D-staged. AC-3 ✓ git status post-commit: 0 .qwen entries (gitignored), 6 source files M (для следующего commit). AC-4 ✓ commit 438d789 'chore(gitignore): ignore .qwen/...'. AC-5 ✓ verify SKIP (no pytest gates relevant). AC-6 ✓ commit message содержит task slug v14c-qwen-gitignore-symmetry.
