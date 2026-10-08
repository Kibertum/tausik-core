---
slug: mcp-server-caches-modules-re-bootstrap-doesn-t-help-mid
title: "MCP server caches modules — re-bootstrap doesn't help mid-session"
type: gotcha
tags: []
task: null
edges: []
---

After editing scripts/*.py: MCP tools run OLD code until session restart. Re-bootstrap syncs .claude/scripts/ on disk but the running MCP process holds Python module references unchanged. Workaround: use .tausik/tausik CLI for task lifecycle calls — CLI re-imports on each invocation. Bootstrap also rewrites .claude/scripts/ but doesn't restart the MCP process.
