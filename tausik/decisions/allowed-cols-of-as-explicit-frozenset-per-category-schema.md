---
slug: allowed-cols-of-as-explicit-frozenset-per-category-schema
task: brain-sync-sql-whitelist-cols
date: "2026-04-24"
edges: []
---

## Decision

_ALLOWED_COLS_OF as explicit frozenset per category + schema-drift test vs dynamic PRAGMA table_info introspection

## Rationale

Whitelisted columns must be known at code-read time — security review should be possible without running SQLite. Dynamic introspection pulls columns from whatever schema is currently installed, which weakens the guard against a malicious migration. test_allowed_cols_matches_schema parses brain_schema.SCHEMA_SQL via regex to guarantee the two sources stay in sync at test time.
