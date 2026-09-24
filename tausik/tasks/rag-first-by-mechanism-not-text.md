---
slug: rag-first-by-mechanism-not-text
title: "RAG as the code base: a PreToolUse mechanism answers Grep on unfamiliar code with search_code results"
status: planning
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: complex
role: developer
stack: null
tier: null
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

RAG becomes the default route to code by mechanism: on Grep/Read of unfamiliar code a hook injects search_code results, so the index is used without the agent remembering to.

## Acceptance Criteria

1. A PreToolUse hook on Grep (and Read of an unfamiliar path) queries the RAG index and injects the top chunks as context. 2. Skills again name RAG as the route to code, as an explanation of the mechanism. 3. NEGATIVE: effective only if a paired replay (rag-nudge-replay-protocol) shows search_code-derived context used > 0 in condition A. 4. NEGATIVE: an empty or stale index adds nothing and never blocks the call.

## Plan

## Rollback

git revert; the hook leaves the shared declaration

## Journal
