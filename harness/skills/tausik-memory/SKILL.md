---
name: tausik-memory
description: "tausik-memory: search then decide/memory_add (canon B)."
effort: fast
context: inline
---

# /tausik-memory — Memory-only playbook

For `governance_profile=memory-only` (canon B). Not a SENAR session/verify ritual.

## First call

Call **`tausik_memory_brief`** once at the start of work. It returns profile, do/dont,
`decide_vs_memory`, and `next_hint` under a byte budget — without opening a session.

## Default loop

1. **Search first** — `tausik_memory_search` / `tausik_decisions_list` / RAG `search_code` before asking the user or guessing project facts.
2. **Route the write** (no task required first):
   | Kind | Where |
   |---|---|
   | Owner choice + rejected alternatives | `tausik_decide` |
   | Observed fact + provenance | `tausik_memory_add` `context` / `pattern` |
   | Stop-doing | `dead_end` / `gotcha` (or `tausik_dead_end`) |
   | Weekly draft / trail | light task under B, or a decide/memory note |
3. **`task_slug` on `memory_add` is optional** — do not invent a task only to attach memory.
4. **Light backlog when useful** — `tausik_task_quick` / `tausik_task_done` without gates unless `full_path=true`. Trail only; no verify receipts.

## Do not

- Open a task before `decide` / `memory_add` — routing does not require one.
- Call `tausik_session_start` or `tausik_verify` as the default path (advertise marks them `[profile=disabled]`).
- Treat “done” as SENAR-verified — light close is accounting, not a green gate.
- Write project knowledge to `~/.claude/` or host-local rule files — use TAUSIK memory.

## Shared surface

`advertise_do_dont()` in `scripts/memory_only_backlog.py` is the do/dont source for brief and MCP advertise. Keep skills aligned with that list.

## Gotchas

- Description must stay ≤60 characters (skill inventory tax) while still naming
  `tausik-memory` so natural-language matching finds this skill.
- `full_path` / `--full-path` is the only way back onto verify/gates under
  memory-only; a light `task done` is accounting, not a green receipt.
- Do not write project facts into host-local memory (`~/.claude/`, `.cursor/rules/`);
  use `tausik_memory_*` / `tausik_decide` so the next agent on another host inherits them.
