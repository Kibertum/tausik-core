---
slug: column-whitelisting-in-update
title: "Column whitelisting in UPDATE"
type: pattern
tags:
  - backend
  - security
  - sql
task: null
edges: []
---

Backend._update() uses frozenset whitelists (_EPIC_FIELDS, _STORY_FIELDS, _TASK_FIELDS, _PLAN_FIELDS) to prevent SQL injection via arbitrary column names. Any field not in the whitelist raises ValueError. updated_at auto-injected only if present in whitelist.
