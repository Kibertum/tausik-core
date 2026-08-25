---
slug: cli-runs-claude-scripts-only-full-bootstrap-no-flags-syncs
title: "CLI runs .claude/scripts; only full bootstrap (no flags) syncs it"
type: gotcha
tags: []
task: null
edges: []
---

The .tausik/tausik wrapper executes .claude/scripts (generated copy), NOT root scripts/. After editing root scripts/, 'bootstrap.py --refresh' only rewrites .tausik/config.json — it does NOT copy scripts/skills/MCP. To see edited behavior via the CLI (and to refresh what the MCP server loads on restart), run full 'python bootstrap/bootstrap.py' (no flags). Tests/pytest are unaffected (they import root scripts/ directly), so a feature can pass tests yet appear missing in 'tausik status' until a full bootstrap. .claude/ is gitignored here, so this never blocks commits.
