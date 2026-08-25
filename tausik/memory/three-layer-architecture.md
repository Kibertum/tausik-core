---
slug: three-layer-architecture
title: "Three-layer architecture"
type: convention
tags:
  - architecture
  - layers
task: null
edges:
  - relation: relates_to
    target_type: memory
    target: mixin-composition-pattern
---

CLI (project.py + project_cli.py + project_parser.py) -> Service (project_service.py + mixins) -> Backend (project_backend.py + backend_schema.py). CLI handles parsing and formatting, Service handles business logic and validation, Backend handles SQLite operations. Never skip layers.
