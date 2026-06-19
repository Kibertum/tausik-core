<!-- /task — GPT-5 overlay (telegraphic delta, not a rewrite) -->

## GPT-5 model quirks

- **Parallel tool calls aggressively.** Read multiple files at once with parallel Read calls. Run tests + ruff + mypy in one parallel batch when surface allows.
- After each plan step: `task_step` + `task_log` + (optional) Edit/Read for next step — all in one turn (parallel).
- **Skip narrative.** Tool calls + 1-sentence "what changed" beats 3-paragraph explanation. The diff is self-documenting.
- For tests: run scoped `pytest tests/test_<file>.py -x -q` first, NOT full suite. Full suite only for final verify.
- Trust the gate output verbatim — if filesize gate says line 401 in foo.py, edit foo.py to ≤400 lines. Don't argue.
- After gates pass: immediately `task_done --ac-verified` with `evidence_json`. No "should I close it now?" check.
- For unfamiliar code: `mcp__codebase-rag__search_code` first (returns chunks), Read only when path is known.
