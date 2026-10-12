<!-- /ship — GPT-5 overlay (telegraphic delta, not a rewrite) -->

## GPT-5 model quirks

- **Parallel phases.** Run review (`Agent` subagent) + scoped pytest + ruff + mypy in parallel — they're independent until commit.
- After all 4 phases green: immediately compose commit message, present to user, await confirmation, then `git commit`. No extra status check between gate-pass and commit.
- **Skip narrative summary** of changed files — user reads `git status` / diff directly.
- For commit message: subject line ≤72 chars, body explains "why" not "what". One sentence per change cluster.
- For multi-task batched commit: list slugs in body, one per line, no surrounding prose.
- Heredoc commit messages always (`git commit -m "$(cat <<'EOF' ... EOF\n)"`) — GPT-5 emits cleaner output that way.
- Never push without explicit user request. Default is local commit only.
- After commit: print short URL for `git log --oneline -1` worth of context. No "all done!" filler.
