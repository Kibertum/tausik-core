---
slug: skill-install-system
title: "Skill install system: repo add, install, activate for TAUSIK-native repos"
status: done
epic: null
story: null
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/skill_manager.py (new), scripts/project_cli_extra.py, agents/claude/mcp/project/tools_extra.py, agents/claude/mcp/project/handlers.py, bootstrap/bootstrap_venv.py"
scope_exclude: "bootstrap/bootstrap.py, bootstrap/bootstrap_vendor.py (legacy — don't touch), .claude/ generated files"
relevant_files:
  - "scripts/skill_manager.py"
  - "scripts/skill_repos.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_parser.py"
  - "scripts/gate_runner.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T22:38:33Z"
---

## Goal

Users can add TAUSIK-compatible skill repos via CLI/MCP, install individual skills with auto-deps, and activate/deactivate them. Only tausik-skills.json format supported — incompatible repos get a clear message with link to adaptation guide.

## Acceptance Criteria

1. tausik-skills.json format spec defined and documented
2. skill_manager.py: clone_repo (shallow clone), detect_format (tausik-native or incompatible), scan_skills, copy_skill_to_ide, install_skill_deps
3. CLI: skill repo add/remove/list, skill install/uninstall — all work
4. MCP: tausik_skill_install, tausik_skill_uninstall, tausik_skill_repo_add, tausik_skill_repo_remove, tausik_skill_repo_list
5. Per-skill requirements.txt auto-installed into .tausik/venv/
6. Incompatible repos get clear error + link to adaptation guide
7. Works cross-IDE (claude, cursor, windsurf)
8. Tests pass

## Plan

[{"step": "1. Read existing skill management code: project_cli_extra.py (activate/deactivate/list), bootstrap_copy.py (copy_skills), bootstrap_vendor.py (sync_deps), handlers.py", "done": true}, {"step": "2. Create scripts/skill_manager.py \u2014 core logic: clone_repo, detect_format, scan_skills, copy_skill, install_deps, remove_skill", "done": true}, {"step": "3. Add CLI commands to project_cli_extra.py: skill repo add/remove/list, skill install/uninstall", "done": true}, {"step": "4. Add MCP tools to tools_extra.py + handlers", "done": true}, {"step": "5. Add per-skill pip deps to bootstrap_venv.py", "done": true}, {"step": "6. Write tests/test_skill_manager.py", "done": true}, {"step": "7. Run full test suite + review", "done": true}]

## Rollback

## Journal

- 2026-04-07T22:18:35Z [implementation] — All review findings addressed: 1) URL validation (whitelist https/ssh/git@), 2) path traversal prevention via _validate_path_inside, 3) pip install warning for untrusted manifests, 4) git pull failure warning, 5) 11 new tests (security, clone_repo mocked). Total: 879 tests pass, 0 warnings.
- 2026-04-07T22:18:52Z [implementation] — AC verified: 1. tausik-skills.json spec defined in skill-adaptation guide ✓ 2. skill_manager.py: clone_repo, detect_format, scan_skills (find_skill_source), copy_skill, install_skill_deps ✓ 3. CLI: skill repo add/remove/list + skill install/uninstall all work ✓ 4. MCP: 5 new tools (tausik_skill_install/uninstall/repo_add/repo_remove/repo_list) ✓ 5. Per-skill requirements via requires field auto-installed ✓ 6. Incompatible repos get clear error with adaptation guide link ✓ 7. Cross-IDE: cursor files synced, ide_utils detect_ide used ✓ 8. 879 tests pass with -W error ✓
- 2026-04-07T22:28:12Z [implementation] — Split skill_manager.py (526→355 lines) + skill_repos.py (200 lines) to pass filesize gate. All imports updated in CLI, MCP handlers, tests. 879 tests pass.
