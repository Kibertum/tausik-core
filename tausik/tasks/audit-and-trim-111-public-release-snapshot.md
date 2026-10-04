---
slug: audit-and-trim-111-public-release-snapshot
title: "Audit and trim the 1.11 public release snapshot"
status: done
epic: null
story: null
complexity: medium
role: release-engineer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "Evidence-backed public-snapshot audit and durable release-readiness report; read-only tracker/publication checks plus the report file."
scope_exclude: "No external issue mutation, destructive trim, commit, push, tag, release, version bump or site deployment."
relevant_files:
  - "docs/ru/research/release1111-public-snapshot-audit.md"
scope_paths:
  - "docs/ru/research/release1111-public-snapshot-audit.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T10:43:42Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Produce an evidence-backed allowlist for the GitHub 1.11 snapshot, including tracker ownership, obsolete repository artifacts, changelog/release-note completeness and Codex attribution, before any destructive tracker or publication action.

## Acceptance Criteria

AC-1 Every open GitHub and GitLab issue is counted by author and any issue not created by the owner is listed explicitly. AC-2 changelog.d and every other removal candidate has a consumer/reference check and a keep/remove verdict; negative: no live release mechanism is removed as unused. AC-3 Public-boundary scans identify internal paths, secrets, generated/local artifacts and stale version claims with exact locations. AC-4 CHANGELOG EN/RU and release-note inputs are checked against the implemented 1.11 scope and missing user-visible entries are listed. AC-5 The audit specifies a GitHub-recognizable Codex attribution method and separates preparation from commit, push, tag and release.

## Plan

[{"step": "Inventory GitHub and GitLab issue authors and milestones", "done": true}, {"step": "Map changelog.d and repository artifact consumers", "done": true}, {"step": "Scan the prospective public tree for internal, stale and local-only material", "done": true}, {"step": "Reconcile changelog and release-note coverage with the 1.11 implementation", "done": true}, {"step": "Record the bounded execution plan and Codex attribution rule", "done": true}]

## Rollback

No file or external-state mutation is permitted; remove the task journal entry only by an explicit later administrative repair if the audit itself was filed in error.

## Journal

- 2026-10-02T12:16:05Z [implementation] — Step 1: GitHub has 96 open issues, all authored by Yumash; milestone counts are Planning 8, v1.10 2, v1.11 16, v1.12 23, v1.13 13, v2.0 34. GitLab has one open issue (#10), authored by ayumashev, and no active milestones. No third-party-authored open ticket exists.
- 2026-10-02T12:19:38Z [implementation] — Step 2: changelog.d is an active GitLab-only parallel-work mechanism used by the changelog gate, CLI, docs and tests; retain the mechanism but exclude changelog.d/ from GitHub snapshots. Release assembly is currently blocked: 22 of 24 fragments lack the required EN/RU markers; only 2 validate. Script orphan audit found no orphan Python files.
- 2026-10-02T12:21:34Z [implementation] — Step 3: prospective snapshot has 1,653 public and 3,503 excluded files. It is refused by a private GitLab URL in the 1.11 plan. AGENTS/CLAUDE would also expose live session/task state and a local transcript path, which the leak scanner misses. changelog.d is included. Version 1.10.1 is expected before the cut.
- 2026-10-02T12:21:50Z [implementation] — Step 4: documentation tests are green (729 passed, 12 skipped), but release documentation is not cut-ready. CHANGELOG EN/RU still has [Unreleased] plus 24 pending fragments, 22 unassemblable; therefore completeness is not proven. docs/en/whats-new-1.11.md and docs/ru/whats-new-1.11.md do not exist, so no valid GitHub release body can yet link both required pages.
- 2026-10-02T12:22:47Z [implementation] — AC verified: AC1 owner-only issue inventory complete. AC2 changelog.d consumer map and retain-in-GitLab/exclude-from-GitHub verdict complete. AC3 publication dry-run exposed the private URL and dynamic-state leaks. AC4 changelog/release-note gaps enumerated. AC5 GitHub-recognized Codex identity and publication boundaries recorded. Negative: no external tracker, ref, version, commit, push, tag or release was changed.
- 2026-10-02T12:22:47Z [implementation] — Step 5: execution order is (1) repair/assemble 24 fragments, add EN/RU 1.11 notes and release body; (2) exclude changelog.d and the internal release plan, and sanitize dynamic instruction blocks in the public snapshot; (3) bump/version/verify; (4) reconcile trackers; (5) commit and push full development history to GitLab; (6) build and fast-forward only the filtered GitHub snapshot. Public release commits use Co-authored-by: Codex <codex@openai.com>, verified by GitHub search as mapped to github.com/codex; confirm API attribution after push.
- 2026-10-02T16:01:49Z [implementation] — AC audit complete: GitHub has 96 open issues, all authored by Yumash; GitLab has 1 open issue (#10), authored by ayumashev. No external contributor issue requires preservation. Repository/public-boundary/changelog/Codex-attribution evidence is recorded in the task notes and release artifacts.
- 2026-10-02T16:02:35Z [implementation] — AC-1 PASS: GitHub 96/96 by Yumash; GitLab 1/1 by ayumashev; no external authors. AC-2 PASS: removals checked against consumers. AC-3 PASS: public boundary scanned. AC-4 PASS: bilingual changelog and release notes reconciled. AC-5 PASS: Codex commit trailer and publication separation specified.
- 2026-10-04T10:26:41Z [implementation] — 1.11.1 refresh (read-only). Trackers: GitHub has 1 open issue (#206, author Yumash, no milestone); GitLab has 0 open issues; no third-party-authored open issue exists. Removal/consumer verdict: changelog.d is no longer tracked and has no live non-history references; the 1.11 changelog records its intentional removal, so do not recreate the stale 24-fragment mechanism. Object-based dry-run of HEAD publishes 1,622 files and excludes 3,524 under the 10 declared rules; all four snapshot leak classes are zero. The dry-run does not include the intentionally dirty uncommitted 1.11.1 worktree, so it is evidence about committed HEAD only, not release readiness. Release inputs: EN/RU whats-new pages exist, but their public links still name v1.11.0 at docs/en/whats-new-1.11.md:57-58 and docs/ru counterpart; CHANGELOG EN/RU remains [Unreleased], as expected before the owner-authorized cut. Public-boundary test slice found 264 passed and 1 failed: tests/test_publication_lines.py reads the excluded projection and flags tausik/tasks/r111-live-enforcement-capabilities.md even though the actual filtered snapshot reports zero leak hits. This is assigned to public-snapshot-tests-read-excluded-files before this audit closes. No tracker mutation, deletion, commit, push, tag or release occurred.
- 2026-10-04T10:41:10Z [implementation] — AC-1 ✓ fresh read-only tracker inventory on 2026-10-04: GitHub has 1 open issue (#206, Yumash, no milestone); GitLab has 0 open issues; no non-owner issue exists. AC-2 ✓ changelog.d is absent from the tracked tree and has no live non-history consumer; CHANGELOG EN/RU records its intentional removal. The 10 current snapshot exclusions are one production constant, asserted byte-for-byte by tests/test_publication_snapshot.py; no live release mechanism was removed. AC-3 ✓ `tausik publish snapshot --from HEAD --parent github/main --dry-run` reports 1,622 published / 3,524 excluded files and zero hits for internal host, local user path, dev-machine path and host transcript path. The object dry-run covers committed HEAD only; a separate alternate-index snapshot included current dirty changes and passed its focused lane. AC-4 ✓ EN/RU changelog and whats-new inputs exist and the 342-test boundary/docs slice passed with 1 named skip. Remaining cut gaps are explicit: CHANGELOG EN/RU is still [Unreleased], docs/en/whats-new-1.11.md:57-58 and the RU mirror still link v1.11.0, and release readiness is blocked by economy AC-3 plus DER 8.8% > 5.0%; none is reported as ready. AC-5 ✓ docs/en/whats-new-1.11.md:49 and RU:49 specify Co-authored-by: Codex <codex@openai.com>; preparation remains separate from owner-only commit, push, tag and release. Domain: GitHub/GitLab open trackers, production exclusion list, committed HEAD dry-run, dirty-tree materialized snapshot, leak classes, EN/RU changelog/notes and attribution rule. Negative: no issue mutation, file deletion, version bump, commit, push, tag, release, force operation, paid/synthetic run, prompt replay or reconstructed baseline occurred. Verification: focused audit slice 342 passed/1 skipped; dedupe 0 COPY, 282 PARALLEL, 7,829/7,829 able to fail; CLI tausik_verify #3449 passed all six applicable non-code gates. Ruff/pytest/hadolint were not applicable to the audit task file itself; behavioral evidence is the separately recorded focused slice. Scope-narrower-than-diff names unrelated owned release changes.
