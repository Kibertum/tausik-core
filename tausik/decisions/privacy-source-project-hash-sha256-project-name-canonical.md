---
slug: privacy-source-project-hash-sha256-project-name-canonical
task: brain-db-schema
date: "2026-04-22"
edges: []
---

## Decision

Privacy: Source Project Hash = SHA256(project_name_canonical)[:16] в каждой записи brain

## Rationale

16 hex = 64 bit, коллизии для N=1000 пренебрежимы. По содержимому brain нельзя определить имена проектов пользователя. Реестр имён — локально в ~/.tausik-brain/projects.json, хэш не обратим без него.
