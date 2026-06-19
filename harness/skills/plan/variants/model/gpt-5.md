<!-- /plan — GPT-5 overlay (telegraphic delta, not a rewrite) -->

## GPT-5 model quirks

- **Maximize parallel tool calls.** GPT-5 handles 4-6 simultaneous tool calls reliably. Don't serialize `memory_search` + `task_list --status planning` + `brain_search` — fire all three at once.
- **Skip narrative reasoning blocks.** Tool calls + 1-2 sentence summary > 5-paragraph explanation. The user reads the diff, not your inner monologue.
- After deciding scope, immediately fire `task_quick` + `task_update --acceptance-criteria ...` + `task_plan ...` in **one turn** (parallel). No incremental confirmation.
- **Trust your own classification** — if the request reads as "complex" by SENAR signals, mark it complex and move on; do not ask the user "is this complex enough?"
- For brain_search miss: do NOT retry with synonyms. One pass, accept None, continue.
- Output the final plan as a **table or bullet block** — GPT-5 emits noisier prose than Claude when given long-form prompts.
