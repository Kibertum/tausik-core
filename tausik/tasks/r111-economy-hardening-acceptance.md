---
slug: r111-economy-hardening-acceptance
title: "Accept 1.11 economy hardening on natural work"
status: active
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: "Evidence-only release acceptance over frozen prefix, replay, natural Codex task windows and already executed default/slow lanes."
scope_exclude: "No runtime changes, synthetic or paid benchmark, reconstructed baseline, cross-task causal claim, commit, push or release."
relevant_files:
  - "docs/ru/research/release111-economy-acceptance-final.md"
  - "changelog.d/economy-hardening-acceptance-111.md"
scope_paths:
  - "docs/ru/research/release111-economy-acceptance-final.md"
  - "changelog.d/economy-hardening-acceptance-111.md"
scope_tools: []
depends_on:
  - r111-bounded-work-packet
  - r111-compact-verification-output
  - r111-compound-progress-close
  - r111-prefix-dedup-lazy-schema
  - r111-terra-first-escalation
completed_at: null
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

Decide 1.11 readiness from direct prefix and workflow reductions plus naturally observed accepted-task rounds, without synthetic paid benchmarks or reconstructed baselines.

## Acceptance Criteria

AC-1 The same-surface repeated-prefix measurement shows at least 30 percent reduction. AC-2 Frozen replays prove the three selected deterministic cycles were removed without information or quality loss. AC-3 At least three natural post-change accepted tasks are reported with all attempts and a median no greater than 40 response rounds; otherwise the criterion remains explicitly unmet. AC-4 Default and slow quality lanes are green with skipped and deselected denominators stated. AC-5 Negative: no synthetic paid model run, cross-task model causal claim or convenient baseline reconstruction is used.

## Plan

[{"step": "Freeze acceptance inputs and verify implementation task identities", "done": true}, {"step": "Collect direct prefix and deterministic replay measurements", "done": true}, {"step": "Read at least three natural accepted-task windows with retries included", "done": true}, {"step": "Run release quality lanes and issue an evidence-bounded verdict", "done": true}]

## Rollback

Remove only the acceptance report and changelog fragment; runtime is unchanged.

## Journal

- 2026-10-01T20:29:38Z [planning] — OWNER TARGET: 1.11 must maximize economy before release. Direct acceptance thresholds are at least 30 percent same-surface prefix reduction and natural median at most 40 rounds over at least three post-change accepted tasks, with default and slow quality lanes preserved.
- 2026-10-01T21:48:59Z [planning] — Preliminary acceptance evidence: prefix same-surface63333->42519 bytes (-32.9%) verified by r111-prefix-dedup-lazy-schema receipt3323. Natural accepted cohort compound99/compact50/prefix46 rounds, median50 >40: AC-3 unmet. Frozen rows and exclusions: .tausik/planning/release-111/hardening-natural-20261002.json. Routing observations and final default/slow lanes still pending; task not closed.
- 2026-10-01T22:58:04Z [planning] — Dependency update: do not close until the four economy recovery tasks complete or are explicitly refused. Earlier implementation cohort median 50 remains visible; exact verification-cycle replay remains unmet.
- 2026-10-02T10:19:16Z [implementation] — Frozen implementation identities and evidence sources: prefix receipt #3323, work-packet/compound replays, verification-cycle refusal #3355, natural cohort artifacts and fresh release lanes.
- 2026-10-02T10:19:17Z [implementation] — Direct prefix 63333→42519 bytes (-32.9%) passes. Retrieval and progress/close replay pass; verification replay loses preflight evidence and fails AC-2.
- 2026-10-02T10:19:17Z [implementation] — Natural evidence remains below acceptance: frozen cohort 99/50/46 median 50; two newest complete accepted windows 58 and 61 rounds, with all attempts/retries retained; no third post-recovery window.
- 2026-10-02T10:19:17Z [implementation] — Release lanes pass: default 12791 passed/34 skipped/143 deselected; slow 143 passed/12826 deselected. Verdict HOLD; no task-level token-saving claim.
- 2026-10-02T10:19:18Z [implementation] — AC-1: ✓ same-surface prefix -32.9%. AC-2: ✗ verification pair is not equivalent; preflight evidence is omitted. AC-3: ✗ frozen natural median 50 >40 and post-recovery cohort has only two complete windows at 58/61. AC-4: ✓ default and slow denominators recorded. AC-5: ✓ no paid/synthetic run, reconstructed baseline or model causal claim. Domain: docs/ru/research/release111-economy-acceptance-final.md states the bounded release claim and HOLD barriers.
- 2026-10-02T11:26:45Z [implementation] — Credit metric now available without changing the quality bar: live Codex report measured 29/30 accepted tasks at 2037.571 configured subscription credits; 1 unknown model stayed explicit; raw input 526,421,076 and cached input 514,842,368 (97.8%). This is consumption evidence, not included-quota remaining, API USD, or a savings claim. AC2/AC3 remain unmet and the task stays active.
- 2026-10-02T11:59:03Z [implementation] — Systematic-output work completed without weakening quality: controlled prose replaced existing wording and reduced always-loaded answer contract 776→773 chars (verify #3370, 1057 passed). Format routing adds 0 chars to ordinary prompts and 337 chars only to explanation/visualization intent (verify #3372, 741 passed); no artifact/model run, renderer, or telemetry added. Acceptance remains active/unmet pending replay and natural cohort.
- 2026-10-02T12:06:59Z [implementation] — Release-readiness follow-up: moved the dirty 1.11 worktree safely from v1-10 to new local branch v1-11 without commit/push. Documentation integrity audit passed 729 tests with 12 skipped. Core docs and bilingual changelog cover 1.11 economy features; generated constants intentionally remain 1.10.1 until release cut. Separate tausik/site repository remains unchanged at e7da518 (vendored 1.5.8, manual navigation) and its blocked task still requires a release tag plus owner-authorized GitLab deployment. No additional core change was accepted from this audit; remaining high-value evidence is natural-task rounds/Luna qualification and verification replay, which stay unmet.
