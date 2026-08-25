---
slug: r14-hooks-md-pre-commit-truth
title: "Rewrite pre-commit section in hooks docs (mypy plus RAG, not scoped quality gates)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: light
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:36:32Z"
---

## Goal

Release 1.4 docs truthfulness

## Acceptance Criteria

1. memory_markers.py removed from hooks table (it is a library). 2. Hook count recomputed with explicit methodology (16 Python + 1 shell = 17). 3. Install via core.hooksPath and Windows caveat documented. 4. Negative scenario: cmd.exe without Bash refuses script - caveat is explicit.

## Plan

## Rollback

## Journal

- 2026-05-01T00:36:31Z [implementation] — AC verified: 1. memory_markers.py not listed as hook ✓. 2. Count 16+1=17 with methodology ✓ (lib disclaimer + audit-trail callout). 3. core.hooksPath install + Windows caveat documented ✓. 4. Negative - cmd.exe failure is explicit ✓ (caveat lists timeout(1) and POSIX [ -f ... ] dependency).
- 2026-05-01T00:36:31Z [implementation] — Hook count recomputed: '16 Python + 1 shell pre-commit = 17 active hooks ship with v1.4'. Audit-trail '19' callout added to explain prior accounting that wrongly counted memory_markers.py and _common.py.
- 2026-05-01T00:36:31Z [implementation] — Install instructions added (Option A: copy to .git/hooks/; Option B recommended: git config core.hooksPath scripts/hooks). Windows caveat explicit: bash + timeout(1) required, Git Bash/WSL or pre-commit.cmd wrapper. Bypass section: --no-verify, unset core.hooksPath, CI guidance.
- 2026-05-01T00:36:31Z [implementation] — memory_markers.py removed from PostToolUse hooks table in docs/{en,ru}/hooks.md (it is a regex library imported by memory_posttool_audit.py + brain scrubbing pipeline; not a hook). _common.py disclaimer added in intro.
