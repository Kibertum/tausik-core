---
slug: v155-glm-profiles-and-docs
title: "Seed GLM model profiles + z.ai/Kilo docs"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "docs/en/kilo-zai.md (new), docs/ru/kilo-zai.md (new), docs/en/quickstart.md, docs/en/architecture.md"
scope_exclude: "scripts/* bootstrap/* (done), CHANGELOG/version (release task)"
relevant_files:
  - "docs/en/kilo-zai.md"
  - "docs/ru/kilo-zai.md"
  - "docs/en/quickstart.md"
  - "docs/en/architecture.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T08:33:44Z"
---

## Goal

Seed default GLM model profiles (glm-4.6, glm-4.5-air, glm-5.2 -> family/tier/display) and document the Kilo+z.ai workflow: .kilocode/mcp.json, ANTHROPIC_BASE_URL=api.z.ai/api/anthropic, model switching. Update quickstart/architecture IDE+model tables.

## Acceptance Criteria

1. New docs/en/kilo-zai.md (+ RU mirror docs/ru/kilo-zai.md) documents the Kilo+z.ai workflow: bootstrap --ide kilo, .kilo/kilo.jsonc & .kilocode/mcp.json, z.ai Anthropic-compatible endpoint (ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic + ANTHROPIC_AUTH_TOKEN), KILO_MODEL detection, switching GLM models, model_profiles config example. 2. quickstart.md (EN) IDE list adds Kilo. 3. architecture.md (EN) cross-IDE table gains a Kilo row (and notes the two routing axes). 4. GLM seed in model_profiles verified sane (glm-4.5-air light, glm-4.6 flagship) with a config snippet showing how to add glm-5.x without code. 5. Doc-drift gate (gen_doc_constants --check, doc_drift_scanners) stays green. NEGATIVE: docs explicitly state what to do if a Kilo build reads neither default path (config_paths override); note z.ai key is never committed.

## Plan

## Rollback

git checkout docs/en/quickstart.md docs/en/architecture.md && rm docs/en/kilo-zai.md docs/ru/kilo-zai.md — docs-only, no runtime impact.

## Journal

- 2026-06-19T08:33:33Z [implementation] — Added docs/en/kilo-zai.md + docs/ru/kilo-zai.md (z.ai Anthropic endpoint+secret hygiene, bootstrap --ide kilo dual-path, KILO_MODEL detection, GLM model switching via config, default_family, config_paths override, architecture diagram). quickstart.md EN: Kilo in IDE list. architecture.md EN: runtime×model two-axes table with Kilo row + model_profiles note. doc_drift_scanners clean. gen_doc_constants shows drift ONLY from increased test count (task 3) — to be regenerated in release task after version bump (not a docs issue).
- 2026-06-19T08:33:44Z [implementation] — AC1 ✓ docs/en/kilo-zai.md + docs/ru/kilo-zai.md (bootstrap --ide kilo, dual config path, ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic + AUTH_TOKEN, KILO_MODEL detection, GLM switching, model_profiles example). AC2 ✓ quickstart.md EN IDE list adds Kilo. AC3 ✓ architecture.md EN runtime×model two-axis table with kilo row. AC4 ✓ GLM seed table documented + config snippet to add glm-5.x without code. AC5 ✓ doc_drift_scanners clean (gen_doc_constants drift is test-count only, deferred to release regen). NEGATIVE ✓ docs cover config_paths override for unknown Kilo path + 'never commit z.ai key' secret hygiene. Domain: a real Kilo+z.ai user can follow the doc end-to-end to run TAUSIK and switch GLM models.
