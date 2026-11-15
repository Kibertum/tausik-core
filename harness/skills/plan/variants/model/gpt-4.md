<!-- /plan — GPT-4 overlay (telegraphic delta, not a rewrite) -->

## GPT-4 model quirks

- Use **explicit step numbering** in your reasoning before tool calls. GPT-4 follows numbered lists more reliably than prose.
- Prefer **single tool call per turn** while planning — GPT-4's parallel-tool-call rate degrades when scope is unclear.
- Use one `tausik_task_add` call with AC, budget, plan steps, rationale, scope, and dependencies. Never parallelize follow-up cross-task mutations; a bound execution lease correctly refuses them.
- Skip the long-form `## Algorithm` recap in your response. The base SKILL.md already encodes the steps — restating wastes tokens.
- For domain familiarity check (step 1.4): if uncertain, **directly invoke** `tausik explore start` rather than asking the user "should we explore?"
- Verify slug regex (`^[a-z0-9][a-z0-9-]*$`) before the atomic `task_add` call.
