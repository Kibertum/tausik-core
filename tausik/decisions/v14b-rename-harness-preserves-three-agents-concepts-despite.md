---
slug: v14b-rename-harness-preserves-three-agents-concepts-despite
task: v14b-rename-harness
date: "2026-05-06"
edges: []
---

## Decision

v14b-rename-harness preserves three `agents/` concepts despite global rename to harness/

## Rationale

(1) `.claude/agents/`, `.codex/agents/`, `.cursor/agents/`, `.qwen/agents/` — host's native sub-agent namespace, not our source. (2) Vendor-skill `agents/` namespace inside vendor tarballs (bootstrap_vendor.py + skills.example.json `agents_dir`) — these still install into host's `.claude/agents/`. (3) `harness/skills/review/agents/<name>.md` — internal subfolder for parallel reviewer instructions in /review skill (distinct from framework-source `agents/`). All three documented in CHANGELOG migration note.
