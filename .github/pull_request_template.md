<!-- TAUSIK is built with TAUSIK. PRs are expected to go through the same gates. -->

## What & why
Brief description + the problem it solves. Link the issue if any.

## Checklist
- [ ] Opened under a TAUSIK task (goal + acceptance criteria) — `tausik task start <slug>`
- [ ] `tausik verify` green (or `pytest` + `ruff check .` + `mypy` locally)
- [ ] New behavior covered by tests; `gen_doc_constants --check` green if counts changed
- [ ] Files under the 400-line cap (or justified)
- [ ] No new module-level third-party imports in CLI-reachable modules (stdlib-only core)
- [ ] Docs / CHANGELOG updated (EN + RU) if user-facing

## Acceptance criteria verified
Paste the `AC-N: ✓ … via tests/…` evidence (mirror your task's QG-2 evidence).

## Rollback
How to undo (git revert / flag off).
