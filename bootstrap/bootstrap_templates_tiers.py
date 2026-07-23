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

- Project patterns / dead ends: TAUSIK `memory add` (SQLite `.tausik/tausik.db`).
- Host prefs: agent-specific auto-memory (`~/.claude/` is Claude-only — see glossary).
- **Memory-first:** `memory_search` BEFORE asking the user for / guessing an
  established project fact (hosts, env, paths, decisions). Store env facts as `context`.
- **Routing litmus:** would another agent, in another tool, need this to work on
  THIS project? Then `memory add` — never your host's own memory. Foreign sinks
  (`~/.claude/**/memory/`, `.cursor/rules/`, `.github/copilot-instructions.md`,
  `.aider*`, …) are blocked by the `memory_route` gate.
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
