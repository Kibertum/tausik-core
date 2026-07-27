---
slug: downstream-rollout-must-checkout-the-release-tag-rev-list
task: rollout-v157-all-projects
date: "2026-07-06"
edges: []
---

## Decision

Downstream rollout must checkout the release TAG (rev-list -n1 vX), never a hardcoded core SHA; and re-bootstrap, not just bump the submodule pointer.

## Rationale

Submodule remotes are split ~14 github (scrubbed orphan, different SHAs) / ~15 gitlab, so a hardcoded SHA fails on half the fleet; the vX tag exists on both with identical trees. Bump alone fixes only .tausik-lib/scripts/hooks; the MCP server + CLI import DEPLOYED .claude/scripts copies (sys.path ../../scripts), so a full fix requires re-bootstrap. Stage only a framework allowlist (never git add -A) to avoid sweeping source WIP/tracked pyc.
