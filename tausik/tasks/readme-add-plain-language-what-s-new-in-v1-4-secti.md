---
slug: readme-add-plain-language-what-s-new-in-v1-4-secti
title: "README: add plain-language What's new in v1.4 section"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "README.md, README.ru.md"
scope_exclude: "CHANGELOG.md, CHANGELOG.ru.md, docs/, scripts/, tests/, harness/, bootstrap/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T21:26:33Z"
---

## Goal

Current README has a near-stable banner but no list of what actually changed in v1.4. User wants a short, jargon-free 'What's new' section right after the banner so a returning user sees the headline changes at a glance instead of digging into CHANGELOG. Mirror in EN + RU.

## Acceptance Criteria

AC-1: Add a 'What's new in v1.4' callout/section directly after the banner block in BOTH README.md and README.ru.md, before the main TAUSIK intro paragraph; AC-2: 5-7 bullets total, plain language (no internal jargon like 'QG-2 verify-first', no slug refs); each bullet ≤ 150 characters; AC-3 (negative): bullets should NOT contain unexplained acronyms (B+C, QG-2, FPSR), task slugs, or test counts — those belong in CHANGELOG; AC-4: EN and RU sections cover the same items in the same order so the bilingual mirror stays in sync.

## Plan

## Rollback

## Journal

- 2026-05-07T21:26:26Z [implementation] — AC-1: ✓ "What's new in v1.4 (in plain language)" / "Что нового в v1.4 (простыми словами)" inserted in both README.md and README.ru.md right after the banner and before the "TAUSIK is a quality control framework" intro paragraph. AC-2: ✓ 7 bullets, plain language, each ≤150 chars (longest ~145). AC-3: ✓ no internal jargon (no QG-2, B+C, FPSR, slug refs, no test counts in the bullets — those stay in CHANGELOG). AC-4: ✓ EN/RU mirrors cover the same 7 items in identical order: fast task close → per-task budget → skill bundles → IDE/model variants → brain scrubbing → audit toolkit → push tickets.
