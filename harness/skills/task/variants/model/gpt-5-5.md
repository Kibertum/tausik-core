<!-- /task — GPT-5.5 overlay (telegraphic delta, not a rewrite) -->

## GPT-5.5 model quirks

- **Maximize parallel tool calls** (8+/turn supported). Front-load all reads (Read, Grep, search_code) for a step into one fan-out, then write in the next turn.
- **Zero narrative.** One sentence per turn maximum. The user reads the diff.
- Single-turn step completion: Edit + `task_step` + `task_log` + (next step's Read) in one parallel batch.
- Auto-trigger `task_done --ac-verified` immediately after final gate passes. No confirmation step.
- For test runs: parallel `pytest path/to/test_a.py` + `pytest path/to/test_b.py` when independent. Full suite only when scoped tests all green.
- Use `mcp__codebase-rag__search_code` BEFORE any Grep/Read of unfamiliar code. Returns chunks; cheaper than full-file reads.
- For gate failures: fix the exact line cited, re-run gate. Do NOT add "while we're here" cleanup.
- For filesize gate above 400: extract the largest function into a sibling module, link via thin delegator. Don't try to compress comments.
