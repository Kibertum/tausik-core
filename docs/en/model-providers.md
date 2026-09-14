**English** | [Русский](../ru/model-providers.md)

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
| Codex | yes | `.codex/config.toml` + `.codex/hooks.json` | `.codex/skills/` | `AGENTS.md` |
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
> **Codex (since v1.9.0).** `bootstrap.py --ide codex` writes `.codex/hooks.json`,
> deploys the skills to `.codex/skills/` and generates `AGENTS.md`, which Codex
> reads natively. The hook set is the SAME declaration Claude Code's profile uses,
> so a gate added to one host cannot silently miss the other.
>
> **If Codex does not show the TAUSIK tools after a restart.** Whether the
> project config takes precedence over the global `~/.codex/config.toml` depends
> on the host version, and there is one way to find out: open Codex and look at
> the tool list. The fallback needs no code change — copy the block between the
> `# >>> TAUSIK MCP servers` and `# <<< TAUSIK MCP servers` markers from
> `.codex/config.toml` into `~/.codex/config.toml`. The paths in it are absolute,
> so it works from either file, and the markers make it findable to remove later.
>
> MCP servers are registered in the PROJECT's `.codex/config.toml`, never in
> `~/.codex/config.toml`: a project's bootstrap does not own the user's home
> directory. The block is APPENDED between markers rather than rewritten —
> Python 3.11 ships `tomllib` for reading only, and a parse-and-reemit would
> drop the comments and section order that "preserve-first" is about. A file
> that does not parse is left untouched and reported: Codex would not read it
> either, and hiding someone's breakage under our block earns the complaint
> "TAUSIK broke my config".
>
> Codex has a real hook API — `PreToolUse`, `PostToolUse`, `SessionStart`,
> `SessionEnd`, `UserPromptSubmit`, `Stop`, and the same
> `hook_event_name`/`permissionDecision` protocol — so Rule 1 and the write ACL
> are ENFORCED there, not merely instructed, **once the user has trusted the
> project's hooks in Codex**. That precondition is the host's, not ours, and it
> was measured live rather than assumed (session #251): with the generated
> `.codex/hooks.json` present but NOT trusted, the exact forbidden
> `Path('outside.txt').write_text(...)` ran to completion — no hook fired, no
> refusal, the file existed. The same operation under a trusted profile was
> refused before the file existed. Nothing on disk distinguishes the two
> states, so no scan of the profile can report the second half; only the host
> knows. An untrusted generated profile enforces NOTHING and must not be
> described as protected.
>
> What it does NOT have is any workspace variable: `CLAUDE_PROJECT_DIR`,
> `CODEX_PROJECT_ROOT` and `workspaceFolder` are all absent. Hook commands are
> therefore written as absolute paths, which means renaming the project directory
> requires re-running bootstrap. A `.codex/hooks.json` carrying Claude's
> `${CLAUDE_PROJECT_DIR}` expands it to nothing and disables every gate while
> still listing them all — the failure this generator exists to prevent.

### Codex enforcement matrix

This is the closed set of governance contracts claimed for Codex in v1.9.
**Hard** means TAUSIK refuses the operation, either at its MCP/CLI service boundary
or by intercepting the host operation. It does not mean every advisory policy is a
block: for example, secret scanning retains its separately configured warn/strict
severity.

| Contract | Mode | Disk-backed mechanism |
|----------|------|-----------------------|
| QG-0 Context Gate | hard | `tausik_task_start` refuses an incomplete task through MCP and CLI. |
| QG-2 Implementation Gate / Verify-First | hard | `tausik_task_done` refuses closure without a fresh signed `tausik_verify` receipt. |
| Rule 9.2 Session limit | hard | `tausik_task_start` refuses work past the active-time limit. |
| Rule 1 Task before code | hard | `.codex/hooks.json` wires `task_gate.py` to Codex `PreToolUse` — **only after the user has trusted the project hooks in Codex**; an untrusted profile enforces nothing (measured live, session #251). |
| Rule 2 Scope Boundaries | hard | `.codex/hooks.json` wires `scope_write_gate.py` and `bash_write_gate.py` to Codex `PreToolUse` — **only after the user has trusted the project hooks in Codex**; shell coverage is the declared catalogue, not a claim to interpret every program. |

`tests/test_codex_support_matrix.py` reads both language tables, requires this
complete list, and generates a Codex profile before accepting any `hard` row. A
documentation edit cannot silently widen the promise beyond its mechanism — and
the two host-interception rows must carry the trust precondition in both
languages, because a `hard` that is true only under a condition the reader was
not told is a claim wider than the mechanism.

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

Declare rates in `.tausik/config.json`. **What the config says wins** — the
shipped Claude table is a seed, not the authority, so you can correct a rate
that has gone stale without editing Python:

```json
{
  "llm_pricing_usd_per_million": {
    "gigachat/GigaChat-2-Max": {"input": 0.60, "output": 2.20},
    "claude-sonnet-5": {"input": 2.00, "output": 10.00},
    "ollama/llama3": 0.0
  }
}
```

A value is either an object with `input` and `output`, or a bare number meaning
"both directions at this rate". **Prefer the object form**: no real tariff
charges the same for input and output, so a bare number necessarily prices one
of the two wrongly. The number form is still accepted because existing configs
use it.

An explicit `0.0` is honoured (a genuinely free local model), distinct from the
unpriced default: the warning fires only when there is neither a configured
price nor a shipped one. Entries that are negative, non-numeric, or an object
missing `input` or `output` are dropped with a warning — half a tariff is not a
tariff, and a price that cannot be read is reported as **unknown**, never as
`$0.00`. `tausik metrics` names any model it carries tokens for but cannot
price, instead of folding those tokens into a confident zero.
