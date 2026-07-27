---
slug: tausik-brain-init-join-existing-yes-non-interactive-on-a
title: "tausik brain init --join-existing --yes --non-interactive on a project where the Notion integration "
type: dead_end
tags:
  - brain
  - integration
  - notion
task: null
edges: []
---

Approach: tausik brain init --join-existing --yes --non-interactive on a project where the Notion integration was just created and never shared with the workspace's 4 BRAIN DBs
Reason: Notion search() returns 0 hits when integration lacks page access. CLI errors: "could not resolve all 4 database IDs. Missing: decisions, web_cache, patterns, gotchas". Fix is user-side in Notion UI: share each existing BRAIN database with the integration. Auto-discovery via search depends on shared access — no programmatic workaround. Alternative: pass IDs explicitly via --decisions-id/--web-cache-id/--patterns-id/--gotchas-id from a sister project's config.
