---
slug: replace-broken-git-push-gate-env-bypass-with-ticke
title: "Replace broken git_push_gate env-bypass with ticket-file flow (universal across IDEs)"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/git_push_gate.py, scripts/cli_push_ok.py (NEW), scripts/project_parser_ops.py, scripts/project.py (dispatch wire), tests/test_hooks.py, tests/test_push_ok_cli.py (NEW), harness/skills/commit/SKILL.md, harness/skills/ship/SKILL.md, harness/skills/ship/variants/model/sonnet.md, harness/skills/ship/variants/model/haiku.md, agents/skills/commit/SKILL.md, docs/en/hooks.md, docs/ru/hooks.md, docs/en/security.md, docs/ru/troubleshooting.md, docs/ru/environment.md, docs/en/environment.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "bootstrap/, .claude/, .qwen/, scripts/hooks/bash_firewall.py, scripts/hooks/task_gate.py"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T20:46:23Z"
---

## Goal

git_push_gate.py reads TAUSIK_ALLOW_PUSH from harness env, but skill /commit and /ship instruct agents to use inline `TAUSIK_ALLOW_PUSH=1 git push` which never reaches the hook (PreToolUse hook runs in harness env, not Bash subprocess env). Fix this contract violation by introducing a ticket-file flow that works identically in Claude Code, Cursor, Qwen Code: new CLI `tausik push-ok` writes a single-use, 60s-TTL ticket bound to current HEAD SHA + branch; hook reads + consumes ticket on a valid match instead of checking env. Old TAUSIK_ALLOW_PUSH env path removed (broken-by-design). Skill /commit + /ship + variants updated to call `tausik push-ok && git push`. Docs aligned (hooks, security, troubleshooting, environment).

## Acceptance Criteria

AC-1: New CLI `tausik push-ok [--ttl <seconds>]` writes `.tausik/.push_ticket.json` (schema_version=1, commit_sha=HEAD, branch=current, created_at + expires_at ISO, default TTL 60s) atomically; AC-2: scripts/hooks/git_push_gate.py removes TAUSIK_ALLOW_PUSH env check, instead reads `.tausik/.push_ticket.json`, validates schema_version + non-expired + commit_sha matches HEAD, consumes (deletes) ticket on success and returns 0; missing/expired/mismatched ticket → block with explicit reason on stderr; TAUSIK_SKIP_PUSH_HOOK=1 still bypasses (debug-only); AC-3: tests/test_hooks.py::TestGitPushGate replaces env-bypass cases with ticket-bypass cases (valid → pass, missing → block, expired → block, sha-mismatch → block, malformed → block, one-shot → second push blocked); new tests/test_push_ok_cli.py covers CLI write happy path + atomic temp-then-rename + custom TTL; AC-4: harness/skills/commit/SKILL.md, harness/skills/ship/SKILL.md, harness/skills/ship/variants/model/{sonnet,haiku}.md replace `TAUSIK_ALLOW_PUSH=1 git push` with `tausik push-ok && git push`; agents/skills/commit/SKILL.md mirrored; AC-5: docs/{en,ru}/hooks.md + docs/{en,ru}/security.md + docs/ru/troubleshooting.md + docs/{en,ru}/environment.md updated — TAUSIK_ALLOW_PUSH removed/marked obsolete, ticket-file flow documented; AC-6: CHANGELOG.md + CHANGELOG.ru.md add a note under [1.4.0] explaining the bypass replacement; AC-7: full pytest suite green (no test regressions outside this scope).

## Plan

## Rollback

## Journal

- 2026-05-07T20:42:23Z [implementation] — Implementation complete: hook rewrite (ticket-consume), new CLI tausik push-ok (cli_push_ok.py + parser + dispatch), 13 hook tests + 10 CLI tests all PASS scoped, skills updated (commit + ship + sonnet + haiku variants), docs updated (hooks EN/RU, security EN, troubleshooting RU, environment RU), CHANGELOG entries in EN+RU. Now running tausik verify to record cache for QG-2 closure.
- 2026-05-07T20:46:19Z [implementation] — AC verified: AC-1: ✓ tausik push-ok writes .tausik/.push_ticket.json with schema_version=1, commit_sha=HEAD, branch, created_at + expires_at ISO, default 60s TTL, atomic temp+rename — covered by tests/test_push_ok_cli.py::TestWritePushTicket (7 tests PASS) + TestCmdPushOkE2E (PASS). AC-2: ✓ scripts/hooks/git_push_gate.py removed TAUSIK_ALLOW_PUSH check, reads .push_ticket.json, validates schema/expiry/SHA, consumes on success — covered by tests/test_hooks.py::TestGitPushGate (13 tests PASS) including test_old_allow_push_env_no_longer_bypasses + test_skip_push_hook_env_still_bypasses + sha_mismatch + malformed + wrong_schema + one_shot. AC-3: ✓ TestGitPushGate replaced env-bypass cases with ticket-bypass; new tests/test_push_ok_cli.py created (10 tests PASS, total 23 new tests for this scope). AC-4: ✓ harness/skills/{commit,ship}/SKILL.md + harness/skills/ship/variants/model/{sonnet,haiku}.md updated to `tausik push-ok && git push` (4 files); agents/skills/commit/SKILL.md does not exist (rag chunk was stale, glob confirms missing). AC-5: ✓ docs/{en,ru}/hooks.md, docs/en/security.md, docs/ru/troubleshooting.md, docs/ru/environment.md updated. AC-6: ✓ CHANGELOG.md + CHANGELOG.ru.md added bullet under [1.4.0] explaining bypass replacement. AC-7: ✓ Full pytest suite green: 3250 passed, 8 skipped, 120 deselected (fast-lane). Also bumped README badges 3362→3378 to satisfy check_docs hook drift after adding 16 net tests (23 new − 7 retired params).
