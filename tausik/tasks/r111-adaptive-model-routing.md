---
slug: r111-adaptive-model-routing
title: "1.11: route work to economical host models"
status: done
epic: release-111-economy-draft
story: release111-context-and-workflow
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/model routing, delegation and telemetry; host capability adapters; task/start/run/ship skills; focused tests; EN/RU model routing documentation and 1.11 changelog"
scope_exclude: "Automatic mutation of an unsupported running session; unlimited parallel agents; silent model downgrade; provider credentials; unrelated host refactors; release publication"
relevant_files:
  - "scripts/model_route.py"
  - "scripts/model_profiles.py"
  - "scripts/model_routing_session.py"
  - "scripts/model_routing_adherence.py"
  - "scripts/service_delegate.py"
  - "scripts/service_task.py"
  - "scripts/service_task_team.py"
  - "scripts/skill_profile_detect.py"
  - "scripts/providers/codex.py"
  - "scripts/usage_observation.py"
  - "tests/test_adaptive_model_route.py"
  - "tests/test_model_profiles.py"
  - "tests/test_providers.py"
  - "tests/test_model_routing_session.py"
  - "tests/test_task_next_model_hint.py"
  - "tests/test_ow_delegate.py"
  - "tests/test_routing_adherence.py"
  - "tests/test_usage_observation.py"
  - "tests/test_cross_model_parity_gate.py"
  - "tests/test_task_start_model_banner.py"
  - "harness/skills/task/SKILL.md"
  - "harness/skills/run/SKILL.md"
  - "harness/skills/ship/SKILL.md"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/ru/research/model-routing-matrix.md"
  - "docs/en/codex-economy-baseline.md"
  - "docs/ru/codex-economy-baseline.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/model_route.py"
  - "scripts/model_profiles.py"
  - "scripts/model_routing_session.py"
  - "scripts/model_routing_adherence.py"
  - "scripts/service_delegate.py"
  - "scripts/service_task.py"
  - "scripts/service_task_team.py"
  - "scripts/skill_profile_detect.py"
  - "scripts/providers/codex.py"
  - "tests/test_adaptive_model_route.py"
  - "tests/test_model_profiles.py"
  - "tests/test_providers.py"
  - "tests/test_model_routing_session.py"
  - "tests/test_task_next_model_hint.py"
  - "tests/test_ow_delegate.py"
  - "tests/test_routing_adherence.py"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/ru/research/model-routing-matrix.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/usage_observation.py"
  - "tests/test_usage_observation.py"
  - "docs/en/codex-economy-baseline.md"
  - "docs/ru/codex-economy-baseline.md"
  - "harness/skills/task/SKILL.md"
  - "harness/skills/run/SKILL.md"
  - "harness/skills/ship/SKILL.md"
  - "tests/test_cross_model_parity_gate.py"
  - "tests/test_task_start_model_banner.py"
scope_tools: []
depends_on:
  - r111-runtime-observation-contract
completed_at: "2026-10-01T16:46:04Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Extend TAUSIK's existing Claude model guidance into a provider-neutral execution route that selects economical subagent models and reasoning levels for Codex and Kilo/GLM when the host exposes that control, while never pretending it can switch an unsupported running session.

## Acceptance Criteria

AC-1 A provider-neutral route resolves phase, complexity and risk to a configured model family, reasoning effort and speed for Claude, OpenAI/Codex and GLM; selected values and provenance are explicit. AC-2 Codex can apply the route when spawning a bounded subagent; existing Claude delegation remains compatible; Kilo/GLM applies only through a verified host surface. An unsupported running-session switch is reported as advisory, never as applied. AC-3 Economy policy prevents recursive or shotgun delegation, keeps verification/evidence/task closure with the owner, and escalates to a stronger model only for named risk or failed-quality signals. AC-4 Telemetry distinguishes recommended, applied, rejected and unavailable routes and can compare accepted-task tokens plus retries without double-counting cache or reasoning subsets. AC-5 Behavioral tests cover unknown host/model, missing capability, stale configuration and failed spawn without changing the current model or weakening QG-0/QG-2. AC-6 Codex is exercised first; Claude routing regressions remain green; Kilo/GLM limitations or live evidence are stated exactly without fabricated parity.

## Plan

[{"step": "Inventory existing Claude routing and each host's real model-control surface; freeze a provider-neutral route contract.", "done": true}, {"step": "Implement bounded Codex-first route application, preserve Claude behavior, add Kilo/GLM only where a verified surface exists, and record applied versus advisory outcomes.", "done": true}, {"step": "Measure accepted-task quality/cost on the frozen corpus, document host limits, and keep release acceptance dependent on live evidence rather than fixture parity.", "done": true}]

## Rollback

Remove the provider-neutral route adapter and host application layer, retaining the existing Claude recommendation/delegation behavior and recorded telemetry schema compatibility.

## Journal

- 2026-10-01T16:31:24Z [implementation] — Implemented provider-neutral routes over the existing Claude capability matrix. Codex reads the active model from its bounded native journal tail and routes simple workers to Terra/low/standard, normal complex work to Sol/medium, and named high risk to Astra; failed quality signals escalate one tier. Claude delegation remains spawn-capable. Kilo/GLM resolves its family but remains advisory pending a verified host spawn API. Root switching is always unsupported. Delegation depth is one, active workers block nested/parallel delegation, and selected becomes applied only at worker task_start. Focused routing/delegation suite: 188 passed before docs.
- 2026-10-01T16:35:55Z [implementation] — Live Codex detection resolved gpt-5.6-sol. Normal simple route: Terra/low/standard; named high-risk planning: Astra/high/standard. Accepted-task summarizer counts input+output once, reports cache/reasoning as subsets, deduplicates response IDs and takes retries from task attempts. Frozen live token pairs remain unmeasured until exact task attribution; release acceptance retains that dependency. Focused behavior suite: 105 passed.
- 2026-10-01T16:45:24Z [implementation] — AC verified: 1. PASS — tests/test_adaptive_model_route.py covers phase/complexity/risk, Claude/OpenAI/GLM family, reasoning, speed and provenance. 2. PASS — live Codex resolved gpt-5.6-sol and produced Terra/low/standard; tests/test_ow_delegate.py proves selected becomes applied only on worker task_start; Claude remains spawn-capable; Kilo is unavailable/advisory. 3. PASS — max depth 1 blocks nested/parallel workers, quality signals escalate one tier, and coordinator ownership is stated in task/run/ship skills. 4. PASS — schema-2 route outcomes distinguish selected/applied/rejected/unavailable; tests/test_usage_observation.py proves exact accepted-task totals deduplicate responses, count input+output once and report retries from attempts. 5. PASS — unknown host/model, stale override, unsupported capability, invalid signals and abandoned spawn remain unapplied; verify run #3244 passed. 6. PASS — current Codex journal route exercised live; Claude compatibility tests and 105-file scoped verify passed; Kilo/GLM limitation is explicit in EN/RU docs.
- 2026-10-01T16:46:03Z [implementation] — AC verified: 1. PASS — provider-neutral route tests cover phase, complexity, risk, family, reasoning, speed and provenance. 2. PASS — live Codex route and worker-start application tested; Claude compatible; Kilo advisory. 3. PASS — depth one, no parallel worker, named quality escalation, coordinator closure. 4. PASS — distinct route outcomes and exact accepted-task token/retry summary without subset double count. 5. PASS — unknown, stale, unsupported and abandoned routes remain unapplied; verify #3244 passed. 6. PASS — Codex exercised live, Claude regressions green, Kilo limit documented.
- 2026-10-01T16:46:12Z [done] — AC-1: ✓ route contract tested. AC-2: ✓ worker application tested. AC-3: ✓ nested delegation refused. AC-4: ✓ token subsets not double-counted. AC-5: ✓ unsupported/stale routes stay unapplied. AC-6: ✓ Codex live; Claude green; Kilo advisory documented. Negative: unknown host, stale config, invalid signal and failed spawn cannot claim application. Domain: current Codex journal resolved Sol and produced an executable Terra worker route; exact task linkage remains required before any savings claim.
