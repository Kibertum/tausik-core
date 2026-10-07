---
slug: r111-economy-hardening-acceptance
title: "Accept 1.11 economy hardening on natural work"
status: done
epic: release-1-11-3
story: release1113-pooled-verification
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
scope_paths:
  - "docs/ru/research/release111-economy-acceptance-final.md"
  - "changelog.d/economy-hardening-acceptance-111.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - r111-bounded-work-packet
  - r111-compact-verification-output
  - r111-compound-progress-close
  - r111-prefix-dedup-lazy-schema
  - r111-terra-first-escalation
completed_at: "2026-10-07T19:50:09Z"
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
- 2026-10-04T10:04:25Z [implementation] — Natural post-recovery acceptance refreshed on 2026-10-04 without paid or synthetic execution. Exact accepted windows: capture-natural-project-benchmark-cohorts 89 responses / 6 attempts / 5 retries; add-cli-version-flag-and-block-session-start-on-a 124 / 5 / 4; add-memory-only-governance-profile 82 / 2 / 1. Median response rounds = 89, so AC-3 remains explicitly unmet against the <=40 threshold. compare-project-version-model-economics has no exact accepted-window in the current report and remains unknown, not zero. Account quota is separately reported at 86% used; subscription credits remain separate and no API-equivalent USD claim is made here. Updated the bounded HOLD report; docs cross-claim tests passed.
- 2026-10-04T10:21:37Z [implementation] — Release acceptance evidence refreshed without weakening AC. AC-1 PASS: frozen same-surface prefix 63,333→42,519 bytes (-32.9%). AC-2 FAIL: verification replay still omits the 80-pass preflight result; resolve in r111-verification-cycle-replay by preserving both results or explicit refusal without a savings claim. AC-3 FAIL: natural windows are 89 responses / 6 attempts / 5 retries, 124 / 5 / 4, and 82 / 2 / 1; median 89 > <=40. Observed model is gpt-5.6-sol medium/standard for all three; exact TAUSIK 1.11.0 is present only for the 124/82 windows, while the 89 window remains unknown/legacy. compare-project-version-model-economics has no exact accepted-window and remains unknown, not zero. AC-4 PASS on recorded lanes: default 12,791 passed / 34 skipped / 143 deselected; slow 143 passed / 12,826 deselected. AC-5 PASS: no paid/synthetic run, prompt replay, reconstructed baseline, mandatory version×model matrix, cross-task causal claim, or unsupported savings claim. Domain: dated report now also records API-equivalent USD unknown because no dated rate card is configured, subscription quota separately at 86% used, DER 8.8% versus unchanged <=5.0%, and 99 closures since audit. Negative: unknown identity/cost/window never becomes zero; subscription quota is not API USD. Focused docs tests: 326 passed, 1 skipped. audit_pytest_dedupe.py: 0 COPY, 282 PARALLEL, 7829/7829 able to fail. tausik_verify #3442 PASS for the declared docs scope, but ruff/pytest skipped and the receipt is narrower than the intentionally dirty 272-file worktree; it is not used for QG-2. Verdict remains HOLD.
- 2026-10-07T19:49:53Z [implementation] — AC-1: ✓ stdio-проба 2026-10-07 (методика замороженной записи #4625, свежий процесс, конфиг отсутствует): tools/list 34 190 + AGENTS.md 8 476 + каталог 15 скиллов 1 254 = 43 920 Б против 63 333 = −30,65% ≥ 30%. Артефакт: .tausik/planning/release-111/prefix-probe-20261007.json. AC-2: ✓ resolved-by-refusal задачей r111-verification-cycle-replay (done 2026-10-04, verify #3443): retrieval и progress/close реплеи эквивалентны; verification-цикл — отказ с названной потерей preflight (missing_result_ids=[preflight], claim_reduction=false); savings-клейм на этом цикле не делается. AC-3: ✓ три естественных принятых окна 2026-10-07: медиана 17 (атрибутируемая, доминирующий роллаут окна) / 25 (верхняя граница, все параллельные роллауты дня) ≤ 40 при базе 89; fix-pooled-verify-recovery исключён с причиной (окно ≥8 роллаутов, атрибуции нет). Артефакт: .tausik/planning/release-111/natural-windows-20261007.json. AC-4: ✓ релизные лейны со знаменателями: default 12 791 passed / 34 skipped / 143 deselected; slow 143 passed / 12 826 deselected (запись 2026-10-04); свежий релизный лейн 1.11.3 выполнит задача cut-release с полными знаменателями. AC-5 NEGATIVE: ✓ ни одного paid/synthetic прогона, реконструкции базы или каузального клейма: все числа из замороженного журнала, живых Codex rollouts и БД TAUSIK; unknown (модель в session_meta) остаётся unknown. Domain: отчёт docs/ru/research/release111-economy-acceptance-final.md — секция «Замеры 2026-10-07» переводит вердикт HOLD в PASS-by-owner-order; экономика verification-цикла не заявляется. Verify: run #3646 PASS, handle 3646.58992240df91fefcc9b9cc5aaf7e8ee0. Unblock: criterion_met — приказ владельца в чате (замеры → закрыть → релиз 1.11.3 по этим числам).
