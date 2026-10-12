**English** | [Русский](../ru/start-here-agent.md)

# Start here: you are an agent working through TAUSIK

<!-- doc-map: reader=agent; zone=getting-started -->

You are an AI assistant on a project TAUSIK governs. Your writes are gated, your closes need
evidence, and your context carries a rules file on every turn. This page is the reading order
for that situation, and it is short on purpose: everything here is paid for per turn.

## The order

1. **[agent-quickstart.md](agent-quickstart.md)** — the cycle as exact calls, with the replies
   and the refusals you will actually see. Read this before anything else.
2. **`CLAUDE.md` / `AGENTS.md` in the repository root** — the enforceable rules. They are in
   your context already; the point of reading them deliberately once is to notice which are
   hard gates and which are signals.
3. **[agent-contract.md](agent-contract.md)** — the full contract: QG-2 mechanics with every
   boundary, estimation in tool calls, Rule 4 and Rule 7, the cap on command output. Load it on
   demand, not every turn — that is why it is not in the rules file.
4. **[known-limitations.md](known-limitations.md)** — what is NOT guaranteed. A guard whose
   blind spot you do not know reads as total, and you will draw wrong conclusions from a green
   gate.

## Before you close a task

- The scoped pytest line prints a denominator. `[PASS] pytest` over two files out of 318 is not
  a statement about the project — [agent-contract.md](agent-contract.md) explains what the
  narrowed run does and does not cover.
- Evidence names a test, a run or a review. A check mark on its own is a claim.
- A defect task needs a structured root cause with a category from the closed list.

## When you find something while doing something else

File it, do not start it. Filing is free and the first principle requires it; starting is a
departure from the plan, and `task start` will say so. After every close, ask the plan before
choosing — the measurement behind that rule, and why trying harder does not fix it, is in
[agent-contract.md](agent-contract.md).

## What you can skip

The `user` pages, unless the human asks a question they answer. They explain the framework to
someone deciding whether to adopt it; you are already inside it.
