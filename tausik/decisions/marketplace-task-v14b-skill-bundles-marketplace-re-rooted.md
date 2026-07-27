---
slug: marketplace-task-v14b-skill-bundles-marketplace-re-rooted
task: null
date: "2026-05-07"
edges: []
---

## Decision

Marketplace task v14b-skill-bundles-marketplace re-rooted из blocked в LOCAL-only scope — manifest+CLI+docs локально, финальный push в Kibertum/tausik-skills отдельным bullet'ом post-1.4.

## Rationale

Изначальный block — артефакт push moratorium, но локальная работа push не требует: bundles.json + CLI + per-bundle описания авторизуются в исходниках, GitHub raw URL читается consumer'ами после первого push'а. Разделение implementation vs publication разблокировало 100% scope, оставив только 30-секундный финальный push на post-1.4.</rationale>
<parameter name="task_slug">v14b-skill-bundles-marketplace
