---
slug: first-volna-recon-read-brain-init-py-up-to-create-brain
title: "First-volna recon: read brain_init.py up to create_brain_databases (line 188) and rapidly conclude \""
type: dead_end
tags:
  - anti-pattern
  - recon
  - scope
task: v14b-defect-brain-enable-no-discovery
edges: []
---

Approach: First-volna recon: read brain_init.py up to create_brain_databases (line 188) and rapidly conclude "no discovery code, need new CLI subcommand brain enable + run_enable_wizard". Spent ~10 tool calls drafting AC + plan around that wrong premise.
Reason: find_workspace_brain_databases (line 213) and verify_brain_databases (line 253) and the entire Branch A in run_wizard (line 510-561) ALREADY implemented workspace search + --join-existing flow as part of v133-anti-hallucination epic. The actual defect was much narrower: only the title-matching strictness (and the misleading error message). Fixed mid-session by reading the rest of the file BEFORE committing to scope. Lesson: when a recon finds "feature X is missing", read at least to the next major function boundary or to end-of-file before declaring scope. False-negative recon costs more than thorough recon. Especially in modules >400 lines.
