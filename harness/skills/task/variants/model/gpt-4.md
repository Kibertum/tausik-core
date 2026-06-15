<!-- /task — GPT-4 overlay (telegraphic delta, not a rewrite) -->

## GPT-4 model quirks

- **Numbered steps** in your reasoning before edits. GPT-4 follows numbered plans more reliably than freeform descriptions.
- One Edit per turn while iterating; if the surface area is small (3-5 lines), batch with `task_log` in parallel.
- After every significant Edit, call `task_log --message="..."` in the same turn. Don't accumulate uncommitted progress in your own memory.
- For test runs: prefer `pytest -x -q tests/test_<file>.py::test_<name>` (single test) over full file. GPT-4 reasons better with focused output.
- Skip restating the plan steps from base SKILL.md in your response — user already saw them in `/plan`.
- On gate failure: read the error verbatim, fix the **one** thing it complains about, re-run. Don't bundle multiple "while we're here" fixes.
