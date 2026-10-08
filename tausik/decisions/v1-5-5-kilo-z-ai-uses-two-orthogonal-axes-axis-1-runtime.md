---
slug: v1-5-5-kilo-z-ai-uses-two-orthogonal-axes-axis-1-runtime
task: null
date: "2026-06-19"
edges: []
---

## Decision

v1.5.5 Kilo+z.ai uses TWO orthogonal axes. Axis-1 runtime/IDE (claude/cursor/kilo/qwen): Provider classes owning bootstrap dir+settings+transcript+model detection; Kilo is the ONE new Provider (config .kilocode/mcp.json, NOT .kilo/kilo.json). Axis-2 model (Claude+GLM): DATA in model_profiles config (id->family/tier/display/cost); z.ai is NOT a Provider -> DELETE zai.py. Routing matrix emits family-agnostic 'flagship-of-active-family' tier, not hardcoded claude-opus-4-8, so GLM routes without code.

## Rationale

User runs TAUSIK under Kilo (VSCode+CLI) switching z.ai GLM models. 'Different models' = growing data set -> config-driven not class-per-model. Single host (Kilo, shared .kilocode/) is the real Provider. z.ai Anthropic-compatible endpoint makes transcript identical to Claude's (model=glm-*) so detection works via existing reader; zai Provider returning None is a category error. Scaffold was broken: claude.py IndentationError; kilo/zai register() call get() with no arg; model_routing imports scripts.providers which fails under MCP sys.path = silent None.
