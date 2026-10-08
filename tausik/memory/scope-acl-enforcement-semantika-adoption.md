---
slug: scope-acl-enforcement-semantika-adoption
title: "Scope ACL enforcement: семантика adoption"
type: pattern
tags:
  - hooks
  - scope
  - senar-rule2
task: v15-scope-enforce-write
edges: []
---

scope_write_gate.py энфорсит scope_paths ТОЛЬКО когда все активные задачи декларировали ACL: задача без scope_paths даёт legacy-свободу (постепенное внедрение без поломки). Пути вне project root — юрисдикция других хуков. '[]' = явный запрет всех записей. match_path: fnmatch '*' пересекает '/', 'dir/' и bare dir = prefix. Обход: TAUSIK_SKIP_HOOKS=1; строгий режим: TAUSIK_HOOK_FAIL_SECURE=1.
