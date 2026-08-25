---
slug: ext-p4-migration-rollout
title: "[ext P4] Migrate 30 projects off submodule-vendoring to extension-managed"
status: planning
epic: vscode-extension
story: ext-program
complexity: null
role: developer
stack: null
tier: substantial
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Migration script: remove .tausik-lib submodule + vendored .claude/ copies, keep .tausik/tausik.db untouched, switch to extension-managed hosting. Dry-run + verify DB integrity on 1 pilot project, then roll to all 30 D:\Work TAUSIK projects. Exit: no project carries vendored framework code; updates flow only through the extension.

## Acceptance Criteria

## Plan

## Rollback

## Journal
