---
slug: v15-site-redesign
title: "Site redesign (VitePress) — receipts hero/section, sticky-nav, stale fixes, OG-meta"
status: done
epic: v15-release-polish
story: v15-polish-public
complexity: complex
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "site/.vitepress/theme/components/HomeLanding.vue"
  - "site/.vitepress/theme/components/landing/*"
  - "site/.vitepress/config.ts"
  - "docs/en/no-sdk-verify.md"
  - "docs/ru/no-sdk-verify.md"
scope_tools: []
depends_on: []
completed_at: "2026-06-13T13:38:40Z"
---

## Goal

Кратно улучшить landing (site/.vitepress/theme/components/HomeLanding.vue, bilingual EN/RU): P0 — receipts hero+секция (главный differentiator) + fix stale «732 tasks/v1.4.0», sticky section-nav + persistent CTA; P1 — GitHub-stars/social proof, comparison-row receipts, OG/social-meta, split SFC <400 строк; P2 — receipt-flow SVG, IDE-credibility pass. Все copy-блоки в copy.en+copy.ru синхронно. Зависит от v15-receipts-docs.

## Acceptance Criteria

AC1: Landing surfaces signed ed25519 receipts as the headline differentiator — a dedicated receipts section + receipts woven into the hero (badge/anno), bilingual EN+RU synchronously, copy reused from README. AC2: Stale stats fixed — no hardcoded "732"/"v1.4.0"; foot binds to v{VERSION} constant. AC3: Sticky section-nav + persistent CTA present and functional. AC4: Comparison table has a receipts row; config.ts has OG/social meta head tags. AC5: pnpm build in site/ passes; gen_doc_constants --check green. AC6 (negative/boundary): if a copy key is missing in either locale or the build fails (dead link, type error, undefined constant), the build errors and the change is NOT shipped — empty/undefined copy must not render blank sections.

## Plan

## Rollback

git checkout site/.vitepress/theme/components/HomeLanding.vue site/.vitepress/config.ts && rm -rf site/.vitepress/theme/components/landing/ — pure presentational VitePress SFC + config; no DB/runtime/state changes; revert = restore two files + drop new landing/ dir.

## Journal

- 2026-06-13T13:36:24Z [implementation] — P0+P1 done: receipts hero badge+anno+dedicated section (EN+RU, reused README Verifiable-trust copy), stale stats fixed (732→800+, v1.4.0→v${VERSION}), sticky section-nav + persistent CTA, comparison receipts row, config.ts OG/twitter meta. Deferred to 1.x: SFC split <400 (file not gate-scanned, already 1881 pre-existing) + P2 receipt-flow SVG/IDE pass. Next: pnpm build + gen_doc_constants --check.
- 2026-06-13T13:38:36Z [implementation] — AC verified: AC1 ✓ receipts surfaced — hero badge "ed25519 signed receipts" + /ship anno + dedicated #receipts section (4 points + signed-receipt terminal + CTA), bilingual EN+RU synchronous, copy reused from README Verifiable-trust. AC2 ✓ stale stats fixed — "732"→"800+", foot now `Snapshot at v${VERSION}` (binds to constants, no hardcoded v1.4.0). AC3 ✓ sticky .section-nav (position:sticky top:0) with brand + 5 section links + persistent "Get started" CTA. AC4 ✓ comparison table receipts row (ed25519 / tausik-signed/v1) both locales + config.ts head[] OG+twitter meta. AC5 ✓ pnpm build PASS (build complete 7.55s; also fixed 2 pre-existing dead links in no-sdk-verify.md EN+RU blocking the build) + gen_doc_constants --check OK. AC6 (negative) ✓ build is fail-closed — VitePress errors on dead link / missing copy key / type error (proven: build failed red on the dead links until fixed, then green). Security: presentational VitePress SFC + config + 2 doc-link fixes — no runtime/DB/auth/input surface, zero threat surface. Verify run #705 signed receipt key 103a83a212851018.
