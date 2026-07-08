# z.ai GLM under TAUSIK (Claude Code & Kilo)

TAUSIK runs on **z.ai GLM** models under any Anthropic-compatible host. GLM is a
**model family** (axis-2, Decision #119) — pure data in `model_profiles`, not
code — so it is **independent of which host you run in**. The simplest and most
capable path is **Claude Code**: the host is unchanged, so every SENAR gate keeps
firing and only the `model` field reads `glm-*`.

- **Host** (axis-1) = Claude Code / Kilo / Cursor / Qwen — owns the bootstrap
  directory, the MCP config, and active-model detection.
- **Model family** (axis-2) = Claude vs z.ai GLM — pure data. Switching or adding
  GLM models needs **no code change**.

z.ai's endpoint is **Anthropic-compatible**, so the session transcript looks
exactly like Claude's — routing, verdicts, and cost all work unchanged.

> **Subscription, not per-token.** The z.ai **GLM Coding Plan** (from ~$10/mo) is
> a flat-fee subscription with usage quotas — not pay-as-you-go API billing. Same
> spirit as running Claude Code on a Max/Pro plan; you keep working on a
> subscription rather than metered tokens.

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

The **same two env vars** also drive **Kilo** and any other Anthropic-compatible
host — the sections below cover Kilo-specific bootstrap. Available GLM models
today include `glm-4.5-air`, `glm-4.6`, and the `glm-5.x` line (§4).

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
      "command": ["<python>", "${workspaceFolder}/.kilo/mcp/project/server.py", "--project", "${workspaceFolder}"],
      "enabled": true
    }
  }
}
```

Paths are **rename-proof**: a server inside the project and `--project` use
`${workspaceFolder}` (Kilo expands it at launch), so renaming the project folder
does not break the config. An external lib server keeps its absolute path.
Existing servers and other keys are **merged**, not overwritten. Re-running is
idempotent.

**Restart Kilo** after bootstrap so it loads the new MCP config.

### If your Kilo build reads neither default path

Override the target(s) in `.tausik/config.json`:

```json
{ "kilo": { "config_paths": ["kilo.jsonc"] } }
```

(paths are project-relative; the list fully replaces the defaults.)

## 3. Tell TAUSIK which GLM model is active

Kilo has no Claude-style JSONL transcript, so TAUSIK reads the active model from
(in order):

1. the `KILO_MODEL` environment variable — e.g. `export KILO_MODEL=glm-4.6`
2. a `model` field in `.kilo/kilo.json` (or `~/.config/kilo/kilo.json`)

With that set, `task start` shows GLM recommendations and correct
under/over-powered verdicts. Without it, recommendations fall back to
`model_profiles.default_family` (below) and then to Claude.

## 4. Switch / add GLM models — no code change

Defaults shipped in `scripts/model_profiles.py`:

| Capability rank | GLM model |
|-----------------|-----------|
| light (`haiku`) | `glm-4.5-air` |
| mid (`sonnet`)  | `glm-4.6` |
| strong (`opus`) | `glm-4.6` |
| flagship (`fable`) | `glm-4.6` |

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

## How it fits together

```
Kilo Code (addon/CLI)  ──MCP──▶  tausik-project server  (.kilo/kilo.jsonc | .kilocode/mcp.json)
        │
        └── model: glm-4.6  ──▶  model_profiles (family=glm) ──▶ routing rank → glm model + verdict
```

The runtime is Kilo; the model is GLM. Neither knows about the other — that
separation is what makes "TAUSIK in Kilo with any z.ai model" a config exercise,
not a code one.
