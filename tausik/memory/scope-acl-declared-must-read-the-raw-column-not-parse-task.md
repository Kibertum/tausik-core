---
slug: scope-acl-declared-must-read-the-raw-column-not-parse-task
title: "scope ACL: \"declared?\" must read the RAW column, not parse_task_acl output"
type: gotcha
tags:
  - acl
  - gotcha
  - lenient-parser
  - scope
  - senar-rule2
task: mcp-scope-empty-list-legacy-freedom
edges: []
---

parse_task_acl (scope_acl._parse_list) is a LENIENT reader: it collapses both scope_tools/scope_paths = NULL and = '[]' to the same Python []. So `if parsed_list:` CANNOT distinguish "never declared" (NULL → legacy freedom) from "explicitly declared empty" ('[]' → deny-all / restrict-to-core). Any code deciding declared-vs-undeclared must read the RAW DB value (`raw is not None and raw != ''`), mirroring scope_write_gate.has_declared_scope. Bit this in mcp_tool_scope._active_declared_tools (defect mcp-scope-empty-list-legacy-freedom, found by session-145 review): '[]' leaked ALL MCP tools instead of restricting to safe-core. Symmetry with the write-gate is the tell — when you add a second consumer of an ACL, reuse the first's declared-check, don't re-derive it from the parsed list. Relates to [[mcp-surface-scoping-fail-open-symmetric-to-write-gate]].
