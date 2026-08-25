---
slug: project-modules-inventory
title: "Project modules inventory"
type: context
tags:
  - inventory
  - modules
task: null
edges: []
---

12 scripts: project.py (entry), project_cli.py + project_cli_extra.py (CLI handlers), project_parser.py (argparse), project_service.py (service + 3 inline mixins), service_knowledge.py (KB mixin), project_backend.py (SQLite ops), backend_schema.py (DDL + FTS), project_config.py (config loader), project_types.py (TypedDict + constants), frai_utils.py (ServiceError + validators), frai_version.py (version). 6 bootstrap files. 3 test files (134 tests).
