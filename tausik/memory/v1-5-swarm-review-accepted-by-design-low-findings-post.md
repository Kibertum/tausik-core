---
slug: v1-5-swarm-review-accepted-by-design-low-findings-post
title: "v1.5 swarm-review: accepted-by-design LOW findings (post-release backlog)"
type: context
tags:
  - accepted
  - backlog
  - review
  - v15
task: v15p-review-low-cleanup
edges: []
---

From the 67-agent v1.5 review, these LOW findings are ACCEPTED-BY-DESIGN (not fixed — deliberate, low value to churn): (1) autogen parses pyproject.toml up to 3× per invocation — negligible perf; (2) detect_extension_skills uses .env presence as a security-skill hint — intentional heuristic; (3) autogen write_file_with_conflict 'abort-all' == 'skip' for a single file (exit 0) — acceptable single-file semantics; (4) _detect_readme errors='replace' masks non-UTF-8 bytes — intentional (never crash); (5) aidd validate _parse_claims last-matching bullet wins for a repeated claim type — acceptable; (6) _verify_max_filesize regex picks first integer in the claim — acceptable. Plus deferred TEST-GAPS (nice-to-have, not bugs): non-dict delegation JSON, delegate-on-blocked coherence, RENAR advisory with blank task fields, aidd validate drift exit-1 for non-filesize claims, autogen leading-'##' template, aidd missing-template path. All other review findings (2 HIGH, 7 MEDIUM, valuable LOW) were FIXED in v15p-review-ship-blockers + v15p-review-low-cleanup.
