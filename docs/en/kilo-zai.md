**English** | [Русский](../ru/kilo-zai.md)

# z.ai GLM under TAUSIK (Claude Code & Kilo)

<!-- doc-map: reader=user; zone=ide-and-skills -->

TAUSIK treats **z.ai GLM** as a model family and the program that runs it as a
separate host. Routing profiles are portable data; enforcement and usage evidence
remain host-specific. Claude Code and Kilo therefore need separate validation.

- **Host** (axis-1) = Claude Code / Kilo / Cursor / Qwen — owns the bootstrap
  directory, the MCP config, and active-model detection.
- **Model family** (axis-2) = Claude vs z.ai GLM — pure data. Switching or adding
  GLM models needs **no code change**.

An Anthropic-compatible endpoint does not make another host's transcript, gates,
quota or cost semantics identical to Claude Code. TAUSIK only claims the surfaces
measured on each host.

> **Subscription, not per-token.** The z.ai **GLM Coding Plan** (from ~$10/mo) is
> a flat-fee subscription with usage quotas — not pay-as-you-go API billing. Same
> spirit as running Claude Code on a Max/Pro plan; you keep working on a
> subscription rather than metered tokens.

### Kilo usage evidence in 1.11

Kilo 7.8.1 exposes a documented local SQLite session store. TAUSIK reads it in
read-only mode with `tausik metrics tokens --host kilo --json` or MCP
`tausik_metrics({"host":"kilo"})`. The two surfaces share one implementation,
deduplicate resumed responses and reconcile the five disjoint Kilo counters against
session totals. The sanitized project cache contains no prompts, credentials or raw
paths.

The report records observed Kilo, provider and model versions. Subscription quota,
task attribution and price remain unknown because the source does not expose them.
The adapter has been reconciled against real Kilo sessions. A deliberate GLM smoke
reached Kilo Gateway but failed before generation with HTTP 402; the report therefore
shows one failed GLM record and zero completed GLM responses. Live parity remains
pending credits or a configured z.ai subscription.

---

## 1. GLM under Claude Code (recommended — subscription, full gates)

Keep **Claude Code** as your host and point it at z.ai. Because the host never
changes, **all SENAR enforcement gates keep firing** (QG-0 no-code-without-task,
QG-2 verify, scope / secret / firewall) — GLM simply becomes the brain.

Set two environment variables (shell profile or the IDE secret store — **never**
commit them):

```bash
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_AUTH_TOKEN="<your-z.ai-key>"   # z.ai GLM Coding Plan key
```

Launch Claude Code. It now reasons through GLM on your z.ai subscription; TAUSIK
reads `model: glm-*` from the transcript and routes within the GLM family
(`model_profiles`, family `glm`). To recommend GLM tiers from the first message,
set `"default_family": "glm"` in `.tausik/config.json` (see §4).

> **Secret hygiene:** the z.ai key is a credential. Keep it in your shell profile
> or the IDE's secret store — never in `.tausik/config.json`, `.kilo/`, or
> anything tracked by git.

> **Smoke-test billing before you rely on it.** z.ai sells the Coding Plan against
> its `/api/coding/paas/v4` endpoint; confirm your Coding-Plan quota actually
> bills through the Anthropic-compatible `/api/anthropic` endpoint used above
> (send one request, check the z.ai dashboard) so usage draws on the subscription
> and not a pay-as-you-go wallet. z.ai documents the Coding Plan for Claude Code,
> but pin this down first.

Kilo configures providers through its own host surface; do not infer its active
provider from Claude Code environment variables. The sections below cover
Kilo-specific bootstrap and model detection.

## 2. Bootstrap TAUSIK for Kilo

```bash
python .tausik-lib/bootstrap/bootstrap.py --ide kilo
```

This writes the TAUSIK MCP server stanza to **both** known Kilo config paths
(robust across Kilo versions — Decision #120):

- `.kilo/kilo.jsonc` (current kilo.ai docs)
- `.kilocode/mcp.json` (older Cline-lineage builds)

Both contain the same `mcp` entry:

```json
{
  "mcp": {
    "tausik-project": {
      "type": "local",
      "command": [
        "<abs-path>/.tausik/venv/Scripts/python.exe",
        "<abs-path>/.kilo/mcp/project/server.py",
        "--project",
        "<abs-project-path>"
      ],
      "enabled": true
    }
  }
}
```

Paths are **absolute** (forward-slashed). Measured on the live host: Kilo Code
7.8.3 expands no `${workspaceFolder}` in MCP commands — the literal occurs zero
times in its `kilo.exe` CLI, the process that spawns the servers — so an
earlier generator emitted a stanza that parsed but could never spawn. Absolute
paths are the Codex precedent: renaming the project directory requires
re-running bootstrap, and `tausik doctor` runs a live initialize probe against
the configured command, so a config the host cannot load is reported instead of
assumed. Existing servers and other keys are **merged**, not overwritten.
Re-running is idempotent.

**Restart Kilo** after bootstrap so it loads the new MCP config.

### If your Kilo build reads neither default path

Override the target(s) in `.tausik/config.json`:

```json
{ "kilo": { "config_paths": ["kilo.jsonc"] } }
```

(paths are project-relative; the list fully replaces the defaults.)

## 3. Real-time QG-0 gate (Kilo plugin)

The same bootstrap also deploys a **gate plugin** to
`.kilo/plugins/tausik-gates.js`. Kilo auto-loads that directory, so the file is
the registration. It is a port of the OpenCode QG-0 plugin (same CLI question,
same cache, same policies):

- Before every `write`/`edit`/`apply_patch` it asks the TAUSIK CLI whether any
  task is active and **refuses the write without one** (SENAR Rule 1).
- `bash` is deliberately not gated — that would block the very command that
  starts a task. Rule 2 (scope) and secret scanning are not enforced here
  either; the same is true of the OpenCode plugin, and `tausik doctor`'s
  enforcement-coverage line is the per-host truth.
- The CLI verdict is cached against the TAUSIK DB signature (plus a small TTL),
  and the cache may only err toward strictness: `task done` moves the WAL, so a
  cached "allowed" cannot survive it.
- If the CLI is unreachable the gate **fails open loudly** — every ungated
  write prints a `DEGRADED` warning and a supervision-degradation row is
  recorded. Set `TAUSIK_HOOK_FAIL_SECURE=1` to block instead of allow;
  `TAUSIK_SKIP_HOOKS=1` disables the gate (recorded as a bypass).

Honest status: the gate is unit-verified by executing the hook under Node
(`tests/test_host_gate_plugins.py`, both hosts parametrized), and `tausik
doctor` reports `kilo: 2 plugins` — but a live denial inside a running Kilo
session still needs one host restart to observe. Until then the gate is
deployed and proven at the harness level, not yet observed live.

## 4. Tell TAUSIK which GLM model is active

Kilo has no Claude-style JSONL transcript, so the second plugin shipped with
TAUSIK — `tausik-observe.js` — records the model the host is actually running:
on every chat event it writes the host's `{providerID, modelID}` to
`.tausik/runtime/active_model.json` (model ids only — no keys, no conversation
content). The full chain, in order:

1. `.tausik/runtime/active_model.json` — written live by the observer plugin,
   so the model picked in Kilo's UI (z.ai, Ollama, LM Studio, anything) is
   what TAUSIK sees;
2. the `KILO_MODEL` environment variable — e.g. `export KILO_MODEL=glm-4.7`;
3. a `model` field in `.kilo/kilo.jsonc` (JSONC comments allowed),
   `.kilocode/kilo.json` or `~/.config/kilo/kilo.jsonc`.

Every value passes the same token validation before it is stored, and schema
v73 records with the session WHICH source declared it (`provider:kilo`, an
env-var name, …) — the "Session model" line of `tausik doctor` names that
source. When nothing answers, nothing is invented: the doctor keeps its
warning and the model is never guessed from the host's name.

With a model recorded, `task start` shows GLM recommendations and correct
under/over-powered verdicts. Without one, recommendations fall back to
`model_profiles.default_family` (below) and then to Claude.

Honest status: the observer and the whole chain are unit-verified
(`tests/test_kilo_observe_plugin.py`, `tests/test_providers.py` — including
the `TAUSIK_AGENT_MODEL` variable a bash tool receives), but the live
chat-event write and the shell-env injection inside a running Kilo session
still need one host restart to observe.

## 5. Switch / add GLM models — no code change

Defaults shipped in `scripts/model_profiles.py`:

| Capability rank | GLM model |
|-----------------|-----------|
| light (`haiku`) | `glm-4.5-air` |
| mid (`sonnet`)  | `glm-4.7` |
| strong (`opus`) | `glm-4.7` |
| flagship (`fable`) | `glm-4.7` |

Override or extend any of these — and pin GLM as the default family — in
`.tausik/config.json`:

```json
{
  "model_profiles": {
    "default_family": "glm",
    "families": {
      "glm": {
        "opus":  { "model": "glm-5.2", "display": "GLM-5.2" },
        "fable": { "model": "glm-5.2", "display": "GLM-5.2" }
      }
    }
  }
}
```

`default_family: "glm"` makes `task start` recommend GLM models even before any
transcript/`KILO_MODEL` detection — ideal when you only ever run Kilo + z.ai.

Local families need no code either. Model ids are normalized before every
lookup: the provider prefix (`zai-coding-plan/glm-4.7`, `ollama2/glm-4.5-air`)
and a trailing context-window suffix (`glm-4.7 [200k]`) are stripped, so the
same shipped table answers for them. A name the table does not know — a tag
that is part of the id (Ollama's `:latest`) or a purely local name — is one
config entry:

```json
{
  "model_profiles": {
    "families": {
      "glm": {
        "haiku": { "model": "ollama/glm-4.5-air:latest", "display": "GLM-4.5-Air (local)" }
      }
    }
  }
}
```

## 6. Host-level permission policy (the second extension point)

Kilo's config schema (`$schema: https://app.kilo.ai/config.json`) accepts a
`permission` key: per-operation `ask` / `allow` / `deny`, and the rule-shaped
operations (`edit`, `bash`, …) accept `{pattern: action}` objects. Since
2026-10-08 `bootstrap --ide kilo` writes a managed policy alongside the MCP
stanza — the same rules TAUSIK states in prose, now refused by the host itself:

| Operation | Pattern / scope | Action | Why |
|---|---|---|---|
| `edit` | `.tausik/tausik.db` | **deny** | the DB belongs to the service layer; a raw edit corrupts what every tool reads |
| `edit` | `.kilo/plugins/*` | **deny** | enforcement artifacts are bootstrap-managed; a hand edit is drift by definition |
| `bash` | `git push*` | **ask** | publication leaves the machine only with the owner's word (SENAR Rule 7) |
| `bash` | `sqlite3*` | **ask** | no raw SQLite against the project DB |
| `external_directory` | — | **deny** | the agent works inside the project (Rule 2 scope boundaries) |

Merge semantics mirror the `mcp` stanza: your own keys and rules are preserved,
managed keys are rewritten idempotently and win over a user value on the same
pattern (a governance rule you can name is one the file must keep). A global
string `permission: "ask"|"allow"|"deny"` you set yourself is left untouched —
a string cannot carry patterns, and your global choice is yours. Opt out via
`.tausik/config.json` → `{"kilo": {"permission_policy": false}}`.

`tausik doctor`'s enforcement-coverage line counts these as a third shape —
`kilo: 2 plugins and 5 permission rules` — read from the deployed config
itself, never from a list of intentions.

## How it fits together

```
Kilo Code (addon/CLI)  ──MCP──▶  tausik-project server  (.kilo/kilo.jsonc | .kilocode/mcp.json)
        │
        ├── QG-0 gate plugin       (.kilo/plugins/tausik-gates.js) — refuses writes with no active task
        │
        ├── model observer plugin  (.kilo/plugins/tausik-observe.js) — writes .tausik/runtime/active_model.json
        │
        └── model: glm-4.7  ──▶  model_profiles (family=glm) ──▶ routing rank → glm model + verdict
```

The runtime is Kilo; the model is GLM. Neither knows about the other — that
separation is what makes "TAUSIK in Kilo with any z.ai model" a config exercise,
not a code one.
