"""Tier-specific rule-pack bodies — the `minimal` and `full` variants.

Split out of `bootstrap_templates` for the 400-line cap the framework enforces
on everyone else, on the seam that was already there: everything here is
selected by `context_tier` in `.tausik/config.json`, while what remains in
`bootstrap_templates` is the standard body every tier shares. `build_full_body`
still composes them — this module holds no logic, only the alternative bodies.

The precedent is `bootstrap_hooks`, extracted from `bootstrap_generate` for the
same cap: relocation only, contract unchanged.
"""

from __future__ import annotations

MINIMAL_WORKFLOW = """## Workflow (minimal tier)

`/start` → `/plan` or `task start` → implement → `.tausik/tausik verify --task <slug>` →
`task done --ac-verified` → `/end`.

Full diagram: [Workflow](docs/en/workflow.md) (or `docs/ru/workflow.md`).
"""

MINIMAL_MEMORY = """## Memory (minimal)

- **Project memory** — "here it is done this way": `memory add` (SQLite `.tausik/tausik.db`).
- **Shared knowledge** — "the tool is built this way", true beyond this project: `memory add --global`
  (`~/.tausik-knowledge/knowledge.db`; not redacted — never a secret or a client name).
- **Agent auto-memory** — the user's own prefs: host-specific (`~/.claude/` is Claude-only — see glossary).
- **Memory-first:** `memory_search` BEFORE asking the user for / guessing an
  established project fact (hosts, env, paths, decisions). Store env facts as `context`.
- **Routing litmus:** would another agent, in another tool, need this to work on
  THIS project? Then `memory add`; true of the tool beyond this project? `memory add --global` —
  never your host's own memory. Foreign sinks (`~/.claude/**/memory/`, `.cursor/rules/`,
  `.github/copilot-instructions.md`, `.aider*`, …) are blocked by the `memory_route` gate.
"""

MINIMAL_COMMANDS = """## Commands (minimal)

```bash
.tausik/tausik status
.tausik/tausik verify --task <slug>
.tausik/tausik task done <slug> --ac-verified
.tausik/tausik task log <slug> "…"
```

Full CLI: [docs/en/cli.md](docs/en/cli.md).
"""

COMPACTION_CONTRACT = """## Compaction contract (what must survive a context compaction)

Compaction can be instructed; an uninstructed one drops the context whose value shows up later. When your host compacts the conversation, carry these forward VERBATIM, by name — and drop narration, tool output and resolved intermediate states first:
1. **The active task and its slug** — and its current plan step.
2. **The declared scope and the verify receipt** — `relevant_files`, the last `verify` run id / handle.
3. **This session's measurements with their numbers** — a lost measurement costs the run that produced it.
4. **Retired or superseded rules** — a forgotten retirement resurrects a dead rule.
5. **Owner prohibitions** — in the owner's words.
6. **Open forks** — decisions raised and not taken, with the options named.
"""

MINIMAL_COMPACTION = """## Compaction (minimal)

Carry forward verbatim through any compaction: the active task and slug, the declared
scope and verify receipt, this session's measurements, retired rules, owner prohibitions,
open forks. Full contract: `context_tier: standard`.
"""

MINIMAL_TIER_FOOTER = """## Rule pack size

This body was generated with **`context_tier: minimal`** (`.tausik/config.json`). Switch to
`standard` or `full` and re-run TAUSIK bootstrap / refresh for long-form tool routing, full
SENAR tables, and skill/role sections.
"""

FULL_TIER_NOTE = """## Deep onboarding (full tier)

Use this only when you routinely change gates, MCP tooling, or bootstrap templates. Read
[Architecture](docs/en/architecture.md) and [SENAR compliance matrix](docs/en/senar-compliance-matrix.md)
alongside this file.
"""
