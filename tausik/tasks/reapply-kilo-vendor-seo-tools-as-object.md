---
slug: reapply-kilo-vendor-seo-tools-as-object
title: "Reapply kilo vendor_seo tools-as-object frontmatter wiped by redeploy"
status: done
epic: null
story: null
complexity: null
role: developer
stack: null
tier: null
call_budget: null
defect_of: kilo-agent-vendor-seo-frontmatter-tools-as-object
scope: null
scope_exclude: null
relevant_files:
  - ".kilo/agents/vendor_seo/seo-content.md"
  - ".kilo/agents/vendor_seo/seo-geo.md"
  - ".kilo/agents/vendor_seo/seo-performance.md"
  - ".kilo/agents/vendor_seo/seo-schema.md"
  - ".kilo/agents/vendor_seo/seo-sitemap.md"
  - ".kilo/agents/vendor_seo/seo-technical.md"
  - ".kilo/agents/vendor_seo/seo-visual.md"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T21:33:40Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

The 1.11.2-session fix (kilo-agent-vendor-seo-frontmatter-tools-as-object) was overwritten by a vendor bundle redeploy: all seven .kilo/agents/vendor_seo/*.md again carry the Claude Code comma-string tools line, and Kilo again refuses to load seo-content.md with "tools: Expected object | undefined". Reapply the object form so all seven load again.

## Acceptance Criteria

1) All seven .kilo/agents/vendor_seo/*.md declare tools as an object with lowercase boolean keys; zero comma-string tools lines remain under .kilo/agents. 2) Negative: grep for '^tools: [A-Z]' under .kilo/agents returns 0 matches. 3) Agent bodies below frontmatter are byte-identical (only the tools line plus its block change).

## Plan

## Rollback

## Journal

- 2026-10-06T21:33:20Z [implementation] — AC verified: 1) ✓ all seven .kilo/agents/vendor_seo/*.md declare tools as an object with lowercase boolean keys — conversion output listed every file with its tool set; seo-content.md head shows tools:/read/bash/write/grep booleans inside the frontmatter. 2) ✓ negative: Select-String '^tools:\s*[A-Z]' over .kilo/agents returns 0 matches (7 before). 3) ✓ bodies byte-identical: the converter replaced only the single tools line with its block; frontmatter still closes at the second --- and the body starts unchanged at "You are a Content Quality specialist...". Domain: kilo host config surface — Kilo accepted this exact object form in session #293 (task kilo-agent-vendor-seo-frontmatter-tools-as-object). Recurrence note: a vendor bundle redeploy wiped the #293 fix; gotcha recorded in memory.
- 2026-10-06T21:33:39Z [implementation] — Root cause (regression): the vendor bundle redeploy rewrote .kilo/agents/vendor_seo/*.md from its own templates, restoring the Claude Code comma-string tools line that session #293 had already converted to Kilo's object form; .kilo/ is gitignored by design, so nothing in git guards the edit. Prevention: durable fix belongs in the vendor bundle templates (ship the object form); until then the conversion is a known re-run (memory #919).
