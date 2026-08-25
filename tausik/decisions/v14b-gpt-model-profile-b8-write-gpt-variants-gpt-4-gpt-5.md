---
slug: v14b-gpt-model-profile-b8-write-gpt-variants-gpt-4-gpt-5
task: v14b-gpt-model-profile
date: "2026-05-06"
edges: []
---

## Decision

v14b-gpt-model-profile (B8 — write GPT variants/{gpt-4,gpt-5,gpt-5-5}.md overlays for /plan, /task, /ship) is blocked on a prerequisite: model-profile auto-detection + axis decision. New task b8-pre-model-profile-auto-detect-interactive-promp captures the gate.

## Rationale

Without auto-detect or interactive prompt, no real user will ever set TAUSIK_MODEL_PROFILE=gpt-5 manually — the variants would be dead code. Also `variants/` currently mixes two axes (IDE: claude/cursor/qwen/codex vs model: haiku/sonnet/opus/gpt-N), and Cursor can run any model. Adding gpt-N files without picking the axis (model? IDE? hybrid `cursor-gpt-5.md`?) cements the wrong contract. Decision: ship detection + prompt + axis FIRST, variants AFTER.
