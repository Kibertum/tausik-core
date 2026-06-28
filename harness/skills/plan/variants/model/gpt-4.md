<!-- /plan — GPT-4 overlay (telegraphic delta, not a rewrite) -->

## GPT-4 model quirks

- Use **explicit step numbering** in your reasoning before tool calls. GPT-4 follows numbered lists more reliably than prose.
- Prefer **single tool call per turn** while planning — GPT-4's parallel-tool-call rate degrades when scope is unclear.
- After `task_quick`/`task_add`, **immediately** call `task_update` for AC + plan in the **same turn** (parallel calls). Don't ask "should I add AC now?" — just do it; AC is QG-0 mandatory.
- Skip the long-form `## Algorithm` recap in your response. The base SKILL.md already encodes the steps — restating wastes tokens.
- For domain familiarity check (step 1.4): if uncertain, **directly invoke** `tausik explore start` rather than asking the user "should we explore?"
- Verify slug regex (`^[a-z0-9][a-z0-9-]*$`) **before** calling `task_quick` to avoid back-and-forth on slug rejection.
