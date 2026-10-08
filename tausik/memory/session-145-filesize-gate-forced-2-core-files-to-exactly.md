---
slug: session-145-filesize-gate-forced-2-core-files-to-exactly
title: "Session #145: filesize gate forced 2 core files to exactly 400 lines (evidence for revisit)"
type: context
tags:
  - evidence
  - filesize-gate
  - session-145
  - technical-debt
task: null
edges: []
---

During session #145 two small, legitimate additions tripped the 400-line filesize gate and had to be shaved to EXACTLY 400: scripts/project_parser.py (added one add_rollup_flags call → 401, fixed by moving an import to module top → 400) and scripts/gate_registry.py (added one GateSpec → 405, fixed by trimming a comment from 7 lines to 2 → 400). Both now sit at the limit, so the NEXT edit to either trips the gate again — the file is one honest line from red. This is concrete evidence for [[l26-filesize-gate-revisit]] (the gate deforms architecture more than it protects): the pressure it creates is comment-shaving and import-relocation, not real decomposition. gate_registry.py and project_parser.py are both natural single-responsibility registries/parsers that grow by one entry per feature; a per-entry line budget punishes exactly the additive change the registry pattern exists to make cheap. Candidate fixes for the revisit: exempt declarative registry/parser modules, or raise the cap for files that are flat lists of specs.
