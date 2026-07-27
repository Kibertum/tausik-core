---
slug: shared-hook-helpers-in-scripts-hooks-common-py-last-user
task: brain-bypass-marker-hardening
date: "2026-04-24"
edges: []
---

## Decision

Shared hook helpers in scripts/hooks/_common.py (last_user_prompt_text + marker_present_anchored) instead of per-hook duplication

## Rationale

The bypass-marker substring check was duplicated in memory_pretool_block.py and brain_search_proactive.py. Review2 found two new bypass classes (U+2028, tilde fences, indented code) that needed to be fixed in BOTH files. With shared helpers, a future third hook automatically inherits the hardening. Cost: one import + one sys.path.insert per hook.
