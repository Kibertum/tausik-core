---
slug: r14-brain-bootstrap-prompt
title: "Bootstrap: prompt to setup Shared Brain on first init (interactive wizard)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:48:04Z"
---

## Goal

Release 1.4 readiness: r14-brain-bootstrap-prompt

## Acceptance Criteria

1. bootstrap.py prints 'Setup Shared Brain (cross-project knowledge in Notion)? [y/N]' in interactive mode after init succeeds. 2. Answering y launches .tausik/tausik brain init via subprocess. 3. quickstart docs (en+ru) document the new prompt and how to skip. 4. Negative scenario: non-TTY/CI runs (no --interactive) never block on the prompt; EOFError on input falls through to skip path.

## Plan

## Rollback

## Journal

- 2026-05-01T00:48:03Z [implementation] — Added optional Shared Brain prompt to bootstrap/bootstrap.py: shown only when args.interactive AND args.init is not None (DB exists). y -> .tausik/tausik brain init via subprocess. EOFError handled gracefully (CI fallback to skip).
- 2026-05-01T00:48:03Z [implementation] — Documented in docs/en/quickstart.md and docs/ru/quickstart.md after Step 2 with explicit non-TTY behaviour. Bootstrap dryrun tests pass 4/4.
- 2026-05-01T00:48:04Z [implementation] — AC verified: 1. bootstrap.py shows brain prompt in interactive mode ✓ (bootstrap.py:395-419). 2. y answer runs tausik brain init ✓. 3. docs/{en,ru}/quickstart.md describe the prompt + skip path ✓. 4. Negative - args.interactive guard plus EOFError trap means CI never blocks ✓.
