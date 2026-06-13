**English** | [Русский](/ru/docs/skills)

# Skills (v1.4)

Skills are intent-based instructions that define agent behaviour. You don't memorize names or syntax — you write what you want, and the agent picks the right skill. Slash-prefix (`/plan`, `/ship`) explicitly invokes one.

After bootstrap, **13 core skills** ship with TAUSIK from `harness/skills/` (plus `/brain` *conditionally* when the project has Notion configured — see [Shared Brain](shared-brain.md)). Additional **official / vendor skills** (20) are available on demand: install per-skill via `tausik skill install <name>`, or expand the whole bundle via `python .tausik-lib/bootstrap/bootstrap.py --include-official` (alias: `--include-vendor`). **Map of repo skills:** [Skill ecosystem (one page)](skill-ecosystem.md). **Bulk install by group:** [Skill Bundles](skill-bundles.md).

> **v1.4.x default change.** Before v1.4.x bootstrap auto-deployed all 38 source + registry skills (~1,520 tok in the system-reminder list). v1.4.x ships 13 + brain conditional (~480 tok) by default — saving ~1,040 tokens per turn. Re-run bootstrap with `--include-official` if you want the full set surfaced to the agent. **v1.4.0 also dropped 5 redundant skills** (`/go`, `/next`, `/diff`, `/onboard`, `/init`) — bringing the vendor count to 20. See **[Skill Bundles Migration](skill-bundles-migration.md)**.

**Multi-host variants:** skills can ship optional **`variants/<profile>.md`** overlays — see [Skill profiles & variants](skill-profiles.md).

## Core Skills (13 + brain conditional)

These are always available after bootstrap — the workflow primitives every TAUSIK project needs. `/brain` is the 14th core skill but only deployed when `tausik brain init` has set up Notion config (so projects that never use the shared brain don't pay its token cost).

### Workflow

| Skill | When |
|-------|------|
| `/start` | Begin a work session — loads handoff, status, memory block |
| `/end` | Wrap up the session — saves metrics + handoff |
| `/checkpoint` | Save context without ending the session (recommended every 30–50 tool calls) |
| `/plan` | Plan a task from a free-form description (interview phase + AC) |
| `/task` | Work on an existing task with QG-0/QG-2 enforcement |
| `/ship` | Wrap up a task: review + test + gates + commit |
| `/commit` | Create a standardized git commit |

### Knowledge

| Skill | When |
|-------|------|
| `/brain` *(conditional)* | Query/store cross-project knowledge in the Shared Brain (Notion + local mirror). Deployed only when `tausik brain init` has populated `brain.notion_db_ids` in `.tausik/config.json`. |
| `/explore` | Time-boxed investigation (default 30 min) before committing to an approach |
| `/interview` | Socratic Q&A — at most 3 questions to pin down requirements |
| `/reason` | Record a structured reasoning trace (intent→premise→action→verification) on a task — see [Reasoning Trace](reasoning-trace.md) |

### Quality

| Skill | When |
|-------|------|
| `/review` | Code review against 28-point SENAR checklist (5 parallel agents, iterative) |
| `/test` | Run or write tests, track coverage |
| `/debug` | Reproduce → isolate root cause → fix |

## Official / Vendor Skills (20)

Not auto-deployed by default. Two ways to surface them:

- **Per-skill (recommended).** `tausik skill install <name>` from `skills-official/` or the `tausik-skills` repo, then `tausik skill activate <name>`. Adds only what you ask for to the system-reminder list.
- **Whole bundle.** Re-run `python .tausik-lib/bootstrap/bootstrap.py --include-official` (alias: `--include-vendor`). Generates lightweight stubs for every entry in `skills-official/registry.json`. Use when you want the v1.3.x behaviour (~38 skills always visible).

### Quality / Discipline (opt-in)

| Skill | When |
|-------|------|
| `/zero-defect` | Session-scoped precision mode for high-stakes work (auth/payment/migration). Slows velocity 2–3× but reduces defects. Maestro-inspired. |
| `/skill-test` | Meta tool for skill authors — auto-generate and run scenarios for any skill |

### Document Extraction (opt-in)

| Skill | When |
|-------|------|
| `/markitdown` | Convert DOCX/PPTX/XLSX/HTML/EPUB/PDF to markdown via the markitdown CLI (requires `pip install markitdown`) |

Installed from the `tausik-skills` repo. Use `tausik skill install <name>` to add, `tausik skill activate <name>` to enable.

### Productivity / Wrap-up

| Skill | When |
|-------|------|
| `/daily` | Today's summary: completed tasks, commits, time |
| `/run` | Autonomous batch execution of a markdown plan |
| `/loop-task` | Autonomous task execution loop with fresh context |
| `/dispatch` | Orchestrate parallel worker agents on independent tasks |

### Analysis

| Skill | When |
|-------|------|
| `/audit` | Code-quality audit — static analysis, metrics, actionable report |
| `/security` | Security audit (OWASP Top 10, secrets scan) |
| `/optimize` | Performance optimization — bottleneck analysis |
| `/ultra` | Deep 10-point analysis for complex architectural decisions |
| `/retro` | Retrospective on recent work |
| `/presale` | Presale estimation — capacity planning + proposal |

### Integrations (external services via MCP)

| Skill | When |
|-------|------|
| `/jira` | Jira issue management (create/update/search) via MCP |
| `/bitrix24` | Bitrix24 CRM — tasks, deals, contacts via webhook API |
| `/confluence` | Confluence publishing — create/update pages |
| `/sentry` | Sentry error monitoring via MCP |

### Documentation / Extraction

| Skill | When |
|-------|------|
| `/markitdown` | Convert DOCX/PPTX/XLSX/HTML/EPUB/PDF to markdown via the markitdown CLI (requires `pip install markitdown`) |
| `/excel` | Read/analyze/generate Excel/CSV |
| `/pdf` | Read/extract/analyze PDF documents |
| `/docs` | Generate or update documentation (jsdoc/docstrings) |

## Lifecycle

```bash
.tausik/tausik skill list                    # active + vendored + available
.tausik/tausik skill repo add <url>          # register a TAUSIK-compatible repo
.tausik/tausik skill install <name>          # clone + copy + pip deps
.tausik/tausik skill activate <name>         # copy from harness/skills → .claude/skills
.tausik/tausik skill deactivate <name>       # remove from .claude/skills (keep vendored copy)
.tausik/tausik skill uninstall <name>        # remove completely
```

The official vendor repo: `https://github.com/Kibertum/tausik-skills`. Custom repos are supported — see **[Skill Adaptation Guide](skill-adaptation.md)**.

### Bulk install via bundles

`tausik skill install <name>` installs one skill at a time. For groups (integrations, data-formats, quality-pro, automation, workflow-helpers), use **bundles** instead — see **[Skill Bundles](skill-bundles.md)**:

```bash
.tausik/tausik skill bundle list                    # discover bundles
.tausik/tausik skill bundle install integrations    # install jira/bitrix24/confluence/sentry in one call
```

> **v1.4 deprecations:** `/go`, `/next`, `/diff`, `/onboard`, `/init` were removed — each duplicated built-in functionality. Migration table in **[Skill Bundles Migration](skill-bundles-migration.md)**.

## What's Next

- **[Workflow](workflow.md)** — how skills compose into a work day
- **[CLI Commands](cli.md)** — calling TAUSIK from the terminal directly
- **[MCP Tools](mcp.md)** — programmatic surface for agents
- **[Vendor Skills](vendor-skills.md)** — installing and authoring skill packages
