# Configuration trust tiers

Implementation: [`scripts/config_trust.py`](../../scripts/config_trust.py).
SPEC: `sec-config-trust-tiers` (SEC, v1). Task: `l26-config-trust-tiers`.

## The problem

`.tausik/config.json` is an ordinary file inside the repository, and the
enforcement switches lived in it:

| Key | What it turned off |
|---|---|
| `qg0.scope_hard_gate` | the block on edits outside a task's declared scope |
| `risk.l3_block_on_high` | the external L3 review required to close a high-risk task |
| `task_done.auto_verify` | closes a task on an inline run, skipping the signed receipt |
| `gates.<name>.enabled` | the gate itself |
| `gates.<name>.severity` | demotes `block` to `warn` |
| `gates.<name>.trigger` | detaches the gate from events: enabled, never fires |
| `gates.<name>.file_extensions` | narrows the input filter until nothing matches |

A single write to a git-tracked file was enough for an agent to remove its own
supervision. The premise was already recorded in one spot in the tree —
`bootstrap_opencode.py`: *".tausik/config.json travels with the repo, so the
override is UNTRUSTED"*. This module generalizes it.

## The rule

Config is read from three tiers, least to most trusted:

| Tier | Location | Travels with the repo |
|---|---|---|
| project | `.tausik/config.json` | **yes** |
| user | `~/.tausik/config.json` | no |
| managed | `$TAUSIK_MANAGED_CONFIG` | no |

Higher tiers win on merge. On top of that: **a guarded key from the project tier
applies only if it is at least as strict as what the trusted tiers already
established** — or the framework default when they are silent.

- Tightening from the project tier passes through untouched. Live example from
  this repository's own config: `gates.mypy.enabled: true` against a `false`
  default survives.
- Weakening is rejected and the enforced value is **written in its place**, not
  deleted. Deleting would work only because every consumer happens to default to
  the strict value — an invisible coupling that breaks the first time somebody
  writes `cfg["gates"]["x"]["enabled"]` without a default.
- Tightening also beats the trusted tier. If an operator's
  `~/.tausik/config.json` merely restates a default (`mypy.enabled: false`) and
  the project sets `true`, `true` wins: "project may only tighten" holds in this
  direction too, or a tightening the policy already approved would be lost
  silently in the merge. On UNguarded keys ordinary tier precedence still
  applies.
- Rejection is never silent: every one is logged and surfaced in `tausik doctor`.

```
$ tausik doctor
  WARN  Config trust tier    qg0.scope_hard_gate: project value False rejected
                             (project scope may only tighten scope hard gate
                             (blocks edits outside a task's declared scope));
                             True applied
```

## What is guarded, and what is not

The seven keys above. The selection criterion is explicit: **a key is guarded
only if it TURNS OFF supervision** — not if it scopes supervision or tunes one
of its parameters.

Deliberately outside the perimeter (decision #137):

- `gates.filesize.exempt_files` — scopes the gate. Its legitimate values
  (generated directories, research dumps) are project-specific by nature and
  have no sensible home in a per-machine user tier. Handled separately in
  `l26-filesize-gate-revisit`.
- `verify_cache_ttl_seconds` — a parameter, not a switch. The real freshness
  control is `files_hash`: the cache is invalidated when files change, and
  different tasks have different `relevant_files` and therefore different
  hashes. TTL only bounds an unchanged tree, where a half-hour-old green is
  still evidence about that same tree. Its legitimate value depends on how long
  the individual project's suite takes.

### Off, spelled differently

Guarding `enabled` alone would be decorative. A gate that stays enabled but
loses every trigger never runs; a gate whose `file_extensions` is narrowed to
nothing never receives input. Both are "off" written another way. So `trigger`
and `file_extensions` are guarded as SETS: a project may extend them, never
shrink them. A non-list where a list belongs is rejected too — that is not a
legible tightening.

### Gate commands

`_validate_custom_gate` historically ran only for gates absent from
`DEFAULT_GATES`. That meant overriding `gates.ruff.command` skipped the
allowed-executable check entirely — a cloned repository could point a built-in
gate at any binary and the shell-less runner would execute it. Every command an
override supplies is validated now; a refused one falls back to the default
while the rest of the override still applies.

Still open: a command can be reduced to an ALLOWED but inert one
(`gates.ruff.command = "python -c pass"` — `python` is on the list, the gate
formally runs and is always green). Tracked as `l26-gate-command-neutering`.

## Threat surface — the honest boundary

**Closed: a repository cannot grant itself authority.** `.tausik/config.json`
arrives with every clone, fork and PR; `~/.tausik/config.json` does not. A
contributor can no longer ship a branch that quietly turns the gates off on the
reviewer's machine, and an agent editing the project config can no longer lower
its own bar.

**Not closed, stated plainly rather than implied:** an agent that can run
arbitrary shell commands can write `~/.tausik/config.json` or export
`TAUSIK_MANAGED_CONFIG` itself. Tiers are **not a sandbox**. What they buy is a
raised bar and, more importantly, **visibility**: weakening now has to happen
outside the repository, so it can no longer hide inside a diff that looks like an
ordinary config tweak. Real containment needs an enforcement point the agent
cannot reach at all — out of scope here.

## The reader / writer contract

The split is mandatory, not cosmetic:

| Function | Returns | For |
|---|---|---|
| `load_config()` | effective config (merge + policy) | **readers** |
| `load_config_with_rejections()` | the same plus the rejection list | `doctor`, introspection |
| `load_project_config()` | the raw project layer | **writers** |

`save_config()` persists whatever it is handed. A writer that read the effective
config would copy the user's and the operator's settings into the repository
file. Every round-trip writer (`ProjectService.gate_enable/gate_disable`, MCP
`_handle_gate_toggle`, brain `_ConfigOps`) reads the raw layer.

## `gates disable` behavior

Disabling a guarded gate from the project tier writes the key but does not change
behavior. Reporting success there would be exactly the silent lie this work
exists to remove, so the caller is told the truth:

```
$ tausik gates disable filesize
Gate 'filesize' NOT disabled — project scope may only tighten gate on/off
switch. The key was written to .tausik/config.json but the effective config
keeps True. To disable it for real, set it in the user tier
(~/.tausik/config.json) or in $TAUSIK_MANAGED_CONFIG.
```

## Environment variables

| Variable | Purpose |
|---|---|
| `TAUSIK_MANAGED_CONFIG` | path to the managed tier; unset means the tier is absent |
| `TAUSIK_USER_CONFIG` | overrides the user-tier path (tests, multi-account boxes) |

## Migrating an existing project

A project that disabled a gate in `.tausik/config.json` will find that gate
enabled after upgrading, with the key named in `tausik doctor`. That is
intentional. If the opt-out is legitimate — a sandbox, a CI image, a gate that
genuinely does not apply — move it to `~/.tausik/config.json` or to the file
`$TAUSIK_MANAGED_CONFIG` points at. Tightening from the project tier is
unchanged.

A corrupted, non-object, oversized or unreadable trusted layer is ignored with a
warning: it never crashes the framework and is never read as permission to
weaken — the policy stays in force.
