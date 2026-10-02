---
slug: initial-compound-replay-assertions-used-a-nonexistent
title: "Initial compound replay assertions used a nonexistent backend verification_run_list API and rewrote "
type: dead_end
tags:
  - testing
  - verification
task: r111-compound-progress-close
edges: []
---

Approach: Initial compound replay assertions used a nonexistent backend verification_run_list API and rewrote a same-size source for stale-handle detection
Reason: The real backend exposes verification rows through SQL/service readers, and the file hash sampler can preserve equality for a same-shape rewrite in this fixture. Query the canonical verification table through the backend connection and append distinct content so the production handle validator observes a changed hash.
