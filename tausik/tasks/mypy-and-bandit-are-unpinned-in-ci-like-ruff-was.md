---
slug: mypy-and-bandit-are-unpinned-in-ci-like-ruff-was
title: "mypy и bandit в CI стоят без пина — тот же класс, что уронил гейт ruff в день выпуска"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: backend
stack: null
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - ".github/workflows/*.yml"
  - ".gitlab-ci.yml"
  - pyproject.toml
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Вердикт каждого статического инструмента в CI определяется конфигом репозитория, а не тем, что вышло накануне — как уже сделано для ruff.

## Acceptance Criteria

## Plan

## Rollback

git revert правки конфигов CI

## Journal
