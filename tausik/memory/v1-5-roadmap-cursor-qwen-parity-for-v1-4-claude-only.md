---
slug: v1-5-roadmap-cursor-qwen-parity-for-v1-4-claude-only
title: "v1.5 roadmap: Cursor/Qwen parity for v1.4 Claude-only features"
type: context
tags:
  - cross-ide
  - epic
  - roadmap
  - v1.5
task: null
edges: []
---

v1.5 must cover Cursor + Qwen adaptation for whatever ships Claude-only in v1.4 token-optimization track. Specifically:

- **CLAUDE.md split** → Cursor analog: `.cursor/rules/*.mdc` per-glob auto-attach. Qwen analog: per-subdir `QWEN.md` if Qwen Code supports it (verify), else single QWEN.md augmented with directory-conditional sections.
- **Sub-agents (`.claude/agents/*.md`)** → Cursor has no native equivalent — emulate via chained skill calls or skip. Qwen: same — verify if there's a sub-agent primitive, else emulate or skip.
- **AIDD project scaffold (`tausik project init --template aidd`)** → IDE-agnostic by design, should already work for all three; v1.5 task is just smoke-test + minor polish.
- **Active-time session counter** → IDE-agnostic, already covers all three.

**Why:** session #50 directive — Claude-only in v1.4, parity in v1.5. This memory is the parity-task source list.

**How to apply:** when /plan'ing v1.5 epic, generate one cross-ide task per Claude-only feature with stack=cursor and stack=qwen. Reference this memory entry as the canonical list.
