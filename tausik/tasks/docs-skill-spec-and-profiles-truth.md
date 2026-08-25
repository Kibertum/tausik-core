---
slug: docs-skill-spec-and-profiles-truth
title: "Skill-spec + skill-profiles truth — fix Categories table and two-axis claim"
status: done
epic: null
story: null
complexity: medium
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
completed_at: "2026-05-15T13:38:52Z"
---

## Goal

(1) skill-spec.md:50-73 — переписать Skill Categories table: actual core_skills 11 из .tausik/config.json (не 5). Remove 'init' skill (removed v1.4). (2) skill-spec.md:70 — .claude-bootstrap.json → .tausik/config.json. (3) skill-profiles.md:9-26 — либо drop two-axis claim либо ship variants/ide/ (сейчас только model/). (4) skill-profiles.md:22-25 — drop opus.md и qwen.md (нет файлов); реальные: gpt-4, gpt-5, gpt-5-5, haiku, sonnet.

## Acceptance Criteria

(1) skill-spec.md Categories table обновлена с актуальными 11 core skills и .tausik/config.json path. (2) skill-profiles.md two-axis claim фикснут — либо снят либо документирован реально. (3) opus.md и qwen.md удалены из списка (нет файлов). (4) pnpm build clean. (5) Ошибка: устаревшие имена не должны остаться.

## Plan

## Rollback

## Journal

- 2026-05-15T13:38:52Z [implementation] — AC verified: skill-spec.md Categories table обновлена (11 core, .tausik/config.json path, init removed note). skill-profiles.md two-axis claim qualified (ide/ только в _profile-demo; production skills имеют только model axis). opus.md и qwen.md помечены как detector-resolved-but-no-file (fall back to base). pnpm build 4.35s clean.
