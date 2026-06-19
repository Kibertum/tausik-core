# Kilo Code + z.ai (GLM)

TAUSIK runs as a first-class MCP host inside **Kilo Code** (the VSCode addon and
its CLI), driven by **z.ai GLM** models. This works because of two design
choices (Decision #119):

- **Kilo is a runtime host** (axis-1) — it owns the bootstrap directory, the MCP
  config, and active-model detection. It is the only thing that changes when you
  switch IDE.
- **z.ai GLM is a model family** (axis-2) — pure data in `model_profiles`, not
  code. Switching or adding GLM models needs **no code change**.

z.ai's endpoint is **Anthropic-compatible**, so the session transcript looks
exactly like Claude's — only the `model` field reads `glm-*`. Routing,
verdicts, and cost all work unchanged.

---

## 1. Point your agent at z.ai

z.ai exposes an Anthropic-compatible endpoint. Set these for Claude Code **or**
Kilo (Kilo respects the same Anthropic env vars):

```bash
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_AUTH_TOKEN="<your-z.ai-api-key>"   # NEVER commit this
```

> **Secret hygiene:** the z.ai key is a credential. Keep it in your shell
> profile or the IDE's secret store — never in `.tausik/config.json`, `.kilo/`,
> or anything tracked by git.

The GLM Coding Plan ($10/mo tier) gives access to the GLM family
(`glm-4.5-air`, `glm-4.6`, and the `glm-5.x` line).

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
