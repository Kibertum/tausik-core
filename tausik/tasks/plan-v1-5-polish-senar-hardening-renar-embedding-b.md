---
slug: plan-v1-5-polish-senar-hardening-renar-embedding-b
title: "Plan v1.5 polish + SENAR hardening + RENAR embedding backlog"
status: done
epic: null
story: null
complexity: null
role: architect
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
completed_at: "2026-06-11T23:03:30Z"
---

## Goal

Decompose user directives into TAUSIK backlog: (1) v1.5 polish epic incl. reindex-hang defect and research T-items, (2) SENAR rules 4/5/6/7 enforcement epic, (3) RENAR v1.0-draft embedding epic, (4) shared brain hardening epic. All tasks with goal/AC-ready descriptions, prioritized, no duplicates with existing 27 planning tasks.

## Acceptance Criteria

1) 4 epics created (v15-polish, v15-senar-hardening, v16-renar-core, brain-hardening) with stories and tasks, each task has goal + AC seed in description. 2) No duplicates with existing v15-evidence-attestation backlog (reuse v15-scope-rule2-hardgate, v15-l3-risk-trigger links). 3) Priorities P0-P2 assigned; reindex-hang defect is P0. 4) Plan summary presented to user. Negative scenario: if epic/story creation fails mid-way, log created slugs and continue — partial structure is recoverable, not a blocker.

## Plan

## Rollback

## Journal

- 2026-06-11T23:03:17Z [implementation] — CHECKPOINT + completion: 4 epics, 8 stories, 30 tasks created. v15-polish: 11 (v15p-fix-rag-reindex-hang P0, handler-drift, T1/T2/T5/T10, doc-drift-gate, shell-true, coverage, fts-cron, release-150). v15-senar-hardening: 5 (rule4-external-reviewer, rule4-domain-challenge, rule6-rollback, rule5-hardgate, rule7-rootcause). v16-renar-core: 9 (reasoning-steps, reason-skill, task-replay, model-pinning, audit-hashchain, spec-types, adapt-lite, drift-detectors, conformance-yaml). brain-hardening: 5 (audit-first, reliability, semantic-search, capture-ux, outline-spike). No dup with v15-evidence-attestation (rule2-hardgate, l3-risk-trigger reused as links). RENAR verified at v1.0-draft 31.05.2026 via WebFetch.
- 2026-06-11T23:03:30Z [implementation] — AC-1: ✓ 4 epics + 8 stories + 30 tasks created in DB (epic list / task list confirm). AC-2: ✓ no duplicates — v15-scope-rule2-hardgate and v15-l3-risk-trigger referenced as links, not recreated. AC-3: ✓ P0-P2 prefixes in titles; v15p-fix-rag-reindex-hang marked P0. AC-4: ✓ summary delivered in chat. Negative scenario not triggered — all creations succeeded.
