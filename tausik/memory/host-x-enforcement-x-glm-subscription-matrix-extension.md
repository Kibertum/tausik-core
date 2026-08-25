---
slug: host-x-enforcement-x-glm-subscription-matrix-extension
title: "Host x enforcement x GLM-subscription matrix (extension research, session #102)"
type: context
tags:
  - cursor
  - enforcement
  - extension
  - glm
  - hooks
  - kilo
  - qwen
  - zai
task: ext-p0-derisk-spike
edges: []
---

Research swarm (7 agents) for epic universal-vscode-extension established the 4-host landscape. ENFORCEMENT (SENAR gates need a pre-tool hook that can hard-deny): Claude Code = native Claude hook contract (full). Qwen Code = borrows Claude's EXACT hook JSON contract (PreToolUse deny + exit-2), bootstrap_qwen.py already emits full parity, test-pinned (test_bootstrap_hooks_parity.py) -> gates port near-free. Cursor = has OWN hooks.json since 1.7 (Oct 2025): beforeMCPExecution/beforeShellExecution/beforeReadFile allow/deny/ask + failClosed -> hard-deny possible but needs a Cursor-format adapter (TAUSIK emits none today). Kilo (Cline lineage) = NO hook mechanism found -> gates advisory only. So 3 hook dialects: Claude+Qwen share one; Cursor its own; Kilo none. DELIVERY: VS Code + Kilo + Qwen Companion via MS Marketplace; Cursor via Open VSX (no vscode.lm MCP API -> must write .cursor/mcp.json). GLM-BY-SUBSCRIPTION works on ALL 4 (z.ai Coding Plan): Claude Code + Qwen via Anthropic-compatible /api/anthropic (host unchanged, gates intact); Cursor + Kilo via OpenAI-compatible /api/coding/paas/v4. Key reframe: model axis and host axis are orthogonal (Decision #119) -> GLM-by-subscription is DECOUPLED from the extension and available today via env vars. Host priority: Claude Code(MVP)->Qwen->Cursor->Kilo(advisory).
