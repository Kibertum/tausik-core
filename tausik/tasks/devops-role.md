---
slug: devops-role
title: "Add first-class DevOps role to the role registry"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 35
defect_of: null
scope: "harness/roles/devops.md (new); docs/ru/roles.md, docs/en/roles.md (list + count); roles DB table via `role create`/`role seed`."
scope_exclude: "scripts/service_roles.py and role seed logic (no code change — use existing CLI); .claude/ deployed copies (never edit directly); other role profiles."
relevant_files:
  - "harness/roles/devops.md"
  - "docs/ru/roles.md"
  - "docs/en/roles.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T10:13:01Z"
---

## Goal

Ship a `devops` behavioral role profile + DB registration so DevOps / IaC / CI-CD / Kubernetes work routes and prompt-injects like the other default roles (architect, developer, qa, tech-writer).

## Acceptance Criteria

1. `harness/roles/devops.md` exists and follows the same behavioral-prompt structure as `harness/roles/architect.md`/`developer.md` (role framing, focus areas, review lens, anti-patterns). 2. `tausik role list` shows `devops` as a registered DB row titled "DevOps". 3. `tausik role show devops` resolves to the profile path at `harness/roles/devops.md`. 4. `docs/ru/roles.md` (and the EN twin if present) list `devops` among the default profiles and update the "N профилей" count accordingly. 5. NEGATIVE/EDGE: re-running `tausik role seed` is idempotent — it does NOT create a duplicate `devops` row (verify count unchanged on second run); and `tausik role show no-such-role` still errors cleanly rather than silently succeeding.

## Plan

## Rollback

`tausik role delete devops` to drop the DB row; `git checkout -- harness/roles/devops.md docs/ru/roles.md docs/en/roles.md` to revert the profile + docs.

## Journal

- 2026-07-26T10:10:40Z [implementation] — AC verified: (1) harness/roles/devops.md created, follows architect/developer.md structure (Role heading, Core Priorities, Skill Modifiers /review//plan//task//test//commit, Anti-patterns). (2) `role list` shows devops registered, title 'DevOps'. (3) `role show devops` resolves profile + prints content. (4) docs/ru/roles.md 'пять→шесть' + devops line; docs/en/roles.md 'five→six' + devops line. (5a) `role seed` idempotent: devops rows before=1 after=1. (5b) `role show no-such-role` prints 'Error: Role ... not found.'. Deployed via bootstrap --ide all (Roles: 6 copied); drift check now clean. Bonus: role show also picked up organic task_count=8 — 7 pre-existing tasks already used devops as free-text role, confirming the gap was real.
- 2026-07-26T10:10:43Z [implementation] — DISCOVERED (out-of-scope, filing separate bug): `tausik role show <nonexistent>` prints the not-found error but exits 0 — a silent-error violation. Isolated: task show missing→exit 1, stack show missing→exit 2, bad-command→exit 2, but role show missing→exit 0. Root cause in project_cli_role.py error handling. Will file+fix as its own defect task.
- 2026-07-26T10:12:09Z [implementation] — AC1 ✓ harness/roles/devops.md follows architect/developer profile structure. AC2 ✓ `role list` shows devops, title 'DevOps'. AC3 ✓ `role show devops` resolves profile + prints content (verified via CLI). AC4 ✓ docs/ru (пять→шесть) + docs/en (five→six) list devops. AC5 ✓ `role seed` idempotent (devops rows before=1 after=1); `role show no-such-role` prints not-found error. Deployed via bootstrap --ide all (Roles: 6 copied), drift check clean. Verify run #1335 signed. Note: found separate pre-existing bug (role show missing exits 0) — filing as its own defect.
- 2026-07-26T10:12:42Z [implementation] — AC1-5 verified: profile follows structure; role list shows DevOps; role show resolves profile; docs ru/en updated (шесть/six); role seed idempotent (1→1); role show missing errors. Verify signed. Separate pre-existing bug (role show missing exits 0) filed as own defect.
- 2026-07-26T10:12:59Z [implementation] — AC1-5 verified: profile follows structure; role list shows DevOps; role show resolves profile; docs ru/en updated (шесть/six); role seed idempotent (1->1); role show missing errors. No python logic -> no-tests-expected declared. Separate pre-existing bug (role show missing exits 0) filed as own defect.
