---
slug: glm-by-subscription-is-decoupled-from-the-extension-and
task: null
date: "2026-07-08"
edges: []
---

## Decision

GLM-by-subscription is DECOUPLED from the extension and available today with zero code: set ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic + ANTHROPIC_AUTH_TOKEN into Claude Code. Host stays Claude Code so ALL SENAR gates work; transcript reports model=glm-*, which TAUSIK already recognizes (model_profiles glm family). z.ai Coding Plan (~$10/mo) = subscription, not per-token.

## Rationale

User's burning need is GLM-on-subscription, which they conflated with the (larger, separate) extension project. Model axis and host axis are orthogonal (Decision #119). GLM runs by subscription on ALL four hosts; the extension is about update-pain, not GLM. docs/ru/kilo-zai.md already documents the same Anthropic env vars work for Claude Code, not just Kilo.
