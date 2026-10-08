---
slug: roles-storage-hybrid-metadata-in-sqlite-profile-markdown-in
task: null
date: "2026-04-25"
edges: []
---

## Decision

Roles storage = hybrid (metadata in SQLite, profile markdown in agents/roles/{role}.md)

## Rationale

SQLite-only loses rich profile editability and grep-ability. Markdown-only loses fast lookup, FTS search, and cross-task aggregation. Hybrid: row in `roles` table for slug/title/created_at + foreign-key references from tasks; markdown body for description/profile/instructions agent reads on activation. CRUD MCP touches both.
