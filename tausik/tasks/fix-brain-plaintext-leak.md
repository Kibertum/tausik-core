---
slug: fix-brain-plaintext-leak
title: "Scrub all string fields before brain write"
status: done
epic: v131-blind-review-fixes
story: security-high
complexity: simple
role: developer
stack: python
tier: light
call_budget: 12
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_mcp_write.py"
  - "tests/test_v131_blind_review.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-27T12:13:01Z"
---

## Goal

Extend scrub_inputs haystack to include tags, stack, domain, severity, evidence_url, query, name (web_cache). Currently only named text fields are scrubbed → project name leaks via tags. Closes HIGH (Sec).

## Acceptance Criteria

1. brain_mcp_write.scrub_inputs haystack includes ALL string-valued props; 2. tags/stack/domain/severity/evidence_url/query/name fields are scrubbed; 3. Test: project name in tags array is rejected by scrubber; 4. Negative: tags=['[вычеркнуто: third-party-project]', 'kibertum.ru'] is blocked by scrub layer.

## Plan

## Rollback

## Journal

- 2026-04-27T12:10:33Z [implementation] — AC: 1.✓ _TEXT_FIELDS_BY_CATEGORY extended for all 4 categories: tags/stack/superseded_by (decisions), tags/domain (web_cache), tags/stack/confidence (patterns), tags/stack/severity/evidence_url (gotchas); 2.✓ _stringify helper handles list/tuple values (joins with space); 3.✓ Test `test_brain_scrub_inputs_covers_tags_and_stack` proves tags=['kibertum-project'] is now blocked; 4.✓ Test `test_brain_scrub_inputs_passes_clean_data` proves clean data still passes; 5.✓ Negative — project name slipped through tags is blocked at scrub layer before any Notion write.
- 2026-04-27T12:13:00Z [implementation] — AC: 1.✓ _TEXT_FIELDS_BY_CATEGORY расширен для всех 4 категорий: tags/stack/superseded_by (decisions), tags/domain (web_cache), tags/stack/confidence (patterns), tags/stack/severity/evidence_url (gotchas); 2.✓ _stringify() handles lists; 3.✓ Test test_brain_scrub_inputs_covers_tags_and_stack: project name в tags блокируется; 4.✓ Test test_brain_scrub_inputs_passes_clean_data: чистые данные проходят; 5.✓ filesize gate: 375 lines &lt; 400; 6.✓ Negative — slug проекта в tags array больше не утекает в Notion.
