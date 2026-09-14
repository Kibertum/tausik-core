---
slug: the-19-pages-still-say-no-saving-figure-exists
title: "The 1.9 pages still say no token-saving figure exists, one session after the paired replay produced one"
status: done
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "README.md, README.ru.md, docs/en/whats-new-1.9.md, docs/ru/whats-new-1.9.md, tests/test_release_notes_1_9.py, .gitignore"
scope_exclude: null
relevant_files:
  - README.md
  - README.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
  - ".gitignore"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - README.md
  - README.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
  - ".gitignore"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-14T00:27:51Z"
---

## Goal

Release condition 1 (TAUSIK-plan-1.9.md §6): the saving promise is not published without a number. README.md, README.ru.md, docs/en/whats-new-1.9.md and docs/ru/whats-new-1.9.md say the figure "does NOT exist yet" and that saying "there is no saving" would be as unverified as claiming one. Since session #263 that is false: docs/ru/research/rag-nudge-replay-protocol.md §7 holds a valid paired measurement — ten fixed read-only questions, same commit, same model, cross-check matched — in which the harness WITH rag-first nudges cost more (Σ cache_creation + Σ output 198,848 vs 195,055, +1.9%; exploration result bytes 326,323 vs 292,715, +11.5%) and the nudges did not change tool choice (search_code 0 of 62 calls with them, 0 of 76 without). The telemetry facts stay true (233 of 57,251 rows carry input tokens; no "without TAUSIK" baseline) — the telemetry instrument still produces no figure; the replay instrument does, once, on one corpus and one pair, without generalisation (§6 of the protocol). The four pages must say exactly that, the caveat must sit next to the promise as before, and the numbers on the pages must be counted from the protocol's §7 table by a test, not retyped by hand. Also: .agents/ (a foreign skills directory that appeared 2026-09-09) is untracked and not ignored — a `git add -A` at the release commit would ship it; add it to .gitignore next to the other host directories.

## Acceptance Criteria

AC-1: tests/test_release_notes_1_9.py::TestTheUnmeasuredPromiseSaysSo passes with the caveat updated — the promise "экономия токенов"/"token saving" is still named and within 1200 chars of it the pages now say the figure was MEASURED ONCE and showed no saving on that pair ("ИЗМЕРЕНО ОДИН РАЗ" / "MEASURED ONCE"); the telemetry-absence sentence ("ОТСУТСТВИЕ величины" / "ABSENCE of a quantity") stays, scoped to the telemetry instrument. AC-2: a new test reads the §7 table of docs/ru/research/rag-nudge-replay-protocol.md (primary B and A, exploration bytes B and A, search_code B and A) and asserts each of the four pages (README.md, README.ru.md, docs/en/whats-new-1.9.md, docs/ru/whats-new-1.9.md) carries those exact figures — a number on the page is counted from the protocol, convention #673. AC-3 (negative): the same test fails when a page's figure is edited by one digit (mutation run logged), and the pages contain no sentence generalising beyond "on this corpus, in this pair" — the test refuses the phrases "экономии нет" / "there is no saving" unless followed within 80 chars by "на этой паре" / "on this pair". AC-4: .agents/ is in .gitignore; `git status --short` no longer lists it; tests/test_publication_lines.py still passes. AC-5: the full lane on the resulting tree is green (0 failed).

## Plan

## Rollback

git revert of the commit; prose and one test, no schema, no behaviour.

## Journal

- 2026-09-14T00:25:04Z [implementation] — AC-1 ✓ tests/test_release_notes_1_9.py::TestTheUnmeasuredPromiseSaysSo — caveat params moved to «ИЗМЕРЕНО ОДИН РАЗ» / "MEASURED ONCE"; the four pages rewritten: telemetry still produces no figure (233 of 57 251, no baseline — ABSENCE of a quantity kept, scoped to telemetry), the paired replay did (protocol §7 linked), 198 848 vs 195 055 (+1,9 %), 326 323 vs 292 715 (+11,5 %), search_code 0 of 62 / 0 of 76, one reading on one corpus, repeat of one condition varied 13 %. AC-2 ✓ tests/test_release_notes_1_9.py::TestTheMeasuredFigureIsCountedFromTheProtocol::test_the_page_carries_the_protocol_figures reads the §7 rows (primary, bytes, search_code) from docs/ru/research/rag-nudge-replay-protocol.md and checks README.md, README.ru.md, docs/{en,ru}/whats-new-1.9.md carry B, A and % (any thousands separator). AC-3 ✓ (NEGATIVE) mutation: README.md 198,848→198,849 → test_the_page_carries_the_protocol_figures FAILED (1 failed, 3 passed), restored byte-exact (cmp); docs/ru/whats-new «экономии нет на этой паре»→«экономии нет вообще» → test_no_saving_is_said_only_about_this_pair FAILED (1 failed, 3 passed), restored byte-exact. AC-4 ✓ .gitignore gets .agents/ with a comment; git status no longer lists it; tests/test_publication_lines.py 13 passed. Deployed profiles refreshed (bootstrap --ide all; --check clean; settings.json byte-identical). Domain: the pages now say what the repository's own protocol says, no wider — a reader of README sees the number, its source and its limit in one paragraph. AC-5: full lane running on this tree (lane3).
- 2026-09-14T00:27:46Z [implementation] — AC-5 (in progress): lane3 on the tree BEFORE the changelog entry: 3 failed / 10477 passed — two were the entry-count figure on the pages (250 → 251 after the new CHANGELOG entry, recounted on both pages, tests/test_release_notes_1_9.py 44 passed) and one is tests/test_release_roadmap.py::TestCommittedMapIsCurrent — ROADMAP.md went stale when this task reopened story release19-clean-publication-and-onboarding; it is regenerated after this close and the final lane runs on the tree to be committed. Scoped verify #2643: ruff PASS, pytest PASS (tests/test_release_notes_1_9.py), receipt signed. CHANGELOG entry added in both languages (Changed — the saving promise is measured once, and the pages say so).
