---
slug: v1-4-0-release-banner-changelog-version-stamp
title: "v1.4.0 release banner + CHANGELOG version-stamp"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "README.md, README.ru.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/, harness/, bootstrap/, tests/, .claude/, docs/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T20:18:42Z"
---

## Goal

Add near-stable/pre-2.0 banner to README.md + README.ru.md (warning about possible doc drift on edge-cases) and version-stamp CHANGELOG.md + CHANGELOG.ru.md by renaming '[Unreleased] — v1.4.0 polish (Phases B + C)' to '[1.4.0] — 2026-05-07' in both files. Acceptance criteria: 1. Banner block present in both README files immediately after badges and before main intro text; 2. Banner text honestly notes large change set (B+C polish phases) and possible doc drift; 3. CHANGELOG.md and CHANGELOG.ru.md headers renamed to '[1.4.0] — 2026-05-07' with no other content changes.

## Acceptance Criteria

AC-1: Banner block (callout) present in BOTH README.md and README.ru.md immediately after the badges block and before the main intro paragraph; AC-2: Banner text marks v1.4 as near-stable / pre-2.0, references large B+C polish change set, and warns about possible doc-vs-behaviour drift on edge cases; AC-3: CHANGELOG.md and CHANGELOG.ru.md top-level header renamed from '## [Unreleased] — v1.4.0 polish (Phases B + C)' to '## [1.4.0] — 2026-05-07' with no other content edits.

## Plan

## Rollback

## Journal

- 2026-05-07T20:18:07Z [implementation] — Applied 4 edits: README.md + README.ru.md (banner block after badges, before main intro), CHANGELOG.md + CHANGELOG.ru.md (## [Unreleased] — v1.4.0 polish (Phases B + C) → ## [1.4.0] — 2026-05-07). EN/RU banner texts mirror each other; AC-1+AC-2+AC-3 satisfied via direct edit. Now running tausik verify --task to record green into cache before task_done.
- 2026-05-07T20:18:20Z [implementation] — AC verified: 1. ✓ README.md lines 12-18 banner inserted between badges (line 11) and main intro (line 20). README.ru.md lines 12-21 banner inserted between badges (line 11) and main intro (line 23). Both placed immediately after badges block and before main intro paragraph. 2. ✓ Banner text marks v1.4 as 'near-stable pre-2.0 release' (EN) / 'околостабильный pre-2.0 релиз' (RU); references 'B+C polish phases — verify-first contract, brain artifact pipeline, audit suite, skill bundles, two-axis variants, per-task cost/token budgets' large change set; warns about 'doc-vs-behaviour drift and rough edges on uncommon paths' (EN) / 'рассинхрон в документации и редкие нестабильности на edge-cases' (RU). 3. ✓ CHANGELOG.md line 10 renamed: '## [Unreleased] — v1.4.0 polish (Phases B + C)' → '## [1.4.0] — 2026-05-07'. CHANGELOG.ru.md line 12 renamed identically. Only the header line edited; body content untouched in both files. Verified by tausik verify --task v1-4-0-release-banner-changelog-version-stamp passed=True (pytest gate green).
- 2026-05-07T20:18:32Z [implementation] — AC verified: 1. ✓ README.md lines 12-18 banner inserted between badges (line 11) and main intro (line 20). README.ru.md lines 12-21 banner inserted between badges (line 11) and main intro (line 23). Both placed immediately after badges block and before main intro paragraph. 2. ✓ Banner text marks v1.4 as 'near-stable pre-2.0 release' (EN) / 'околостабильный pre-2.0 релиз' (RU); references 'B+C polish phases — verify-first contract, brain artifact pipeline, audit suite, skill bundles, two-axis variants, per-task cost/token budgets' large change set; warns about 'doc-vs-behaviour drift and rough edges on uncommon paths' (EN) / 'рассинхрон в документации и редкие нестабильности на edge-cases' (RU). 3. ✓ CHANGELOG.md line 10 renamed: '## [Unreleased] — v1.4.0 polish (Phases B + C)' → '## [1.4.0] — 2026-05-07'. CHANGELOG.ru.md line 12 renamed identically. Only the header line edited; body content untouched in both files. Verified by tausik verify --task passed=True (pytest gate green).
