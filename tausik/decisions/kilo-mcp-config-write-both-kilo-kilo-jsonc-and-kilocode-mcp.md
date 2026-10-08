---
slug: kilo-mcp-config-write-both-kilo-kilo-jsonc-and-kilocode-mcp
task: v155-kilo-bootstrap-generator
date: "2026-06-19"
edges: []
---

## Decision

Kilo MCP config: write BOTH .kilo/kilo.jsonc AND .kilocode/mcp.json (robust across Kilo versions, per user request). Same schema both: top key 'mcp', per-server {type:'local', command:[python, server.py, '--project', dir], enabled:true} — command is an ARRAY (authoritative kilo.ai docs). _IDE_DIRS['kilo']='.kilo'. Overridable via .tausik/config.json kilo.config_paths.

## Rationale

kilo.ai official docs say project config = kilo.jsonc (root) or .kilo/kilo.jsonc (org), key 'mcp', command array, type/enabled/timeout. Earlier web search said .kilocode/mcp.json (older Cline-lineage). User runs Kilo Code addon daily but unsure which path their version reads → asked to support both. Same stanza in both files is harmless; whichever Kilo build reads, it finds TAUSIK's MCP server. Supersedes the .kilocode-only note in Decision #119.
