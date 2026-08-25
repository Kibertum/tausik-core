---
slug: soft-archive-of-done-tasks-and-memory-rows-uses-an-archived
task: v14b-hygiene-archive-confirm
date: "2026-05-06"
edges: []
---

## Decision

Soft-archive of done tasks AND memory rows uses an `archived_at TEXT` column (nullable, ISO8601 UTC) layered on top of the existing `status='done'` — NOT a new `status='archived'` value.

## Rationale

Keeping `status='done'` means historical metrics (FPSR, lead time, defect counts), FTS5 indexes, `task_show`/`memory_show` by id, and audit trails are unaffected — the archive is purely a default-list filter. Switching to `status='archived'` would have required updating the CHECK constraint via a full table rebuild AND every metrics query (which currently group by status) to include the archived bucket. Trade-off accepted: archived rows still occupy disk and FTS index space; users who want hard delete must run `task delete` / `memory delete` explicitly. Same pattern works for both v25 (tasks) and v26 (memory).
