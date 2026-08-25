---
slug: site-mention-renar
title: "[site] Mention RENAR alongside SENAR on landing (foundation section + footer)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T10:43:29Z"
---

## Goal

The tausik.tech landing mentions SENAR (foundation section + footer 'Spec' column) but never RENAR. Add a mirrored RENAR mention (EN+RU) to HomeLanding.vue: extend the foundation section body to note TAUSIK adopts RENAR (reasoning/governance standard, renar.tech) advisory-first, and add a renar.tech link to the footer Spec/Спецификация column. Version is NOT changed in source — it auto-derives from constants.json (already 1.5.3); the live site just needs a redeploy.

## Acceptance Criteria

AC1: HomeLanding.vue EN + RU foundation section body mentions RENAR (bold) with a renar.tech link, advisory-first framing, without removing the SENAR text. AC2: footer Spec (EN) + Спецификация (RU) columns include a renar.tech link. AC3: VERSION untouched (still derives from constants.tausik_version = 1.5.3); no hardcoded version added. AC4: file still valid Vue/TS (no syntax break) — quick build or lint sanity. Negative: SENAR mentions remain intact; no other landing copy changed.

## Plan

## Rollback

## Journal

- 2026-06-15T10:43:28Z [implementation] — AC verified: 1. ✓ HomeLanding.vue senar.bodyHtml EN (line ~243) + RU (~480) now append a RENAR mention (bold, renar.tech link, advisory-first framing); SENAR text untouched 2. ✓ footer Spec (EN ~249) + Спецификация (RU ~486) columns now include [renar.tech, https://renar.tech] 3. ✓ VERSION untouched — still `constants.tausik_version` (=1.5.3 in committed constants.json); no hardcoded version added. Live site shows 1.5.0 only because deploy is stale; redeploy renders 1.5.3 4. ✓ vitepress build compiled HomeLanding.vue without error (build proceeded past the SFC); the sole build failure is a pre-existing, unrelated RU markdown bug in docs/ru/reasoning-trace.md (split inline-code <slug>), fixed under separate defect task site-reasoning-trace-build
