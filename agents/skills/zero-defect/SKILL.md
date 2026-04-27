---
name: zero-defect
description: "Session-scoped precision mode — read-before-write, verify-before-claim, never-hallucinate-APIs. Use when stakes are high (security, payment, migration). Triggers: 'zero defect', 'precision mode', 'high stakes', 'be careful'."
context: shared
effort: medium
---

# /zero-defect — Precision Mode

Inspired by [Maestro `/zero-defect`](https://github.com/sharpdeveye/maestro). Switches the agent into a stricter operating mode for the rest of the session.

## When to use
- Touching auth, payments, billing, crypto, secrets, session handling
- Database migrations or schema rebuilds
- Bootstrap / packaging changes that ship to all users
- Any task tagged with `complexity=complex` and `defect_of` non-empty (defect-fix)

## The 8 Rules

For the rest of this session:

1. **Read before write** — every Edit must be preceded by Read of the same file in the same turn (or a verified prior Read).
2. **Verify before claim** — never write "tests pass" / "feature works" without running the test or operation in this session.
3. **Don't hallucinate APIs** — if uncertain, run `mcp__codebase-rag__search_code` (RAG) for the symbol; fall back to `Grep` only if RAG is empty or stale. Then read upstream docs.
4. **Re-derive don't recall** — for tricky logic, re-derive from current code state; don't trust memory of a previous read.
5. **Smaller edits** — prefer many small Edits with verification between, over one large rewrite.
6. **Atomic commits** — group changes by concern; never bundle a refactor with a feature.
7. **Single responsibility per task** — split if scope creeps.
8. **Pre-commit gate** — run `/test` and `/review` (TAUSIK's 6-agent pipeline) before saying "done".

## Activation

When user invokes `/zero-defect`:
1. Acknowledge mode is active and list the 8 rules.
2. For the rest of the session, prepend each substantive response with: `[ZERO-DEFECT]`.
3. Refuse to mark `task done --ac-verified` without recent test evidence in notes.

## Gotchas
- Slows velocity by ~2-3×. Use only when warranted, not as default.
- Doesn't replace QG-2 — runs IN ADDITION to gates.
- Cannot enforce rule 1 (Read-before-Write) at the framework level — relies on agent discipline.
