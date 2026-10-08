---
slug: claude-first-then-cursor-qwen-for-new-optimizations
title: "Claude-first, then Cursor/Qwen for new optimizations"
type: convention
tags:
  - cross-ide
  - optimization
  - roadmap
  - v1.5
task: null
edges: []
---

When implementing context/token optimizations or new harness primitives (sub-agents, directory-scoped instructions, advanced hooks), ship Claude-only in current minor and add Cursor/Qwen adaptation to the next minor's roadmap. Per session #50: explicit user directive — do NOT bundle cross-IDE parity into the same release.

**Why:** validate the optimization works under real Claude usage before paying 3x bootstrap surface cost across IDEs. Saves rework if the design changes after measurement.

**How to apply:** for any new bootstrap output / skill / sub-agent / .mdc-equivalent: add it under `agents/claude/` only in current cycle, file an explicit v1.5 (or next-minor) roadmap task `cross-ide-parity-<feature>` with stack tags for cursor and qwen. Document Claude-only in the feature's docs.
