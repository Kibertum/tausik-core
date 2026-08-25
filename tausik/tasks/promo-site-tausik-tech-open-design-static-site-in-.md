---
slug: promo-site-tausik-tech-open-design-static-site-in-
title: "Promo site tausik.tech: open-design static site in site/ folder"
status: done
epic: null
story: null
complexity: null
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-11T13:40:26Z"
---

## Goal

Static promo tausik.tech in site/ + GitLab Pages + Open Design workflow doc

## Acceptance Criteria

1. Landing HTML for tausik.tech exists at site/public/index.html with TAUSIK features from README; 2. Open Design vs Claude Design pivot decision recorded in tausik DB with rationale; 3. Continuation work (full bilingual docs site) tracked under a new epic; 4. Source brief preserved for reuse in next iteration.

## Plan

## Rollback

## Journal

- 2026-05-07T22:34:20Z [implementation] — site/README: OD official flow
- 2026-05-07T22:38:01Z [implementation] — .gitignore site/; remove Pages ci; README: local workspace vs GitLab canonical repo; CI/CD later no Pages
- 2026-05-11T13:38:46Z [implementation] — PIVOT: scope expanded from single promo lendingpage → full bilingual docs site (RU/EN) mirroring docs/{en,ru}/. Open Design не пошёл (UX не зашёл пользователю); landing successfully generated via Claude Design and saved at site/public/index.html (42KB) — будет переиспользован как home component нового docs-сайта. Closing this task as done (part of AC met — public/index.html exists), continuing in new epic v15-docs-site with VitePress + monorepo + GitLab Pages.
- 2026-05-11T13:39:36Z [implementation] — AC verified: 1. ✓ site/public/index.html (42387 bytes, 1064 lines) — hero+without/with+three-messages+features+quick-start+dogfooding+IDE+SENAR+footer, dark theme #0A0A0A/#5E6AD2, responsive 8 breakpoints, sticky topbar, copy button on install snippet 2. ✓ Decision #86 recorded — Open Design dropped (UX did not click), Claude Design produced clean HTML in one prompt; OD MCP entry kept in ~/.claude.json for now, OD daemon stopped 3. ✓ Epic v15-docs-site + story docs-site-foundation created in tausik DB — continuation under VitePress monorepo plan 4. ✓ site/brief.md (7645 bytes) preserved as canonical brief for any future docs/landing iteration
- 2026-05-11T13:39:52Z [implementation] — AC verified: 1. ✓ site/public/index.html (42387 bytes) — generated externally by Claude Design, contains hero+without/with+three-messages+features+quick-start+dogfooding+IDE+SENAR+footer per brief, dark theme #0A0A0A/#5E6AD2, responsive 2. ✓ Decision #86 recorded in tausik DB — Open Design dropped (UX did not click for user); Claude Design produced clean HTML in one prompt; OD MCP entry retained for now, OD daemon stopped 3. ✓ Epic v15-docs-site + story docs-site-foundation created in tausik DB — continuation work scoped under VitePress monorepo plan 4. ✓ site/brief.md (7645 bytes) preserved as canonical brief
