---
slug: kilo-code-mcp-config-path-is-version-dependent-write-both
title: "Kilo Code MCP config path is version-dependent — write both"
type: gotcha
tags:
  - bootstrap
  - kilo
  - mcp
  - v155
task: v155-kilo-bootstrap-generator
edges: []
---

Kilo Code's MCP config path differs across builds: official kilo.ai docs say project-level lives in kilo.jsonc (project root) or .kilo/kilo.jsonc (org), while older Cline-lineage builds read .kilocode/mcp.json. The SCHEMA is consistent everywhere: top-level key 'mcp', per-server {type:'local', command:[python, server.py, '--project', dir] (command is an ARRAY not a string), enabled:true, optional environment/timeout}. TAUSIK bootstrap_kilo.generate_kilo_config writes BOTH default paths with the same stanza (Decision #120) so whichever Kilo build is installed finds the server; override via .tausik/config.json kilo.config_paths. Server path resolves to copied .kilo/mcp/project/server.py first, else lib_dir/harness/claude/mcp/project/server.py. Don't assume a single path — verify against the user's Kilo version if a single-file write is ever needed.
