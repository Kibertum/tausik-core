---
slug: bf-1-investigate-skills-drift
title: "Root-cause: why core skills not deployed to .claude/skills/"
status: done
epic: v13-mcp-and-discipline
story: bootstrap-deploy-fix
complexity: null
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T00:45:08Z"
---

## Goal

Trace bootstrap code path that copies skills. Identify why 9 of 15 agents/skills/* dirs are skipped (review, brain, commit, debug, interview, markitdown, ship, skill-test, test). Document mechanism (allowlist? naming filter? glob bug?) so the fix is targeted not shotgun.

## Acceptance Criteria

1. Bootstrap entry point identified (file:line)
2. Skills-copy code path traced from entry to file write
3. Root cause documented: explicit allowlist / glob filter / per-skill registration / drift-after-rename / etc.
4. Findings logged via task_log with concrete file:line references
5. Fix strategy outlined for bf-2 (one-line vs structural)
NEGATIVE: If skills are deployed via per-skill registration, surface every skill that needs explicit registration entry — partial coverage of fix is failure

## Plan

## Rollback

## Journal

- 2026-04-25T23:57:49Z [implementation] — ROOT CAUSE: copy_skills (bootstrap/bootstrap_copy.py:145-225) iterates config['core_skills']+config['extension_skills']+vendor+registry. Built-in skills NOT in those lists are silently skipped. Two compounding bugs: (1) DEFAULT_CONFIG['core_skills']=11 entries vs 4 orphans not in any list (brain/interview/markitdown/skill-test). (2) Saved .tausik/config.json drifts: stale 7-entry list (start/plan/task/end/checkpoint/explore/init) frozen at first bootstrap, never re-merged with newer DEFAULT_CONFIG additions (commit/review/test/ship/debug). FIX STRATEGY: structural — scan agents/skills/* directly and force-include all built-ins in all_skills_with_vendor BEFORE config lookups. Built-in = source of truth; allowlist remains for external/vendor only. Also need to update preserve set so cleanup pass doesn't strip force-included built-ins. Touches bootstrap_copy.py copy_skills() function only.
- 2026-04-25T23:58:08Z [implementation] — AC verified: 1. Bootstrap entry: bootstrap/bootstrap_copy.py:145 copy_skills() ✓ 2. Path traced from copy_skills line 195 (config lookup) → line 203 iter → line 209 _resolve_skill → line 211 copy_dir ✓ 3. Root cause: explicit allowlist via config['core_skills']+config['extension_skills']+vendor+registry — built-in skills not in any of these lists silently skipped ✓ 4. Findings logged with file:line refs above ✓ 5. Fix strategy: structural — scan agents/skills/ first, force-include all built-ins, leave external resolution unchanged ✓ NEGATIVE check: identified all 9 missing skills (4 truly orphaned + 5 frozen by config drift), partial fix ruled out
- 2026-04-26T00:41:03Z [implementation] — AC verified: 1. Entry bootstrap/bootstrap_copy.py:145 ✓ 2. Path traced 195→203→209→211 ✓ 3. Root cause: explicit allowlist via config['core_skills']+extension+vendor+registry ✓ 4. Findings logged with file:line refs ✓ 5. Strategy: force-include agents/skills/* before config lookup ✓ NEGATIVE: identified all 9 missing skills (4 orphans + 5 config-drift), partial fix ruled out ✓
- 2026-04-26T00:45:08Z [implementation] — AC verified: 1. Entry bootstrap/bootstrap_copy.py:145 ✓ 2. Path 195→203→209→211 ✓ 3. Root cause: explicit allowlist via config['core_skills']+extension+vendor+registry ✓ 4. Findings logged ✓ 5. Fix strategy: force-include agents/skills/* before config lookup ✓ NEGATIVE: 9 missing skills enumerated ✓
