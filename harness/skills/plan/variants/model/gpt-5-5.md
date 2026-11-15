<!-- /plan — GPT-5.5 overlay (telegraphic delta, not a rewrite) -->

## GPT-5.5 model quirks

- **Aggressive parallel tool calls** — GPT-5.5 handles 8+ in one turn. Front-load all read-only ops (`memory_search`, `task_list`, `status`) into a single fan-out before any decision.
- **Zero narrative.** Tool calls speak; prose is overhead. One-sentence summary at end of turn maximum.
- Single-call task creation: one atomic `tausik_task_add` carries AC, budget, plan steps, rationale, scope, and dependencies. For a graph, create nodes in topological order. Confirm only if user objects.
- **Self-classify aggressively** — pick complexity tier, role, stack from signals; ask the user only if signals contradict.
- For unfamiliar domain: skip the "should we explore?" question — call `explore start` directly with a 30-min cap. Auto-end with summary.
- Skip recap of base SKILL.md sections in output. User wants the plan + slug, nothing else.
