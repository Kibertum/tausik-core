---
slug: changelog-s137-review-fix-batch
title: "CHANGELOG: record the four review-found fixes from the session-137 sweep"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 14
defect_of: null
scope: "CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "code, tests, other docs"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-25T06:38:24Z"
---

## Goal

The session-137 adversarial review of the #135-136 groundwork found four real defects (task-done scope write-before-guard, complexity ceremony-set missing AGENTS.md, gate SCOPE-label spoofable/dropped-on-error, AC-evidence REVIEW/DOMAIN parity asymmetry), all fixed and closed. The 1.8 [Unreleased] changelog documents every such fix in prose (cf. commit 1d9483c 'close seven enforcement holes found by adversarial review') but these four are not yet recorded. Add a themed section to both CHANGELOG.md and CHANGELOG.ru.md in the established narrative voice, keeping the two language mirrors in sync.

## Acceptance Criteria

1. CHANGELOG.md [Unreleased] gains one themed section covering all four fixes in the existing narrative voice (problem → consequence → fix), each fix identifiable. 2. CHANGELOG.ru.md gains the byte-parallel Russian section at the same position — the two mirrors stay in sync (per the file's own sync note). 3. Negative/guard: no version bump, no new release header, and no existing [Unreleased] entry is altered or removed — only an addition. 4. The section names the four concrete behaviours (certified-scope corruption, AGENTS.md ceremony overcount, spoofable/dropped SCOPE label, RU/EN evidence parity) so a reader maps each to its fix. 5. check_docs / filesize gates green.

## Plan

## Rollback

## Journal

- 2026-07-25T06:38:22Z [implementation] — AC verified: 1. ✓ CHANGELOG.md: new '### Reviewing the groundwork found four more holes...' section prepended at top of [Unreleased], narrative problem→consequence→fix voice, all four fixes identifiable 2. ✓ CHANGELOG.ru.md: byte-parallel Russian section '### Ревью фундамента нашло ещё четыре дыры...' at the same position; mirrors in sync 3. ✓ Negative/guard: no version bump, no new release header, existing [Unreleased] entries untouched — diff is pure addition above '### Groundwork' 4. ✓ Section names all four: certified-scope corruption, AGENTS.md ceremony overcount, spoofable/dropped SCOPE label, RU/EN evidence parity 5. ✓ verify run #1307 exit=0 (docs, no_tests_declared); filesize/doc gates green at close
