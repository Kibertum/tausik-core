---
slug: release-1-9-0-cut-tag-snapshot
title: "Release 1.9.0: the cut, the tag on the development line, the verified snapshot on GitHub, the published-tags record"
status: done
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/published_tags.json"
  - ROADMAP.md
  - "tests/test_published_tags_are_promises.py"
  - "tests/test_release_notes_1_9.py"
scope_paths:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/published_tags.json"
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-14T02:32:38Z"
resolution: null
resolution_reason: null
---

## Goal

Owner, session #264: «когда будешь уверен, что 1.9 можно выпускать — выпускай согласно нашим договорённостям». Confidence measured: GitLab pipeline #7722 on beb1ea5e is green in all four jobs including tests-full (pytest -m ''); the six release conditions of TAUSIK-plan-1.9.md §6 hold on that commit. The acts, in the order docs/ru/publishing.md prescribes (decision #368): (1) the CHANGELOG cut in both languages — [Unreleased] becomes [1.9.0] — 2026-09-14 with an empty Unreleased above it, the release commit; (2) that commit pushed and its pipeline green; (3) annotated tag v1.9.0 on it, pushed to origin; (4) tausik publish snapshot --from v1.9.0 --parent github/main, then publish verify; (5) refspec pushes to GitHub: the snapshot as main (fast-forward) and as refs/tags/v1.9.0 (lightweight); (6) tausik/published_tags.json updated on the development line in the same go, one commit after the push; (7) GitHub Release v1.9.0 with the notes; (8) PR #5 closed with the release link, as promised in its thread; tickets stay open per #366 until the owner closes them.

## Acceptance Criteria

AC-1: CHANGELOG.md and CHANGELOG.ru.md carry '## [1.9.0] — 2026-09-14' with the 1.9 entries under it and an empty [Unreleased] above (tests/test_release_notes_1_9.py reads the section on either side of the cut). AC-2: the release commit's GitLab pipeline is green in all four jobs. AC-3: 'tausik publish verify --snapshot <sha> --from v1.9.0' reports the snapshot tree equal to the filtered tree of the tag. AC-4: git ls-remote github shows refs/heads/main and refs/tags/v1.9.0 on the snapshot sha, and tausik/published_tags.json records v1.9.0 → that sha (tests/test_published_tags_are_promises.py green against the live remote). AC-5 (negative): no force push, no moved tag — every push is a fast-forward or a new ref; the firewall would have refused otherwise. AC-6: GitHub Release v1.9.0 exists with the notes; PR #5 closed with the link.

## Plan

## Rollback

A published tag never moves (publishing.md); before the GitHub push everything is local and reversible (git tag -d, branch reset); after it, a defect is fixed forward in 1.9.1.

## Journal

- 2026-09-14T02:32:10Z [implementation] — AC-1 ✓ CHANGELOG.md / CHANGELOG.ru.md: [Unreleased] → Nothing yet. / Пока пусто. above `## [1.9.0] — 2026-09-14`; tests/test_release_notes_1_9.py 44 passed on the released side. AC-2 ✓ release commit 0cfccd89: GitLab pipeline #7726 success in lint, doc-constants, tests, tests-full. AC-3 ✓ `publish snapshot --from v1.9.0 --parent github/main` → snapshot 03f1531b, "snapshot tree 4af23de7eb93 equals the filtered tree of v1.9.0", github/main faaa10f4 an ancestor; `publish verify` OK; dry run: 1329 published, 3121 excluded under 9 rules, 0 files in both leak classes. AC-4 ✓ ls-remote github: refs/heads/main = 03f1531b, refs/tags/v1.9.0 = 03f1531b; annotated v1.9.0 on the development line pushed to origin (0cfccd89); tausik/published_tags.json records v1.9.0 → 03f1531b, _taken_at 2026-09-14, session 264; tests/test_published_tags_are_promises.py 9 passed against the live remote. AC-5 ✓ (NEGATIVE) every push was a fast-forward or a new ref; no --force anywhere; the first main push hung 8 minutes on `git credential-manager get` (a hidden GUI prompt — no terminal in this session) and was stopped BEFORE anything reached the remote (main still faaa10f4), then re-run with a one-off `-c credential.helper=!gh auth git-credential` — no persistent git config changed. AC-6 ✓ GitHub Release v1.9.0 created (title + notes derived from docs/en/whats-new-1.9.md with absolute links; marked latest); PR #5 commented with the link and closed as promised; GitLab #5/#6/#14 stay open per decision #366 for the owner to close. Post-publication: GitHub workflow on main #34799474905 (macOS / 3.13 cells) was in_progress at this writing — read with `gh run view`.
