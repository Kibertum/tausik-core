# Model Providers

TAUSIK is model-agnostic. Skills work with any LLM that supports tool use.

## Supported Platforms

"Scaffolded" means `bootstrap.py --ide <name>` has a generator branch for it: it
writes the config, wires the MCP servers, and installs the skills. Anything not
scaffolded gets no wiring from TAUSIK — you would have to configure the host by
hand. The scaffolded set is the single source of truth in
`bootstrap/bootstrap_config.py::SCAFFOLD_IDES`; keep this table in sync with it.

| Platform | Scaffolded | Config file | Skills location | Instructions file |
|----------|-----------|-------------|-----------------|-------------------|
| Claude Code | yes | `.claude/settings.json` | `.claude/skills/` | `CLAUDE.md` |
| Cursor | yes | `.cursor/settings.json` | `.cursor/skills/` | `.cursorrules` |
| Qwen Code | yes | `.qwen/settings.json` | `.qwen/skills/` | `QWEN.md` |
| Kilo Code | yes | `.kilo/` | `.kilo/skills/` | `AGENTS.md` |
| OpenCode | yes | `opencode.json` | `.opencode/skills/` | `.opencode/tausik-rules.md` |
| Codex | no | `.codex/config.toml` | — | `AGENTS.md` |
| Windsurf | no | `.windsurf/` | — | `.windsurfrules` |

> **OpenCode (since v1.7.0).** `bootstrap.py --ide opencode` writes `opencode.json`
> (MCP servers + the `instructions` key), puts the rules in
> `.opencode/tausik-rules.md`, and installs the QG-0 enforcement plugin at
> `.opencode/plugins/tausik-qg0.js` — a write with no active task is refused, exactly
> as in Claude Code.
>
> Three traps if you ever configure OpenCode by hand:
> 1. `tools` accepts **booleans only** (`"bash": false`). A `tools.qg0` object aborts
>    startup with `ConfigInvalidError` — TAUSIK never writes that key, and never
>    deletes yours.
> 2. Plugins live in `.opencode/plugins/` (**plural**). A singular `plugin/` directory
>    is not an error: it simply never loads.
> 3. Rules ship via the `instructions` key, **not** `AGENTS.md`. OpenCode resolves
>    AGENTS.md first-matching-file-wins, so yours would shadow ours forever;
>    `instructions` files are merged with your AGENTS.md instead. That is why
>    `--ide opencode` generates no AGENTS.md — it would put the same rules in the
>    context twice.
>
> **Codex is not scaffolded yet** — TAUSIK writes only an `AGENTS.md` for it.
> See [adding a new IDE](/docs/adding-new-ide).

## Using GigaChat (Sber)

GigaChat models can be used via OpenCode with liteLLM:

1. Get API credentials at https://developers.sber.ru/
2. Install OpenCode: `npm i -g opencode-ai` (or via brew) — OpenCode is built by
   [SST](https://opencode.ai); there is no `@anthropic-ai/opencode` package.
3. Configure `opencode.json`:
```json
{
  "model": "gigachat/GigaChat-2-Max"
}
```
4. Set environment: `export GIGACHAT_API_KEY=your_client_secret`
5. Run: `opencode` — uses GigaChat model with all TAUSIK skills

Available models: GigaChat-2-Max, GigaChat-2-Lite, GigaChat 3 Ultra (702B)

## Using Other Providers

OpenCode supports 75+ providers via liteLLM. Common examples:
- `openai/gpt-4o` — OpenAI GPT-4o
- `anthropic/claude-sonnet-4-5` — Anthropic Claude
- `google/gemini-2.5-pro` — Google Gemini
- `ollama/llama3` — Local Ollama models (free)

## Cost telemetry for non-Claude models

TAUSIK ships a price table only for Claude tiers — it will not invent a rate for
GigaChat, GPT, Gemini or a local model, because a fabricated price is worse than
an absent one. Left unconfigured, cost telemetry for such a model records
`cost_usd = 0.00` and prints a one-time stderr warning (`unknown ≠ free`) so the
zero is not mistaken for "this model is free".

To meter your own model, declare a flat USD-per-1M-tokens rate in
`.tausik/config.json` — the same rate is applied to input and output:

```json
{
  "llm_pricing_usd_per_million": {
    "gigachat/GigaChat-2-Max": 1.20,
    "ollama/llama3": 0.0
  }
}
```

An explicit `0.0` is honoured (a genuinely free local model), distinct from the
unpriced default: the warning fires only when there is neither a built-in price
nor an override. Negative or non-numeric entries are dropped.
