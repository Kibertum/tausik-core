**English** | [Русский](../ru/configuration.md)

# TAUSIK Configuration Reference

All knobs live in `.tausik/config.json` at project root. Anything not set falls back to the documented default. To override, add the key under the top-level object (NOT under `bootstrap` — that section is bootstrap-managed).

See also: [environment.md](environment.md) — env vars, [permissions.md](permissions.md) — permission modes.

## Session limits (SENAR Rule 9.2)

| Key | Default | Purpose |
|---|---|---|
| `session_max_minutes` | `180` | Hard limit on session ACTIVE minutes before `task start` blocks. Use `tausik session extend --minutes N` to push live limit. |
| `session_idle_threshold_minutes` | `10` | Gap (in minutes) above which a pause between `events` rows is treated as AFK (excluded from active-time sum). |
| `session_warn_threshold_minutes` | `150` | Stop-hook reminder threshold in `session_cleanup_check.py`. Should be < `session_max_minutes`. |
| `session_capacity_calls` | `200` | Per-session tool-call budget. `task start` blocks if remaining capacity < task `call_budget`. |

## Verification cache (SENAR Rule 5)

| Key | Default | Purpose |
|---|---|---|
| `verify_cache_ttl_seconds` | `600` | How long a green verify run is reused before re-running gates. Lower for security-critical projects. |

## Stacks

| Key | Default | Purpose |
|---|---|---|
| `custom_stacks` | `[]` | List of custom stack slugs accepted by `task add --stack X`. |

## Gates

| Key | Default | Purpose |
|---|---|---|
| `gates` | `{}` | Per-gate overrides: `{ "pytest": { "enabled": true }, "filesize": { "max_lines": 600 } }`. Merges over `default_gates.py`. |

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
  }
}
```

## Health check

`tausik doctor` (v1.3+) verifies that resolved config + venv + DB + skills are coherent and surfaces actionable next steps.
