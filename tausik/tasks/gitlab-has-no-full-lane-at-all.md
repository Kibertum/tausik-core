---
slug: gitlab-has-no-full-lane-at-all
title: "В GitLab нет полной ленты вовсе: на линии разработки гоняется только быстрая половина"
status: planning
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
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
depends_on:
  - full-lane-runs-serial-on-a-twenty-core-machine
completed_at: null
---

## Goal

ЗАМЕР #189 ПО ПРОЧИТАННОМУ КОНФИГУ: джоб `tests` в .gitlab-ci.yml зовёт `pytest tests/ -q --tb=short` и наследует addopts = -m 'not slow' из pyproject. То есть на линии разработки (решение #267: GitLab — линия разработки) гоняется ТОЛЬКО БЫСТРАЯ ПОЛОВИНА. Полная лента живёт исключительно в GitHub (джоб test-full), куда рабочая ветка не попадает и не должна попадать.
СЛЕДСТВИЕ: даже когда триггер починится, slow-тесты — собственные регрессионные тесты проекта (обвязка, интеграция MCP, subprocess) — на ветке разработки не выполнятся ни разу.
ЧТО ДЕЛАЕТСЯ: отдельный джоб полной ленты в GitLab. Стоимость снята задачей про xdist: 3m48s вместо 32m24s делает полную ленту пригодной для КАЖДОГО push, а не только для релиза. Раннер — shell executor на общей машине с переиспользуемым workspace (GIT_CLEAN_FLAGS=-ffdx), venv создаётся заново каждым джобом ВНЕ чекаута; лишний джоб есть лишний pip install, и это надо учесть, а не игнорировать.
ЗАВИСИТ от xdist и от решения по сторожу зависаний.

## Acceptance Criteria

## Plan

## Rollback

Новый джоб в .gitlab-ci.yml. Откат — удаление джоба; продуктовый код не трогается.

## Journal
