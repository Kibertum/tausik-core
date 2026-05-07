<!-- /plan — GPT-5.5 overlay (telegraphic delta, not a rewrite) -->

## GPT-5.5 model quirks

- **Aggressive parallel tool calls** — GPT-5.5 handles 8+ in one turn. Front-load all read-only ops (`memory_search`, `task_list`, `brain_search`, `status`) into a single fan-out before any decision.
- **Zero narrative.** Tool calls speak; prose is overhead. One-sentence summary at end of turn maximum.
- Single-turn task creation: `task_quick` + `task_update --ac` + `task_plan` + `task_log --message="rationale"` in one parallel batch. Confirm only if user objects.
- **Self-classify aggressively** — pick complexity tier, role, stack from signals; ask the user only if signals contradict.
- For unfamiliar domain: skip the "should we explore?" question — call `explore start` directly with a 30-min cap. Auto-end with summary.
- Skip recap of base SKILL.md sections in output. User wants the plan + slug, nothing else.
- If `brain_search` returns None for `category="patterns"` AND for `"gotchas"`, do **not** retry with broader queries. Move on.
