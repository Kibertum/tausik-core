---
slug: rolling-framework-to-downstream-projects-submodule-remotes
title: "Rolling framework to downstream projects: submodule remotes split github/gitlab with different SHAs — checkout by TAG"
type: gotcha
tags:
  - bootstrap
  - github-orphan
  - gitlab
  - rollout
  - submodule
  - v1.5.7
task: rollout-v157-all-projects
edges: []
---

The ~30 TAUSIK projects under D:\Work consume core via a .tausik-lib git submodule, but the submodule remote is split ~14 github.com/Kibertum/tausik-core (the SCRUBBED ORPHAN mirror, different commit SHAs) and ~15 [вычеркнуто: internal-host]. A given release has DIFFERENT commit SHAs on each remote (gitlab 7eb4015 vs github 7c311e8 for v1.5.7 — same tree). So a rollout must NOT checkout a hardcoded core SHA; instead: `git -C lib fetch origin refs/tags/vX:refs/tags/vX` then `tgt=$(git -C lib rev-list -n1 vX)` then `git checkout $tgt`. Both remotes carry the vX tag. `git fetch --tags` alone did NOT materialize the tag locally (needed explicit refspec). Also: hooks run from .tausik-lib/scripts/hooks (fixed by pointer bump) BUT the MCP server + CLI import deployed copies from .claude/scripts (sys.path ../../scripts) — so a full fix needs bump + re-bootstrap. Stage only a framework allowlist (.tausik-lib .claude .cursor .kilo .qwen .mcp.json CLAUDE.md AGENTS.md) — never `git add -A` (repos carry unrelated source WIP + tracked .pyc). Push origin HEAD (fast-forward, no --force). Some remotes may be unreachable (TLS/403/no-origin) — leave committed-local.
