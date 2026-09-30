**English** | [Русский](../ru/configuration.md)

# TAUSIK Configuration Reference

<!-- doc-map: reader=user; zone=configuration -->

All knobs live in `.tausik/config.json` at project root. Anything not set falls back to the documented default. To override, add the key under the top-level object (NOT under `bootstrap` — that section is bootstrap-managed).

See also: [environment.md](environment.md) — env vars, [permissions.md](permissions.md) — permission modes.

## Session signals (SENAR Rule 9.2 — advice, not gates since 1.10)

| Key | Default | Purpose |
|---|---|---|
| `session_max_minutes` | `180` | Advisory threshold on session ACTIVE minutes: above it `task start`, `status` and the Stop hook print advice; nothing refuses. `0` switches it off. |
| `session_idle_threshold_minutes` | `10` | Gap (in minutes) above which a pause between `events` rows is treated as AFK (excluded from active-time sum). |
| `session_warn_threshold_minutes` | `150` | Stop-hook reminder threshold in `session_cleanup_check.py`. Should be < `session_max_minutes`. |
| `session_capacity_calls` | `200` | Per-session tool-call budget. A task `call_budget` above what remains is an advisory line in `task start`, not a refusal. |
| `answer_budget_words` | `200` | Word budget for the agent's final answer. On the next prompt, an answer over it (or without a verdict in its first line) gets one advisory line with the numbers; nothing is blocked. Measure with `tausik metrics answers`. |
| `checkpoint_calls` | `40` | Calls since the last handoff before checkpoint advice (derived from the ledger). `0` switches it off. |
| `journal_freshness_calls` | `40` | Calls since an active task's last log entry before journal advice. `0` switches it off. |
| `audit_every_closures` | `17` | Task closures since the last audit mark before the SENAR 9.5 audit is overdue. |

## Code search (RAG) languages

| Key | Default | Meaning |
|-----|---------|---------|
| `rag.extra_extensions` | `{}` | Extra file types to index, `{".unity": "unity-scene"}`. A built-in extension cannot be overridden. Godot (`.gd`, `.gdshader`, `.tscn`, `.tres`, `.godot`) is built in since 1.10. |
| `rag.boundaries` | `{}` | Where to cut a language into chunks, `{"unity-scene": "^--- !u!"}` (a multiline regex). A bad entry is skipped and named in `rag_status` under `language_config.problems`. |

## Update check

| Key | Default | Meaning |
|-----|---------|---------|
| `updates.check` | `true` | At most once a day, SessionStart runs `tausik update-check` detached: one anonymous GET to GitHub's `releases/latest` of `Kibertum/tausik-core`, nothing about the project in it. `status` then names a newer release. `false` switches it off; `tausik doctor` shows the state. |

## Verification cache (SENAR Rule 5)

| Key | Default | Purpose |
|---|---|---|
| `verify_cache_ttl_seconds` | `600` | How long a green verify run is reused before re-running gates. Lower for security-critical projects. |

## Settings met in the quick-start

All keys sit at the root of `.tausik/config.json` unless a path says otherwise.

| Key | Default | Purpose |
|---|---|---|
| `context_tier` | `"standard"` | Size of the generated rules file: `"minimal"` (shorter), `"standard"`, `"full"` (extended pointers). Bootstrap refuses an unknown value; `tausik doctor` checks drift against the saved tier. |
| `output_mode` | `"off"` | `"caveman"` adds a directive for terse, telegraphic answers. Code, commands, tool output, error messages, acceptance-criteria evidence and decisions stay whole. The answer rules (shape, exceptions, pre-send check) ship in every rules file regardless of this key. A bad value falls back to `"off"`. The "~65% reduction" is the caveman project's own figure, not measured here. |
| `model_profile` | unset | Host profile slug (`a-z`, digits, hyphens), e.g. `claude`, `codex`. Bootstrap writes it when `TAUSIK_MODEL_PROFILE` is set; an invalid value aborts bootstrap. `python bootstrap/bootstrap.py --refresh` refreshes config only. |
| `task_done.auto_verify` | `false` | `true` makes `task done` run the gates inline and close **without a signed receipt**. It is not a bypass of the gates — they still run — but it gives up the receipt, so the config trust check treats it as a weakening and a trusted tier sets it back (`scripts/config_trust.py`). Prefer `task done <slug> --ac-verified --verify`: one call, with the receipt. |

**Rules files are preserved once written.** `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `QWEN.md` and the OpenCode rules file are not rewritten by bootstrap when they exist, so changing `context_tier` or `output_mode` later does not reach them. Bootstrap says so; delete the generated file and run bootstrap again, or edit it by hand.

**The MCP close returns structure.** `tausik_task_done` answers with `stage`, `gate_results` and `blocking_failures`, so an agent can fix what failed without parsing prose.

## Stacks

| Key | Default | Purpose |
|---|---|---|
| `custom_stacks` | `[]` | List of custom stack slugs accepted by `task add --stack X`. |

## Gates

| Key | Default | Purpose |
|---|---|---|
| `gates` | `{}` | Per-gate overrides: `{ "pytest": { "enabled": true }, "filesize": { "max_lines": 600 } }`. Merges over `default_gates.py`. |

## Agent-instruction files (the DYNAMIC block)

`tausik update-claudemd` rewrites the block between `<!-- DYNAMIC:START -->`
and `<!-- DYNAMIC:END -->` in CLAUDE.md and, when one sits beside it, in
AGENTS.md. AGENTS.md is tracked in most projects, so what goes into it is a
policy, not an accident (GitLab #14):

| Key | Default | Purpose |
|---|---|---|
| `claudemd.sibling_dynamic` | `true` | `true`: AGENTS.md is refreshed with the block **minus** "Shared knowledge — from other projects" — other projects' knowledge never enters this repository's history, and a memory tail left with nothing under it is dropped. `false`: AGENTS.md is not written at all; CLAUDE.md is refreshed as before. Only the JSON boolean `false` turns it off — the string `"false"` or `0` is read as on. The key is read from the `.tausik/` beside the file being written. |

The `claudemd_state` commit gate judges each file against the same plan the
writer follows: a sibling the policy does not write is not judged, and a
sibling whose only knowledge would be foreign owes no tail.

## Publication (what a redacted export hides)

The shared store (`~/.tausik-knowledge`) needs no configuration: `--global` on
`decide` / `memory add` writes to it, `$TAUSIK_HOME` moves it. These keys feed
`knowledge export --redacted` only (see [knowledge-store.md](knowledge-store.md)).

| Key | Default | Purpose |
|---|---|---|
| `publication.project_names` | `[]` | Project names to replace with `[REDACTED:project]`, in addition to this project's directory name. |
| `publication.private_url_patterns` | `[]` | Regex strings; a URL matching one becomes `[REDACTED:url]`. |
| `brain.local_mirror_path` | `~/.tausik-brain/brain.db` | Only read by the one-off `knowledge import-brain`: where the retired Notion transport left its local mirror. |

## Example

```json
{
  "session_max_minutes": 240,
  "session_idle_threshold_minutes": 15,
  "verify_cache_ttl_seconds": 1200,
  "custom_stacks": ["ruby", "elixir"],
  "gates": {
    "filesize": { "max_lines": 500 },
    "ruff": { "enabled": false }
  },
  "publication": {
    "project_names": ["acme"],
    "private_url_patterns": ["acme\\.internal"]
  },
  "claudemd": { "sibling_dynamic": false }
}
```

## Health check

`tausik doctor` (v1.3+) verifies that resolved config + venv + DB + skills are coherent and surfaces actionable next steps.
