**English** | [Русский](../ru/zero-defect.md)

# /zero-defect — Precision Mode

`/zero-defect` is a session-scoped operating mode that tightens agent discipline for high-stakes work. It does not promise bug-free output — it lowers the rate at which careless mistakes slip through.

The skill is inspired by [Maestro's `/zero-defect`](https://github.com/sharpdeveye/maestro), adapted to TAUSIK's QG-0 / QG-2 model.

## When to Use

Trigger it explicitly for tasks where a single mistake is expensive:

- **Security surface** — auth flows, JWT/session handling, password reset, RBAC
- **Money** — payment intent creation, refund/void, ledger writes, subscription state
- **Migrations** — schema rebuilds, data backfills, irreversible cleanups
- **Bootstrap / packaging** — anything that ships to every user
- **Defect fixes on complex tasks** — `complexity=complex` and `defect_of` non-empty

Activate by saying `zero-defect`, `precision mode`, `high stakes`, or `be careful`. The skill recognises these triggers and toggles on.

## The 8 Rules

For the rest of the session, the agent commits to:

1. **Read before write** — every `Edit` is preceded by `Read` of the same file in the same turn (or a verified prior Read).
2. **Verify before claim** — no "tests pass" / "feature works" claim without running the test or operation in this session.
3. **Don't hallucinate APIs** — when uncertain, `grep` the codebase or read upstream docs before invoking.
4. **Re-derive, don't recall** — for tricky logic, re-derive from current code; don't trust memory of a previous read.
5. **Smaller edits** — many small `Edit`s with verification between, not one large rewrite.
6. **Atomic commits** — group by concern; never bundle a refactor with a feature.
7. **Single responsibility per task** — split if scope creeps.
8. **Pre-commit gate** — run `/test` and `/review` (TAUSIK's parallel review pipeline) before saying "done".

## Activation Behaviour

When `/zero-defect` is invoked:

1. The agent acknowledges precision mode and re-states the 8 rules.
2. For the rest of the session each substantive response is prefixed with `[ZERO-DEFECT]`.
3. The agent refuses to call `task done --ac-verified` without recent test/operation evidence in notes.

## Cost — and Why That's the Point

- Velocity drops by ~2–3× compared to standard mode.
- Tool-call budgets should be increased proportionally.
- The gain is fewer escapees: defects that would have shipped, the user noticing only after deploy.

## Negative — What `/zero-defect` Does Not Promise

- It does **not** promise bug-free output. It promises a tighter loop, not a perfect one.
- It does **not** replace QG-2. Quality gates still run; `/zero-defect` runs in addition.
- It **cannot** be enforced at the framework level for rule 1 (Read-before-Write). Agent discipline carries it.
- Default mode for casual tasks is faster. Don't switch on `/zero-defect` unconditionally — it has a cost.

## Combine With

- `/review` — runs the 5-agent SENAR review pipeline; `/zero-defect` rule 8 invokes this
- `/test` — explicit test execution; rule 2 requires evidence
- QG-2 scoped pytest gate — `task done` already runs scoped tests; `/zero-defect` requires running them **before** calling `task done`

## What's Next

- **[Skills](skills.md)** — full skill catalogue
- **[Workflow](workflow.md)** — when precision mode fits the day
- **[SENAR Compliance Matrix](senar-compliance-matrix.md)** — how this composes with QG-0 / QG-2
