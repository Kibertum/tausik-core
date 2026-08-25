---
slug: v14-audit-stale-docs
title: "Список потенциально устаревших docs (нет входящих ссылок)"
status: done
epic: v14-dead-code-audit
story: v14-audit-inventory
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/audit_stale_docs.py"
  - "tests/test_audit_stale_docs.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T11:15:46Z"
---

## Goal

Research помечены как archival где нужно.

## Acceptance Criteria

1. Markdown отчёт. 2. Критерии stale. 3. Negative: обязательные docs не помечены удалёнными ошибочно.

## Plan

## Rollback

## Journal

- 2026-05-02T11:15:45Z [implementation] — AC verified: 1. ✓ markdown report via scripts/audit_stale_docs.py + --json/--check режимы. 2. ✓ Stale criteria: not referenced + roots safe + research/release-notes/_generated excluded by glob. 3. ✓ Negative: tests/test_audit_stale_docs.py::TestCollectStale::test_mirror_partner_protected + test_root_docs_always_safe + test_research_excluded — must-keep docs не помечаются.
