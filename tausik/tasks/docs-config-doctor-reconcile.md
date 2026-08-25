---
slug: docs-config-doctor-reconcile
title: "Config/doctor reconcile — session_capacity, brain defaults, env var name"
status: done
epic: null
story: null
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
depends_on: []
completed_at: "2026-05-15T13:37:00Z"
---

## Goal

(1) doctor.md:30 + session-active-time.md:39,45 — session_capacity_minutes → session_capacity_calls (200 calls, не minutes). (2) session-active-time.md:45 — AFK semantics: 'drops from active time' → 'clips to threshold'. (3) configuration.md:36 — TAUSIK_BRAIN_TOKEN → NOTION_TAUSIK_TOKEN. (4) configuration.md:41 — ~/.tausik-brain/mirror.db → brain.db. (5) doctor.md core skills list (8) — синхронизировать с реальными 11 в .tausik/config.json.

## Acceptance Criteria

(1) session_capacity_minutes → session_capacity_calls. (2) AFK semantics 'drops' → 'clips'. (3) brain token env var и mirror path исправлены. (4) doctor core skills list. (5) Ошибка: устаревшие имена не должны остаться.

## Plan

## Rollback

## Journal

- 2026-05-15T13:37:00Z [implementation] — AC verified: session_capacity_minutes → session_capacity_calls (3 файла EN+RU, всего 6). AFK clip semantics. TAUSIK_BRAIN_TOKEN → NOTION_TAUSIK_TOKEN (2 файла). mirror.db → brain.db (2 файла). doctor core skills list синхронизирован с 11 актуальными. pnpm build 4.63s clean.
