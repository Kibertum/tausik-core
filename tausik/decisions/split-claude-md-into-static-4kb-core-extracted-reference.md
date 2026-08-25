---
slug: split-claude-md-into-static-4kb-core-extracted-reference
task: null
date: "2026-05-03"
edges: []
---

## Decision

Split CLAUDE.md into static <=4KB core + extracted reference (docs/ru/agent-contract.md), enforced by regression test (tests/test_claude_md_size.py)

## Rationale

CLAUDE.md is loaded into agent context every turn. Pre-trim it was 15595B = ~4000 tokens of fixed per-turn tax. On a 100-turn session this multiplied to ~400K tokens of overhead just from CLAUDE.md alone. Trim to 4204B (static 3997B, under 4096 cap) saves ~2850 tok/turn, ~285K tok per 100-turn session, with no information loss (heavy reference moved to docs/ru/agent-contract.md, loaded on demand). Architecture table dropped entirely (already lived in docs/ru/architecture.md). Regression test makes the cap permanent: future content additions must go to agent-contract.md or architecture.md, not CLAUDE.md. Closes T2.2 of v14b-token-tier2-architectural; T2.1 (start lite), T2.3 (output truncation), T2.4 (skill auto-deactivate) remain.</rationale>
<parameter name="task_slug">v14b-claudemd-trim
