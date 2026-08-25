---
slug: rollout-v157-all-projects
title: "Roll out framework v1.5.7 to all TAUSIK projects under D:\\Work"
status: done
epic: null
story: null
complexity: null
role: null
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: "Per-project .tausik-lib pointer + .claude/.cursor/.kilo/.qwen deployed harness + generated configs; core is source, already released."
scope_exclude: "Project source code (non-framework paths), package manifests, user docs. Do not force-push. Do not touch repos' unrelated WIP."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-06T12:27:56Z"
---

## Goal

Propagate the v1.5.7 cp1252 decode fix to all 30 TAUSIK-enabled projects under D:\Work by bumping each .tausik-lib submodule to 7eb4015 and re-bootstrapping deployed harness, then commit+push each. Preserve any custom skills for later extraction to a gitlab tausik/skills repo.

## Acceptance Criteria

1) Each reachable project's .tausik-lib points to 7eb4015 and deployed harness re-bootstrapped to v1.5.7. 2) SessionStart hook runs clean (exit 0, valid JSON) in each. 3) Framework-only paths committed (no source WIP swept); pushed to each origin where reachable. 4) Custom skills (diff, standard) preserved, not clobbered, and collected for the skills repo. Failures reported per-repo.

## Plan

## Rollback

Per repo: git revert the framework-update commit, or reset .tausik-lib to prior submodule SHA + git checkout .claude. Nothing pushed is history-rewriting (fast-forward only).

## Journal

- 2026-07-06T12:27:06Z [implementation] — Rollout complete. 30/30 projects functionally fixed (lib at v1.5.7 tag [7eb4015 gitlab / 7c311e8 github], session_start.py fix present, live hook verified). Pushed: 23 repos. Blocked (committed locally, infra/access/WIP — need manual push): cyrm.ru (TLS handshake gitlab.cyrm.tech), archive/nomad (403 no-access), YPN (remote main diverged + local source WIP blocks rebase), azimuth_pwa (no 'origin' remote configured). No-push-needed: BabelChat + pdf-signer (framework untracked/working-tree-only), seabattle (chore already on origin). Key gotcha: submodule remotes split ~14 github / ~15 gitlab; github orphan has different SHAs so checkout must use the v1.5.7 TAG resolved via rev-list, not a hardcoded SHA. Custom skills: 'diff' = official stub (false positive); 'standard' in kibertum-org = genuine custom (corporate-standards authoring) — preserved, backed up, pending formalization into gitlab tausik/skills repo.
- 2026-07-06T12:27:18Z [implementation] — AC1 ✓ verify_state.sh: all 30 repos' .tausik-lib at v1.5.7 tag commit (7eb4015/7c311e8), re-bootstrapped. AC2 ✓ SessionStart hook exits 0 with valid JSON in each (script per-repo verify + spot checks). AC3 ✓ framework-only allowlist staging (.tausik-lib/.claude/.cursor/.kilo/.qwen/.mcp.json/CLAUDE.md/AGENTS.md) — no source WIP swept; 23 pushed, 4 blocked by infra/access/WIP (documented, committed locally). AC4 ✓ custom skill 'standard' (kibertum-org) preserved + backed up; 'diff' confirmed official (false positive). Negative: pdf-signer submodule had local drift blocking checkout -> force-checkout to canonical per directive; YPN rebase correctly refused on dirty tree (WIP protected, not touched).
- 2026-07-06T12:27:38Z [implementation] — AC1-4 verified (see prior log). 30/30 functionally fixed; 23 pushed; 4 blocked by infra/access/WIP (committed locally); custom 'standard' skill preserved. Core code unchanged by this task (downstream git ops only) — verify #934 green.
- 2026-07-06T12:27:52Z [implementation] — Verification checklist (SENAR Rule 5): [scope] Only framework-owned paths staged (.tausik-lib/.claude/.cursor/.kilo/.qwen/.mcp.json/CLAUDE.md/AGENTS.md) via explicit allowlist — verified no source WIP in any commit (git diff --cached inspected; krasnogorskaya 365 / LegalOS 49 source files untouched). [tests] Per-repo live SessionStart hook executed post-bootstrap → exit 0 + valid JSON; core suite 4313 passed underpins the fix. [security] No secrets touched; pushes are fast-forward only (no --force); bash_firewall/git_push_gate honored (no bypass); external-remote pushes that failed did so on TLS/403 and were left committed-local, not force-pushed. [edge-cases] github vs gitlab SHA divergence (tag-resolve), dirty submodule (pdf-signer force-checkout), no-origin repo (azimuth_pwa), diverged+WIP repo (YPN left untouched), untracked-framework repos (BabelChat/pdf-signer no-op), custom skill preservation (standard). [domain] All 30 libs resolve to a commit whose session_start.py contains encoding="utf-8" — the exact fix — confirming real-world correctness beyond tests.
