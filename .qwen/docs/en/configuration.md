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

## Brain (Shared knowledge layer)

| Key | Default | Purpose |
|---|---|---|
| `brain.enabled` | `false` | Master switch for cross-project Notion brain. |
| `brain.local_mirror_path` | `~/.tausik-brain/mirror.db` | Local SQLite mirror of Notion DBs. Tilde + `$ENV` expanded. |
| `brain.notion_integration_token_env` | `TAUSIK_BRAIN_TOKEN` | Env var name holding Notion integration token. |
| `brain.database_ids` | `{}` | Notion DB IDs (`decisions`, `web_cache`, `patterns`, `gotchas`). Wizard-populated by `tausik brain init`. |
| `brain.private_url_patterns` | `[]` | URL patterns scrubbed before brain writes (regex strings). |
| `brain.project_names_blocklist` | `[]` | Project-name substrings scrubbed before brain writes. |

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
  "brain": {
    "enabled": true,
    "notion_integration_token_env": "TAUSIK_BRAIN_TOKEN"
  }
}
```

## Health check

`tausik doctor` (v1.3+) verifies that resolved config + venv + DB + skills are coherent and surfaces actionable next steps.
