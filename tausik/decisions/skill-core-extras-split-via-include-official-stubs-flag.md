---
slug: skill-core-extras-split-via-include-official-stubs-flag
task: v14b-skill-core-cleanup
date: "2026-05-03"
edges: []
---

## Decision

Skill core/extras split via include_official_stubs flag + brain conditional gating

## Rationale

Default bootstrap deploys ONLY 12 source skills (was: 38 = 14 source + 24 registry stubs). Brain is gated on brain.enabled in .tausik/config.json (set by tausik brain init). Registry stubs (skills-official) opt-in via --include-official. Token saving: −1,040/turn in system-reminder (from ~1,520 → ~480). Backward-compat: explicit installed_skills config still wins. Live-tested in this session: default→12, brain.enabled=true→13, --include-official→38.
