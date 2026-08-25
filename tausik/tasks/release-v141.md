---
slug: release-v141
title: "Release v1.4.1 — commit, tag, push"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T16:52:08Z"
---

## Goal

Закоммитить FTS5 fix + version bump + changelog, тегнуть v1.4.1, запушить, дождаться CI.

## Acceptance Criteria

(1) Atomic commit с FTS5 fix + tests + version bump + changelog + constants. (2) Git tag v1.4.1. (3) CI pipeline зелёный. (4) Ошибка: не должно повторно сломать build (Dockerfile уже исправлен).

## Plan

## Rollback

## Journal

- 2026-05-15T16:52:07Z [implementation] — AC verified: Pipeline #2278 (7d15c13) — success, build 20s + deploy 6s. Git tag v1.4.1 запушен на gitlab. Live tausik.tech показывает 'v1.4.1 — near-stable pre-2.0' в footer.
