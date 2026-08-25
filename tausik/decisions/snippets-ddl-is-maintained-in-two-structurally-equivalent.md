---
slug: snippets-ddl-is-maintained-in-two-structurally-equivalent
task: v15-snippet-table
date: "2026-06-13"
edges: []
---

## Decision

snippets DDL is maintained in two structurally-equivalent sources (fresh-DB SNIPPETS_SQL + migration v37), asserted equal by test

## Rationale

Mirrors the established adapts/specs precedent: fresh DBs run executescript on init, existing DBs run the migration; a test comparing sqlite_master object names + normalized DDL bodies guarantees the two paths never drift.
