---
slug: kilo-agent-vendor-seo-frontmatter-tools-as-object
title: "Kilo agent vendor_seo frontmatter: tools as object, not a comma string"
status: done
epic: null
story: null
complexity: null
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
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
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T20:07:59Z"
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

Kilo refuses the seven vendored SEO agent definitions with tools: Expected object | undefined — the frontmatter was written in Claude Code subagent format; Kilo requires a per-tool object. Convert all seven to the object form Kilo accepts.

## Acceptance Criteria

1) All seven .kilo/agents/vendor_seo md files declare tools as an object with boolean values (lowercase names), no comma-string form remains. 2) Negative: the rejected spelling with comma-separated tool names appears zero times under .kilo/agents. 3) Agent body below the frontmatter is byte-identical (only frontmatter changed).

## Plan

## Rollback

## Journal

- 2026-10-06T20:00:25Z [implementation] — AC-1: check - all seven .kilo/agents/vendor_seo md files now declare tools as an object (read/bash/write/glob/grep/webfetch booleans), verified by Get-Content of seo-visual.md and the conversion script output listing every file with its tool list. AC-2: check - grep over .kilo/agents for the comma-string tools line returns 0 matches after the fix (7 before). AC-3: check - only the frontmatter line changed: the script replaced exactly the matched tools line and one trailing blank line; git diff --stat shows 7 files, each 1 hunk. Root cause: frontmatter authored in Claude Code subagent format (tools as a comma string); Kilo schema wants object | undefined. Domain: kilo host config surface.
- 2026-10-06T20:07:54Z [implementation] — AC verified: 1. ✓ all seven .kilo/agents/vendor_seo md files declare tools as an object with boolean values (conversion script listed each file with its tool set; Get-Content seo-visual.md shows the object form) 2. ✓ negative: grep over .kilo/agents for the comma-string tools line returns zero matches after the fix (seven before) 3. ✓ only frontmatter changed: the fixer replaced exactly the tools line plus one blank line per file; bodies untouched (git diff shows one hunk per file).
