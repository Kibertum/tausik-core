---
slug: surface-only-detector-keys-from-scrubbing-issues-to-user
task: brain-review2-hardening-v2
date: "2026-04-24"
edges: []
---

## Decision

Surface only `detector` keys from scrubbing issues to user-facing CLI messages — never raw `match` or `hint` values

## Rationale

Scrubbing matches content that can contain user-controlled text: file paths, emails, project names. Those values could carry ANSI control sequences, prompt-injection payloads, or other hostile content that reaches the agent conversation verbatim. The detector name is a closed set (filesystem_paths | emails | private_urls | project_names_blocklist) so there's no injection surface. Lost diagnostic detail is acceptable — ops can pull full issue list from logs, users just need to know what CLASS of content to redact.
