# Anthropic OSS — TAUSIK Applicability Report

_Generated 2026-04-25 by `research-anthropic-repos` task. Sources: github.com/anthropics public repos._

## Repos surveyed

| Repo | Stars | Lang | Summary |
|------|-------|------|---------|
| [knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | 11.5K | Python | Domain-specific plugins (skills + commands + MCP connectors) for knowledge workers |
| [anthropic-cli](https://github.com/anthropics/anthropic-cli) | 321 | Go | CLI for the Claude API; resource-based command pattern |
| [agent-sdk-workshop](https://github.com/anthropics/agent-sdk-workshop) | 29 | Python | Multi-stage agent patterns (tools → delegation → memory) |
| [original_performance_takehome](https://github.com/anthropics/original_performance_takehome) | 3.8K | Python | Performance eval framework with cycle-counting benchmarks |
| [skills](https://github.com/anthropics/skills) | 123K | Markdown | Lightweight skill spec (YAML frontmatter + Markdown, zero deps) |
| [claude-code-action](https://github.com/anthropics/claude-code-action) | 1.7K | YAML/TS | GitHub Actions integration with mode detection |
| [financial-services-plugins](https://github.com/anthropics/financial-services-plugins) | 7.7K | Python | Vertical-specific plugin template extending knowledge-work-plugins |

## Applicable ideas

### 1. Skill manifest spec & registry (simple, source: anthropics/skills)

**Why TAUSIK cares:** TAUSIK ships 20+ skills in `agents/{role}/skills/` but lacks a machine-readable registry. YAML frontmatter (name, description, tags, activation triggers) would let the CLI expose `tausik skill list --filter agent` and auto-enable skills based on task context.

**Sketch:** Add `skill.yaml` alongside each `SKILL.md` with `name`, `role`, `stack_affinity`, `triggers` (complexity threshold), `dependencies`. CLI reads `.tausik/skills.json` (generated registry) on `task start`. Gates can warn if multiple conflicting skills match.

### 2. Resource-based CLI hierarchy with flat args (simple, source: anthropics/anthropic-cli)

**Why TAUSIK cares:** Current `tausik task start <slug>` works, but `task log <slug> "msg" --phase planning` exposes nested-positional pain. Flat-flag pattern (`ant messages create --max-tokens Y`) is more scriptable, easier to compose in Bash.

**Sketch:** Audit `project_parser.py` to push positional args toward required flags: `tausik task start --slug foo` (allows `--slug @file.txt`), `tausik memory add --type pattern --content "…"`. Improves shell integration and IDE argument hints.

### 3. Progressive capability scaffolding for subagents (medium, source: anthropics/agent-sdk-workshop)

**Why TAUSIK cares:** TAUSIK's batch workflow (`/run plan.md`) spins up parallel subagents with no official scaffolding for multi-stage composition (basic → tool-using → delegating → memory-aware). Anthropic's 4-stage pattern gives a roadmap.

**Sketch:** Add `agents/agent-templates/{stage}.md` (0=basic prompt, 1=mcp_servers list, 2=AgentDefinition + Task tool delegate, 3=session hooks for memory). `/batch` skill references these and suggests a stage matching the user's complexity estimate.

### 4. CI/CD mode inference (medium, source: anthropics/claude-code-action)

**Why TAUSIK cares:** TAUSIK batch agents run headless and could detect context (PR comment / scheduled cron / interactive CLI) and auto-adjust behavior (respond with comment vs. write file vs. print JSON). Avoids manual flags.

**Sketch:** `UserPromptSubmit` hook inspects Git, env vars, and parent process: `TAUSIK_TASK_SLUG` + cron → auto `--phase review` + force `--ac-verified`. `gh pr comment` → auto-post summary. Reduces CI config boilerplate.

### 5. Validated evaluation tier system (simple, source: anthropics/original_performance_takehome)

**Why TAUSIK cares:** TAUSIK metrics track FPSR / DER / lead time but no standardized "achievement tier". Tier bands (bronze/silver/gold/platinum) give aspirational targets and regression detection.

**Sketch:** `agents/evals/tiers.json`: bronze (FPSR <80%), silver (<90%), gold (<95%), platinum (<98%). Gates warn on tier regression. `/metrics` displays tier + rank.

### 6. Brain connector abstraction (medium, source: anthropics/knowledge-work-plugins)

**Why TAUSIK cares:** TAUSIK's brain MCP is hard-coded to Notion. Knowledge-work-plugins splits skills (Markdown) from connectors (`.mcp.json`), letting users swap HubSpot ↔ Slack ↔ Linear without touching Python.

**Sketch:** Refactor `agents/brain/`: keep `.claude/mcp/brain/` as core orchestrator; new `.claude/connectors/brain-notion.mcp.json` (env-var pluggable URL); docs show fork pattern. Skills reference brain via `{brain:query "topic"}` syntax.

### 7. Lightweight skill spec (simple, source: anthropics/skills)

**Why TAUSIK cares:** TAUSIK's SKILL.md files are Markdown but lack standardization. Anthropic's spec enforces YAML structure (name, description; examples, guidelines as sections) — enables `skill list --search` and filtering by role/stack.

**Sketch:** Upgrade `agents/skills/{name}/SKILL.md` headers: `---` YAML fence with `name`, `role`, `stacks` (list), `complexity_ideal`, `examples_count`. CLI parses on `skill install`. Zero runtime deps.

### 8. Session hooks for mode-specific behavior (medium, source: anthropics/agent-sdk-workshop)

**Why TAUSIK cares:** TAUSIK already uses hooks (PreToolUse, PostToolUse, SessionStart). A "before agent thinks" hook variant could inject mode-specific context.

**Sketch:** Formalize `SessionModeDetected` hook variant. Mode "batch" → inject "Environment: headless, disable interactive prompts". Mode "review" → inject checklist template. DRY mode-specific system prompts.

### 9. Multi-provider auth abstraction (complex, source: anthropics/claude-code-action)

**Why TAUSIK cares:** TAUSIK ships as CLI but agents might run on Bedrock (AWS), Vertex (GCP), or Foundry (enterprise). The action abstracts 4 backends behind one API.

**Sketch:** Add `--provider bedrock | vertex | foundry | anthropic` flag. `project_config.py` lazy-loads provider SDKs (not core deps). Skills don't care which backend; gates query cost differently per provider.

## Not applicable (skipped)

- claudes-c-compiler, buffa, connect-rust — compiler/infrastructure internals
- claude-desktop-buddy, maestro, argo-cd — closed-domain or non-agent orchestration
- homebrew-tap, tokio, moka — package management / Rust runtime

## Recommended next steps

Top 3 conversion candidates with proposed slugs:

1. **`tausik-skill-manifest`** (simple, story `tausik-infra`) — add `skill.yaml` + CLI filtering; ~2-3h. Enables auto-activation by role/stack.
2. **`tausik-metrics-tiers`** (simple, story `tausik-infra`) — define tier bands in config; ~3-4h. SENAR compliance scoring + regression detection.
3. **`tausik-brain-swappable-backend`** (medium, story `tausik-infra`) — decouple brain MCP from Notion; ~6-8h. Opens brain to Slack/Linear/HubSpot users.
