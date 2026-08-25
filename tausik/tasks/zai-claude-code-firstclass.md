---
slug: zai-claude-code-firstclass
title: "First-class z.ai GLM under Claude Code (subscription) + docs + v1.5.9"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: null
defect_of: null
scope: "docs/en/kilo-zai.md, docs/ru/kilo-zai.md, scripts/tausik_version.py, pyproject.toml, docs/_generated/constants.json, README.md, README.ru.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/model_profiles.py (no speculative model-ID changes), scripts/providers/*, bootstrap/*, harness/* (no code behavior change — this is docs + version only)"
relevant_files:
  - "docs/en/kilo-zai.md"
  - "docs/ru/kilo-zai.md"
  - "scripts/tausik_version.py"
  - pyproject.toml
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-08T17:40:04Z"
---

## Goal

Make GLM-via-z.ai a first-class, discoverable path under Claude Code (not buried as a Kilo-only feature). GLM already works under Claude Code via the Anthropic-compatible endpoint with full SENAR gates and model detection — this ships the DOCS + framing to surface it, plus a version bump. Reframe docs/{ru,en}/kilo-zai.md from 'Kilo-only' to host-agnostic z.ai GLM with Claude Code as the primary path; add subscription-not-per-token framing + the billing smoke-test caveat (verify Coding Plan quota bills via /api/anthropic). Bump 1.5.8 -> 1.5.9 with CHANGELOG (ru+en). Part of epic universal-vscode-extension (GLM-by-subscription is decoupled from the extension, Decision #126).

## Acceptance Criteria

1. docs/{ru,en}/kilo-zai.md reframed host-agnostic: intro no longer says GLM is a Kilo-only feature; a prominent 'GLM under Claude Code' section documents the exact env vars (ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic + ANTHROPIC_AUTH_TOKEN), states it keeps ALL SENAR gates (host stays Claude Code), and frames z.ai Coding Plan as subscription (not per-token). 2. A billing smoke-test caveat is documented (verify Coding Plan quota bills via the /api/anthropic endpoint before relying on it). 3. Version reads 1.5.9 consistently in pyproject.toml, scripts/tausik_version.py, docs/_generated/constants.json, and both README badges — the doc-drift scanner passes. 4. CHANGELOG.md and CHANGELOG.ru.md both have a [1.5.9] entry describing the first-class Claude Code + z.ai GLM docs. 5. tausik verify passes (no blocking gate failures). NEGATIVE/BOUNDARY: 6. Version-drift is caught, not silently shipped — if any of the four version literals is left at 1.5.8 while others read 1.5.9, the doc-drift scanner (scripts/doc_drift_scanners.py) must FAIL; confirm the scanner is green only when all agree. 7. No broken links introduced — kilo-zai.md keeps its filename (referenced from README ru+en, quickstart, architecture), so those relative links still resolve; retitling content must not orphan any existing reference.

## Plan

## Rollback

git revert the commit; version literals and CHANGELOG entries revert cleanly; docs are additive/reframing only with no code behavior change.

## Journal

- 2026-07-08T17:38:49Z [implementation] — Docs: reframed docs/{ru,en}/kilo-zai.md host-agnostic — new §1 'GLM under Claude Code (subscription, full gates)' with exact env vars, secret hygiene, subscription-not-per-token framing, and billing smoke-test caveat. Filename kept (README/quickstart/architecture links intact). Version bumped 1.5.8->1.5.9 in tausik_version.py, pyproject.toml, README badges (ru+en); constants.json regenerated via gen_doc_constants.py.
- 2026-07-08T17:40:03Z [implementation] — AC verified: 1. ✓ docs/{en,ru}/kilo-zai.md reframed host-agnostic — new §1 'GLM under Claude Code (recommended — subscription, full gates)' with exact env vars (ANTHROPIC_BASE_URL=/api/anthropic + ANTHROPIC_AUTH_TOKEN), 'host stays Claude Code → all SENAR gates fire', subscription-not-per-token framing. 2. ✓ Billing smoke-test caveat added (verify Coding-Plan quota bills via /api/anthropic) in both mirrors. 3. ✓ Version 1.5.9 consistent: pyproject.toml, scripts/tausik_version.py, docs/_generated/constants.json (grep confirmed "tausik_version":"1.5.9"), README.md + README.ru.md badges. 4. ✓ CHANGELOG.md + CHANGELOG.ru.md both have [1.5.9] — 2026-07-08 entry. 5. ✓ tausik verify passed=True (gates hadolint, pytest). 6. ✓ (negative) gen_doc_constants.py drift-reporter (scripts/doc_drift_scanners.py _PY_VERSION_RE) ran clean only after all four literals agreed at 1.5.9 — a leftover 1.5.8 would have been reported. 7. ✓ (boundary) kilo-zai.md filename unchanged; README/quickstart/architecture relative links still resolve.
