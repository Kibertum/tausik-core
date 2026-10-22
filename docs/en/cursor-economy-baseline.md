# Cursor economy baseline for 1.11.7

**English** | [Русский](../ru/cursor-economy-baseline.md)

<!-- doc-map: reader=maintainer; zone=reference -->

Decision #433: the 1.11.7 economy layer for Cursor is **rounds + surface**, not
cache polish. This note records how to count rounds on the memory-only playbook
and what remains **unknown** when the host has no ledger.

## Honesty rules

- Do **not** relabel Codex baseline numbers ([codex-economy-baseline](codex-economy-baseline.md))
  as Cursor savings.
- Do **not** claim API-USD or subscription-% without a dated public price table
  cited in the same paragraph.
- Prefer “unknown” over a fabricated before/after.

## Fixed fixture scenario (memory-only)

Hold model, Cursor plan, and enabled MCP set fixed. Project
`governance_profile=memory-only`. Scenario:

1. `tausik_memory_brief` (once)
2. `tausik_memory_search` or `tausik_decisions_list` (search before write)
3. `tausik_decide` **or** `tausik_memory_add` (one durable write)
4. Optional light task: `tausik_task_quick` → `tausik_task_done` **without**
   `session_start` / `verify`

Stop when the write is durable. Do not open a SENAR session.

## How to count rounds

| Signal | How | When usable |
|---|---|---|
| Agent/tool rounds | Count model turns that issued ≥1 tool call, or count tool-call batches the host shows for the chat | Always available by hand in the Cursor transcript |
| Premium requests | Cursor UI / billing “premium requests” delta for the window, if the account exposes it | Only when the UI shows a dated counter for that chat/window |

Record: date, model id, MCP server names enabled, round count (or premium
delta), and whether the fixture completed without `session_start`/`verify`.

## 1.11.7 release status

**Before/after measured rounds for this fixture: unknown.**

Blocked signal: Cursor does not expose a project-local tool-round ledger that
TAUSIK can read the way Codex journals feed `tausik metrics --host codex`.
This release therefore ships the method + checklist above, not a numeric claim.

Manual checklist (reproducible):

1. New Cursor agent chat on a memory-only fixture project.
2. Disable non-TAUSIK MCP (see [context-economy](context-economy.md#cursor-extra-mcp-servers-tax-the-same-plan)).
3. Run the four fixture steps; write the round count into the task journal or
   a dated research note.
4. Repeat after playbook deploy (`tausik_memory_brief` + lite skills) on a
   matched second chat; compare rounds only — never USD.

When a future host ledger exists, fill the before/after cells here without
rewriting this honesty section.
