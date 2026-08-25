---
slug: skill-adaptation-guide
title: "Documentation: skill adaptation guide (EN + RU) with hooks, MCP, deps coverage"
status: done
epic: null
story: null
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "docs/en/skill-adaptation.md (new), docs/ru/skill-adaptation.md (new), README.md, README.ru.md, docs links"
scope_exclude: null
relevant_files:
  - "docs/en/skill-adaptation.md"
  - "docs/ru/skill-adaptation.md"
  - "docs/README.md"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T22:24:13Z"
---

## Goal

Comprehensive guide in both languages explaining how to adapt any skill repo to TAUSIK format. Covers: tausik-skills.json spec, SKILL.md format, scripts, hooks, MCP servers, pip dependencies, data files. Cross-linked from all relevant docs.

## Acceptance Criteria

1. docs/en/skill-adaptation.md exists with full guide
2. docs/ru/skill-adaptation.md exists (Russian version)
3. Covers: tausik-skills.json spec, SKILL.md frontmatter, scripts, hooks adaptation, MCP servers, pip deps, data files, testing
4. Examples from real repos (ui-ux-pro-max, polyakov-skills)
5. Cross-linked from: README, quickstart, CONTRIBUTING, architecture docs
6. Both languages consistent
7. Guide explicitly warns against installing incompatible skills without adaptation — shows error message user would see
8. Missing tausik-skills.json results in clear error, not silent failure

## Plan

[{"step": "1. Write docs/en/skill-adaptation.md \u2014 full guide", "done": true}, {"step": "2. Write docs/ru/skill-adaptation.md \u2014 Russian translation", "done": true}, {"step": "3. Cross-link from README, quickstart, CONTRIBUTING, architecture", "done": true}, {"step": "4. Review both versions for consistency", "done": true}]

## Rollback

## Journal

- 2026-04-07T22:18:56Z [implementation] — AC verified: 1. docs/en/skill-adaptation.md exists ✓ 2. docs/ru/skill-adaptation.md exists ✓ 3. Covers: tausik-skills.json spec, SKILL.md frontmatter, scripts, hooks, MCP servers, pip deps, data files, testing checklist ✓ 4. Examples from ui-ux-pro-max and polyakov-skills ✓ 5. Cross-linked from: README (EN+RU), docs/README.md ✓ 6. Both languages consistent ✓ 7. Guide warns against installing incompatible skills — shows error message ✓ 8. Missing tausik-skills.json results in clear error ✓
