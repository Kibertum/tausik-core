---
slug: the-declared-closure-evidence-remainder-in-tausik-gates
task: closure-evidence-remainder-redeclared-after-the-notion-removal
date: "2026-09-12"
edges: []
---

## Decision

The declared closure-evidence remainder in tausik/gates.json is raised from rotted 31 / never-existed 20 to the measured 87 / 39, with the Notion removal 77703c4a named as the cause of 72 of the 75 new entries. Not a ratchet reset: the numbers are the measurement, with no headroom, and may only shrink from here.

## Rationale

Measured in session #250 by tausik audit evidence --json crossed with git show --diff-filter=D 77703c4a: rotted 87 of which 58 are files that commit deleted; never_existed 39 of which 14 are bare-name test_brain_*.py citations whose files the same commit deleted (a bare name has no git history to ask), 3 are this session's citations already corrected by a later journal line (the collector counts the first mention; journals are append-only), 1 is a named absence. A citation that rotted because its subject was removed by owner decision #358 is correct history; appending seventy 'removed in 77703c4a' lines would add no information. The remainder stays a ceiling: growth beyond 87/39 is again the signal.
