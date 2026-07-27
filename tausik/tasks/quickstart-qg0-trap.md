---
slug: quickstart-qg0-trap
title: "Fix quickstart first-task QG-0 negative-scenario trap"
status: planning
epic: null
story: null
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Remove the onboarding footgun: quickstart.md's first example task ('создай главную страницу с заголовком и кнопкой') hits the QG-0 negative-scenario HARD block (gate_qg0_check.py:201-207), contradicting the 'два-три сообщения на задачу' promise. Either make the example a task with a natural edge case, or pre-warn the reader that TAUSIK requires an error/boundary criterion and the agent supplies it — set expectations before the block fires.

## Acceptance Criteria

## Plan

## Rollback

## Journal
