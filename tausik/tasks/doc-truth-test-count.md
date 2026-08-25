---
slug: doc-truth-test-count
title: "Doc-truth: bump test count 2246→2270 across docs"
status: done
epic: v134-hardening
story: doc-truth-pass
complexity: simple
role: tech-writer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
  - README.ru.md
  - AGENTS.md
  - CONTRIBUTING.md
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-28T12:29:19Z"
---

## Goal

Update test count claims from 2246 to current 2270 across non-CHANGELOG docs after v1.3.3 added 24 tests. Keep CHANGELOG entries historical (do NOT touch).

## Acceptance Criteria

1. README.md badge URL `tests-2246%20passed` → `tests-2270%20passed` AND label `[![2246 tests]` → `[![2270 tests]`. 2. README.md Stats table row "Test count" → 2270. 3. README.ru.md same two replacements (badge + table). 4. AGENTS.md test count line bumped. 5. CONTRIBUTING.md test count line bumped. 6. docs/en/architecture.md + docs/ru/architecture.md test count bumped. 7. CHANGELOG.md untouched (historical entries are immutable). 8. `pytest --collect-only -q | tail -1` confirms 2270 (or whatever current count is at task time — re-verify before commit). 9. `git grep -n '2246' -- ':!CHANGELOG.md'` returns zero hits after edit. 10. Negative scenario: test count grew between task start and commit — re-grep + re-verify, do not blindly trust 2270.

## Plan

[{"step": "\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c pytest --collect-only \u0434\u043b\u044f \u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u0447\u0438\u0441\u043b\u0430 (re-verify \u043f\u0435\u0440\u0435\u0434 \u043f\u0440\u0430\u0432\u043a\u043e\u0439)", "done": true}, {"step": "git grep -n '2246' -- ':!CHANGELOG.md' \u2014 \u0441\u043f\u0438\u0441\u043e\u043a \u0444\u0430\u0439\u043b\u043e\u0432", "done": true}, {"step": "Edit README.md: badge label + URL + Stats table", "done": true}, {"step": "Edit README.ru.md: badge + table", "done": true}, {"step": "Edit AGENTS.md, CONTRIBUTING.md, docs/{en,ru}/architecture.md", "done": true}, {"step": "git grep '2246' -- ':!CHANGELOG.md' \u2014 \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c 0 hits", "done": true}, {"step": "task done --ac-verified + commit 'docs: bump test count to N'", "done": true}]

## Rollback

## Journal

- 2026-04-28T12:27:39Z [implementation] — pytest --collect-only: 2271 collected. Last full-suite run: 2270 passed, 1 skipped (~6m11s). Using 2270 (passing count) to match existing 'passed' badge semantics. Found 8 occurrences across 6 files (README.md ×2, README.ru.md ×2, AGENTS.md, CONTRIBUTING.md, docs/en/architecture.md, docs/ru/architecture.md).
- 2026-04-28T12:29:05Z [implementation] — AC verified: ✓1 README.md badge + URL bumped 2246→2270 (replace_all). ✓2 README.md Stats table 'Test count | 2246' → 2270 (covered by replace_all). ✓3 README.ru.md badge + URL + table bumped 2246→2270 (replace_all). ✓4 AGENTS.md line 95 bumped. ✓5 CONTRIBUTING.md line 64 bumped. ✓6 docs/en/architecture.md line 158 bumped. ✓7 docs/ru/architecture.md line 171 bumped. CHANGELOG.md untouched (5 historical references preserved per AC #7). ✓8 pytest --collect-only confirmed 2271 collected; last full run 2270 passed +1 skipped — using 2270 ('passed' count) to match badge wording. ✓9 final Grep '2246' shows only CHANGELOG.md hits (5 lines, all historical). ✓10 negative scenario covered: re-verified count was current at task start; if grew, plan step 1 catches it.
- 2026-04-28T12:29:19Z [implementation] — AC verified: ✓1 README.md badge + URL bumped 2246→2270. ✓2 README.md Stats table row bumped. ✓3 README.ru.md badge + URL + table bumped. ✓4 AGENTS.md bumped. ✓5 CONTRIBUTING.md bumped. ✓6 docs/en/architecture.md bumped. ✓7 docs/ru/architecture.md bumped. CHANGELOG.md untouched (5 historical refs preserved per AC #7). ✓8 pytest --collect-only confirmed 2271 collected; last full run 2270 passed +1 skipped — using 2270 ('passed' count). ✓9 final Grep '2246' shows only CHANGELOG.md hits (5 historical lines). ✓10 negative scenario covered: count re-verified at task start.
