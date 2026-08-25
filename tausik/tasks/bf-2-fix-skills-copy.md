---
slug: bf-2-fix-skills-copy
title: "Bootstrap: deploy all agents/skills/* to .claude/skills/"
status: done
epic: v13-mcp-and-discipline
story: bootstrap-deploy-fix
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: "bootstrap/bootstrap_copy.py copy_skills function only"
scope_exclude: "DEFAULT_CONFIG, ALL_EXTENSION_SKILLS, registry resolver, vendor download path"
relevant_files:
  - "bootstrap/bootstrap_copy.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T00:45:30Z"
---

## Goal

All 15 core skills from agents/skills/* deployed to .claude/skills/* on bootstrap run. Co-existence with external skills (installed via tausik skill install) preserved — external survive. /review uses TAUSIK's 6-agent SKILL.md after fix.

## Acceptance Criteria

1. copy_skills() force-includes ALL skills from agents/skills/ regardless of config (built-in = source of truth)
2. External skill resolution (registry/vendor/installed) preserved unchanged for non-built-ins
3. Cleanup pass (preserve set) does NOT strip force-included built-ins
4. After fresh bootstrap, .claude/skills/ contains all 15 built-in skills as full copies (review/brain/commit/debug/interview/markitdown/ship/skill-test/test + 6 already-deployed)
5. After fresh bootstrap, external skills (audit/diff/init/etc) still appear (as stubs or full copies depending on installed_skills)
6. .tausik/config.json no longer needs to track core_skills for built-in deployment to work
NEGATIVE: If a skill exists in BOTH agents/skills/ AND vendor/registry, built-in version wins (no shadowing risk). Empty agents/skills/ dir (theoretical) — do not crash, fall back to current config-driven behavior.

## Plan

## Rollback

## Journal

- 2026-04-26T00:45:30Z [planning] — AC verified: 1. copy_skills force-includes via os.listdir(builtin_dir) before config lookup ✓ 2. External resolution preserved (registry/vendor/installed paths untouched) ✓ 3. Cleanup preserve set includes builtin_names via dict.fromkeys union ✓ 4. Bootstrap shows 'Skills: 37 copied' — all 15 builtins + 22 external in .claude/skills/ ✓ 5. External skills (audit/init/diff/docs) still appear ✓ 6. Config drift no longer blocks built-in deployment ✓ NEGATIVE: built-in wins on collision via dict.fromkeys order ✓
