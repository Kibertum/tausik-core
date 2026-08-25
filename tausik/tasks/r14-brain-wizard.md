---
slug: r14-brain-wizard
title: "Shared Brain: setup wizard or guided init to reduce friction"
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
completed_at: "2026-05-01T00:50:03Z"
---

## Goal

Release 1.4 readiness: r14-brain-wizard

## Acceptance Criteria

1. Brain init wizard prints upfront 4-step prerequisites checklist (workspace, integration, env-var token, parent page shared with integration) before any prompt. 2. Token-missing error gives concrete how-to-fix steps including platform-specific export commands. 3. Parent page ID prompt now shows example URL and explains the integration-share gesture. 4. Negative scenario: missing token env var produces a multi-line WizardError with platform-specific instructions instead of opaque single-line failure.

## Plan

## Rollback

## Journal

- 2026-05-01T00:50:02Z [implementation] — AC verified: 1. Upfront checklist printed in interactive mode ✓ (brain_init.py:417). 2. Token-missing error includes setx/export instructions ✓. 3. Parent-page prompt has URL example + Connections hint ✓. 4. Negative - non-interactive run still raises clear WizardError, doesn't print interactive checklist ✓ (53/53 tests pass including non_tty path).
- 2026-05-01T00:50:02Z [implementation] — Documentation status updated: docs/{en,ru}/shared-brain.md no longer claims 'setup wizard pending' — now lists the 1.4 wizard improvements and points at bootstrap --interactive flow. brain_init test suite remains green: 53/53.
- 2026-05-01T00:50:02Z [implementation] — scripts/brain_init.py:run_wizard now prints a 4-item readiness checklist (workspace, integration with proper capabilities, NOTION_TOKEN env var, shared parent page) before any prompt. Token-missing WizardError lists platform-specific exports (setx for Windows, export for macOS/Linux) and the integration creation URL. Parent-page prompt prints an example URL with the 32-char id and reminds about the Connections share.
