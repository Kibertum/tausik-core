**English** | [Русский](../ru/skills.md)

# Skills (v1.3)

Skills are intent-based instructions that define agent behaviour. You don't memorize names or syntax — you write what you want, and the agent picks the right skill. Slash-prefix (`/plan`, `/ship`) explicitly invokes one.

After bootstrap, **13 core skills** ship with TAUSIK from `agents/skills/`. Additional **vendor / official skills** (25+) are available via `tausik skill install <name>` from the `tausik-skills` repo (or the bundled `skills-official/` directory).

## Core Skills (13)

These are always available after bootstrap — the workflow primitives every TAUSIK project needs.

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
| `/brain` | Query/store cross-project knowledge in the Shared Brain (Notion + local mirror) — v1.3 headline feature |
| `/explore` | Time-boxed investigation (default 30 min) before committing to an approach |
| `/interview` | Socratic Q&A — at most 3 questions to pin down requirements |

### Quality

| Skill | When |
|-------|------|
| `/review` | Code review against 28-point SENAR checklist (5 parallel agents, iterative) |
| `/test` | Run or write tests, track coverage |
| `/debug` | Reproduce → isolate root cause → fix |

## Vendor / Official Skills (25+)

Not auto-deployed — install on demand. Lives in `skills-official/` (bundled) and the `tausik-skills` repo (external). Use `tausik skill install <name>` to add, `tausik skill activate <name>` to enable.

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
| `/go` | One-phrase quick-start: phrase → task created → started |
| `/next` | Pick the best next task |
| `/daily` | Today's summary: completed tasks, commits, time |
| `/diff` | Analyze git diff with risk highlighting |
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
| `/onboard` | Project onboarding: structure, conventions, active work |
| `/retro` | Retrospective on recent work |
| `/presale` | Presale estimation — capacity planning + proposal |
| `/init` | Initialize a new CLAUDE.md from a fresh codebase |

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
.tausik/tausik skill activate <name>         # copy from agents/skills → .claude/skills
.tausik/tausik skill deactivate <name>       # remove from .claude/skills (keep vendored copy)
.tausik/tausik skill uninstall <name>        # remove completely
```

The official vendor repo: `https://github.com/Kibertum/tausik-skills`. Custom repos are supported — see **[Skill Adaptation Guide](skill-adaptation.md)**.

## What's Next

- **[Workflow](workflow.md)** — how skills compose into a work day
- **[CLI Commands](cli.md)** — calling TAUSIK from the terminal directly
- **[MCP Tools](mcp.md)** — programmatic surface for agents
- **[Vendor Skills](vendor-skills.md)** — installing and authoring skill packages
