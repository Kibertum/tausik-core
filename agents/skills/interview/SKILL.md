---
name: interview
description: "Socratic Q&A before a complex task — max 3 clarifying questions to pin down requirements. Use when user says 'interview me', 'ask questions', 'уточни', 'задай вопросы', or before any complex/critical task where the ask is vague."
effort: fast
context: inline
---

# /interview — Socratic Requirements Clarification

Ask **at most 3** clarifying questions before writing code, in the order below. Stop as soon as the answer to a question would NOT change your approach.

Inspired by oh-my-claudecode's Deep Interview mode and prompt-master's "max 3 clarifying questions" principle.

## When to Use

- User request is vague ("make it better", "refactor this")
- Task complexity is **medium** or **complex** and goal is unclear
- Before starting a critical or security-sensitive task
- User explicitly asks: "interview me", "ask questions", "уточни"

## When to Skip

- User already wrote a detailed task with AC
- User says "just do it" / "go" / "обычно делаем так"
- Simple task where scope is obvious from one file/function

## Algorithm

### 1. Inventory what you already know

From memory, conversation, and active task (if any):
- Goal
- Inputs and outputs
- Success criteria
- Forbidden changes (scope_exclude)

### 2. Pick the ≤3 most load-bearing unknowns

Rank candidate questions by **how much the answer changes your plan**. Drop any question whose answer would NOT change what you do.

Priority ladder (top = ask first):
1. **Success criteria** — "What does 'done' look like? Give me one concrete, verifiable example."
2. **Input/output boundaries** — "Where does this data come from and who consumes it?"
3. **Non-goals** — "What should this NOT do, even if it seems natural to add?"
4. **Constraints** — "Performance, compatibility, deprecation windows?"
5. **Reference points** — "Any existing code or pattern in this repo I should mirror?"

Stop at 3.

### 3. Ask them together in one message

Format:
```
Before I start, 3 quick questions (saves a rewrite):
1. {question}
2. {question}
3. {question}
```

Do NOT ask one-by-one — that's chat, not interview.

### 4. After answers — summarize and confirm

Before any code:
```
Got it. Plan:
- Goal: {restated}
- Will do: {X, Y}
- Will NOT do: {Z}
- Done when: {AC}

Proceed?
```

If user says "yes" or any affirmative → start the task. Otherwise iterate once more.

### 5. Record the interview outcome

If an active task exists:
```
.tausik/tausik task log {slug} "Interview: {1-line summary of decisions}"
```

If not, and the task is about to be created, pass the Q&A answers into `/plan` or `/go`.

## Interaction with /plan and /go

- `/plan` + vague description → should invoke `/interview` before creating the task
- `/go` + critical/complex task → should invoke `/interview` before `task_start`

## Output Format

One message with questions only. No code blocks, no preamble. Agent waits for user reply.

## Gotchas

- **Do not ask more than 3 questions.** The whole point of this skill is restraint. Four questions = padding = friction. If you feel pulled to ask a fourth, rank-order and drop the weakest.
- **Do not ask a question whose answer you can derive.** If the codebase or memory already tells you, use that instead of burning a question slot.
- **Don't ask rhetorical questions.** "Are you sure you want to do this?" is not a clarification — it's a delay.
- **Interview is one turn, not a conversation.** Batch questions in a single message, get all answers together.
- **If the user brushes past the interview ("just do it"), respect it.** Do not re-prompt.
