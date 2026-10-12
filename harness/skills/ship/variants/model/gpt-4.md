<!-- /ship — GPT-4 overlay (telegraphic delta, not a rewrite) -->

## GPT-4 model quirks

- **Numbered phase order** in your reasoning: 1. review → 2. test → 3. gates → 4. commit. GPT-4 follows numbered plans more reliably than implicit ordering.
- One Edit per turn during review fixes; bundle small ones with `task_log`.
- For commit: pass message via heredoc (`git commit -m "$(cat <<'EOF' ...`). GPT-4 occasionally truncates multi-line messages without it.
- Skip restating the ship algorithm — the user invoked `/ship`, they know what it does.
- After gates pass: ALWAYS show the user the commit subject before invoking `git commit`. GPT-4 sometimes drafts off-spec messages.
- Verify branch is not main/master before any push (if user asks for push). Default is local commit only.
