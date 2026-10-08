---
slug: references-folder-merged-into-docs-single-canonical
task: null
date: "2026-04-26"
edges: []
---

## Decision

References folder merged into docs/ — single canonical structure

## Rationale

User: 'не вижу смысла в references как отдельной папки, сливаем ее с docs'. Eliminates EN/RU pair confusion (was QUICKSTART.md=RU + QUICKSTART.en.md=EN), centralizes all human + agent-facing docs. bootstrap_copy.copy_references rewritten to copy docs/ instead.
