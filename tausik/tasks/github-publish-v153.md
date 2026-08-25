---
slug: github-publish-v153
title: "[release] Publish clean orphan snapshot v1.5.3 to public GitHub"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: null
tier: light
call_budget: 20
defect_of: null
scope: "Git plumbing only (orphan branch, force-push to github remote). No source file edits."
scope_exclude: "scripts/ harness/ docs/ site/ tests/ (no content changes); gitlab origin (untouched)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T10:55:41Z"
---

## Goal

Publish the current scrubbed v1.5.3 tree (HEAD 0cbf884: Windows fixes + leak scrub + RENAR site + green build) to public github.com/Kibertum/tausik-core as a SINGLE orphan commit, force-pushing over 73845cf. This removes both the old history AND the leaks ([вычеркнуто: third-party-service]/prod-IP/email/docs-audit) from the public repo entirely (orphan = no parents). Per user direction: github gets one powerful commit with the bump, no history. Audit the snapshot before pushing (zero leaks, file-count parity) and smoke-test a fresh clone after.

## Acceptance Criteria

AC1: a single orphan commit (no parents) is created from HEAD's tree; git diff HEAD <orphan> is empty (identical tree, no files dropped). AC2: snapshot audit — git grep over the orphan commit shows ZERO sensitive leaks ([вычеркнуто: third-party-service]/[вычеркнуто: unreleased-codename]/[вычеркнуто: internal-host]/jumashev); tracked file count == 809. AC3: orphan force-pushed to github main; git ls-remote github main returns the new orphan SHA and it has no parent. AC4: fresh clone of github main smoke-tests — bootstrap runs / CLI --version reports 1.5.3 / no leak in clone. AC5: local main restored, temp branch deleted, no disruption to gitlab origin. Negative: github history contains ONLY the one orphan commit (git log shows 1 commit); no leak reachable from any github ref.

## Plan

## Rollback

github reflog / the old 73845cf SHA is recorded here — `git push github 73845cf:main --force` restores the prior state if needed. Local main and gitlab origin are untouched.

## Journal

- 2026-06-15T10:55:40Z [implementation] — AC verified: 1. ✓ orphan commit 12c7e49 created via git checkout --orphan; git diff 0cbf884 HEAD empty (identical tree, 0 files dropped) 2. ✓ git grep over orphan: ZERO sensitive ([вычеркнуто: third-party-service]/[вычеркнуто: unreleased-codename]/[вычеркнуто: internal-host]/jumashev); git ls-files = 809 3. ✓ force-push '73845cf...12c7e49 _ghpub -> main (forced update)'; git ls-remote github main = 12c7e49; rev-list --count = 1 (no parent) 4. ✓ fresh clone of github main: 1 commit, version 1.5.3 (pyproject + tausik_version), 809 files, zero leaks, RENAR present; python bootstrap/bootstrap.py rc=0 'Bootstrap complete!', CLI version 1.5.3 5. ✓ local main restored to 0cbf884, _ghpub deleted; gitlab origin main still 0cbf884 (untouched)
