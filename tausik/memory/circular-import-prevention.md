---
slug: circular-import-prevention
title: "Circular import prevention"
type: gotcha
tags:
  - circular-deps
  - imports
task: null
edges: []
---

ServiceError lives in frai_utils.py (not project_service.py) to prevent circular import: project_service.py -> service_knowledge.py -> ServiceError. All shared utilities (validate_slug, validate_length, validate_content, utcnow_iso) in frai_utils.py. Types in project_types.py. Schema in backend_schema.py.
