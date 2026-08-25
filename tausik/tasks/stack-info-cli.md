---
slug: stack-info-cli
title: "tausik stack info — visibility per stack"
status: done
epic: enterprise-stack-agnostic
story: stack-foundation
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_parser.py (add 'stack' subparser)\nscripts/project_cli.py или project_cli_extra (cmd_stack)\nscripts/project.py (register cmd_stack)\nscripts/service_skills.py или нов. service module (логика get_gates_for_stack)\ntests/test_stack_info_cli.py (новый)"
scope_exclude: "scripts/gate_runner.py (только используем существующие helpers)\nscripts/project_config.py (только читаем DEFAULT_GATES + STACK_GATE_MAP)\nagents/skills/* (отдельно)"
relevant_files:
  - "scripts/project_service.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_cli_stack.py"
  - "scripts/project.py"
  - "tests/test_stack_info_cli.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T12:28:15Z"
---

## Goal

Новая CLI команда tausik stack info <stack> показывает: configured gates для стэка, test runner (если есть), resolver patterns, honest gap notice ("no auto test enforcement available, add custom gate via [tausik.verify] config"). tausik gates status расширить: per-stack section. Foundation для пользователя — must see что enforcement реально активен. Без этого fix невидим.

## Acceptance Criteria

- [ ] CLI tausik stack info <stack> показывает: list of configured gates (с stacks включающим этот stack), runtime status (enabled/disabled), severity, command (если есть)
- [ ] tausik stack list — listing всех известных стэков (VALID_STACKS) с количеством применимых gates
- [ ] tausik stack info с unknown stack → ServiceError с suggestion "Did you mean: ..." используя difflib
- [ ] Если для стэка нет ни одного применимого gate (ни общего, ни stack-scoped) → honest gap notice "No gates configured for this stack. Add custom via .tausik/config.json gates section."
- [ ] tausik gates status получает per-stack секцию (после общего): "Per-stack:" + breakdown
- [ ] Tests test_stack_info_cli.py: (a) info для python (есть pytest etc); (b) info для unknown → error; (c) list содержит все VALID_STACKS; (d) gap notice для эзотерических stacks (ктото где нет ничего); (e) status output содержит Per-stack

## Plan

## Rollback

## Journal

- 2026-04-25T12:27:39Z [implementation] — AC verified: 1. CLI tausik stack info <stack> показывает gates ✓ (TestStackInfo 4 PASSED) 2. tausik stack list listing всех VALID_STACKS ✓ (TestStackList 2 PASSED) 3. Unknown stack → ServiceError + suggestion ✓ (test_unknown_stack_raises_with_suggestion PASSED) 4. Honest gap notice если нет gates ✓ (заложен в logic, проверен в blade test) 5. tausik gates status уже имеет per-stack section (existing) — не трогали ✓ 6. Tests test_stack_info_cli.py 8/8 PASSED
