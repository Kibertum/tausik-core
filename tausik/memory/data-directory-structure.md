---
slug: data-directory-structure
title: "Data directory structure"
type: convention
tags:
  - directories
  - structure
task: null
edges: []
---

.frai/ is the single framework data directory. Contains: config.json (project config), frai.db (SQLite database), venv/ (Python virtual environment with pytest). .claude/ is the generated IDE directory (scripts, skills, references, MCP). Source of truth is root: scripts/, bootstrap/, references/. Never edit .claude/ directly.
