---
slug: codex-sub-agent-toml-files-are-generated-from-harness
task: null
date: "2026-09-09"
edges: []
---

## Decision

Codex sub-agent TOML files are generated from harness/claude/subagents Markdown as the sole canonical instruction source and are deliberately overwritten on rerun.

## Rationale

Maintaining a second prompt copy creates silent instruction drift; bootstrap-generated profiles are reproducible artifacts.
