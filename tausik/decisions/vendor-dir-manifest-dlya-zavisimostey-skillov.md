---
slug: vendor-dir-manifest-dlya-zavisimostey-skillov
task: skill-deps-design
date: "2026-03-22"
edges: []
---

## Decision

Vendor dir + manifest для зависимостей скиллов

## Rationale

Zero deps (stdlib urllib), Windows-совместимо, прозрачные .lock файлы, совместимо с copy_skills. Отвергнуты: git subtree (загрязняет историю), submodules (Windows), zip без manifest (нет версионирования)
