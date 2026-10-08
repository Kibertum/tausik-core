---
slug: ext-p3-enforcement-provider-ux
title: "[ext P3] Enforcement parity + provider UX (subscription, not tokens)"
status: planning
epic: v2-global-mcp
story: v2gm-surfaces
complexity: complex
role: developer
stack: null
tier: deep
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - provider-generates-artifacts-not-the-if-ide-ladder
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#64"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Enforcement parity + backend toggle. Qwen: gates port near-free via the Claude-identical hook contract (finish provider stub: get_active_model + transcript). Cursor: build an adapter emitting .cursor/hooks.json (beforeMCPExecution/beforeShellExecution allow/deny + failClosed) so SENAR gates hard-deny. Backend toggle UX: Claude (shell-out to local Claude Code, subscription, zero API key) vs GLM (z.ai Coding Plan env, subscription) — never become token-custodian. Kilo: accept advisory-only (re-verify no hook mechanism first).

## Acceptance Criteria

## Plan

## Rollback

Генерация .cursor/hooks.json и доводка провайдеров. Откат: git revert плюс повторный bootstrap возвращает прежнюю раскладку профилей; у потребителей файлы перезаписываются следующим bootstrap, ручной чистки не требуется.

## Journal

- 2026-08-29T14:07:04Z [planning] — [#189] ВТЯНУТА В 1.9 РЕШЕНИЕМ ВЛАДЕЛЬЦА 29.08. Замер хостов в этой сессии: у claude и qwen наборы хуков СОВПАДАЮТ полностью (22 уникальных хука на шести событиях), у opencode один плагин tausik-qg0.js, у kilo и cursor ноль развёрнутых механизмов. Ваш собственный текст этой задачи утверждает, что у Cursor механизм ЕСТЬ (.cursor/hooks.json, beforeMCPExecution/beforeShellExecution, allow/deny, failClosed) — значит «Cursor: 0» читается как «не генерируем», а не «невозможно», и это главный дешёвый выигрыш этапа. По Kilo владелец выбрал НЕ advisory-only, а MCP как точку контроля — заведено отдельной задачей kilo-enforcement-through-the-mcp-boundary; пункт «accept advisory-only» этой задачи отменяется. Оценка complex выставлена в #189.
