---
slug: every-mcp-reachable-subprocess-run-must-set-stdin
title: "Every MCP-reachable subprocess.run must set stdin=subprocess.DEVNULL"
type: gotcha
tags:
  - mcp
  - stdin-hang
  - subprocess
  - testing
task: fix-stdin-hang-risk-in-resolve-assessor-git-subpro
edges: []
---

Any subprocess.run in a top-level scripts/*.py module (MCP-reachable, excludes hooks/) MUST pass stdin=subprocess.DEVNULL. Otherwise the child can inherit the MCP server's stdin and hang the server. This invariant is enforced by tests/test_risk_compute_stdin.py::test_all_top_level_subprocess_calls_set_stdin — but it only fires on full-suite pytest, not scoped verify. So when adding a NEW subprocess call, run the full suite (or at least that test) before closing. Caught in #89: fix-hardcode-assessor-identity (#88) added git-config subprocess without it; scoped verify missed it, full-suite pre-commit caught it.
