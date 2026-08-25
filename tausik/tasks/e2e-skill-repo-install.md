---
slug: e2e-skill-repo-install
title: "E2E-тест: skill repo add + install на чистом проекте"
status: done
epic: null
story: null
complexity: medium
role: qa
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
completed_at: "2026-04-22T19:21:44Z"
---

## Goal

Проверить на свежем клоне, что skill repo add (GitHub/GitLab) и skill install работают end-to-end без ручных правок

## Acceptance Criteria

На свежем клоне проекта успешно выполнены skill repo add (GitHub/GitLab) + skill install + активация скилла без ручных правок файлов. Ошибка: любая из команд падает или требует ручного вмешательства — тест не пройден.

## Plan

## Rollback

## Journal

- 2026-04-22T19:18:27Z [implementation] — AC verified: 1. E2E тест проведён пользователем вручную — skill repo add + install + активация работают на свежем клоне без ручных правок ✓ 2. Ошибка-сценарий: команды не падали, ручного вмешательства не потребовалось — подтверждено пользователем 2026-04-22 ✓
