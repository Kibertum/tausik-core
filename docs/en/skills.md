**English** | [Русский](../ru/skills.md)

# Skills (v1.4)

<!-- doc-map: reader=user; zone=core-surface -->

Skills are intent-based instructions that define agent behaviour. You don't memorize names or syntax — you write what you want, and the agent picks the right skill. Slash-prefix (`/plan`, `/ship`) explicitly invokes one.

After bootstrap, **13 core skills** ship with TAUSIK from `harness/skills/`. The official store contains only `docs`, `excel`, and `pdf`. Install one only when needed with `tausik skill install <name>` so unused instructions add no prompt cost. **Map of repo skills:** [Skill ecosystem (one page)](skill-ecosystem.md).

> **Token rule since v1.4.** Before v1.4, bootstrap exposed the whole catalog and spent about 1,520 tokens on its reminder list. The default now exposes only core skills. `--include-official` remains a local-checkout compatibility switch, but per-skill installation is the supported economical path.

**Multi-host variants:** skills can ship optional **`variants/<profile>.md`** overlays — see [Skill profiles & variants](skill-profiles.md).

## Core Skills (13)

These are always available after bootstrap — the workflow primitives every TAUSIK project needs.

### Workflow

| Skill | When |
|-------|------|
| `/start` | Begin a work session — loads handoff, status, memory block |
| `/end` | Wrap up the session — saves metrics + handoff |
| `/checkpoint` | Save context without ending the session (when the checkpoint signal says so) |
| `/plan` | Plan a task from a free-form description (interview phase + AC) |
| `/task` | Work on an existing task with QG-0/QG-2 enforcement |
| `/ship` | Wrap up a task: review + test + gates + commit |
| `/commit` | Create a standardized git commit |

### Knowledge

| Skill | When |
|-------|------|
| `/explore` | Time-boxed investigation (default 30 min) before committing to an approach |
| `/interview` | Socratic Q&A — at most 3 questions to pin down requirements |
| `/reason` | Record a structured reasoning trace (intent→premise→action→verification) on a task — see [Reasoning Trace](reasoning-trace.md) |

### Quality

| Skill | When |
|-------|------|
| `/review` | Code review against 28-point SENAR checklist (5 parallel agents, iterative) |
| `/test` | Run or write tests, track coverage |
| `/debug` | Reproduce → isolate root cause → fix |

## Official / Vendor Skills

The official catalog is a separate repository and is not part of the core release. It deliberately contains only three neutral document skills: `docs`, `excel`, and `pdf`. Integrations belong in MCP servers or third-party repositories; company-specific roles do not belong in TAUSIK.

- Install one capability with `tausik skill install <name>` and activate it only when needed.
- Use `skill bundle` only for a third-party repository that declares one and only when every member is required.
- Avoid `--include-official` in normal projects. It exposes every entry found in a local catalog checkout and increases the repeated prompt prefix.
- The official repository does not publish a bundle.

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

### Spec conformance (agentskills.io)

The SKILL.md format is now the cross-vendor **agentskills.io** canon. A built-in
gate (`skill_spec_conformance`) fails a close/commit when a changed `SKILL.md`
breaks the machine-checkable rules: `name` is 1–64 chars of `a-z0-9` with single
hyphens (no leading/trailing/doubled hyphen) and **must equal its directory
name**; `description` is 1–1024 chars. The gate is inert unless a `SKILL.md` is
among the changed files. Local scaffolds whose directory starts with `_` or `.`
(e.g. `_profile-demo`) are not published skills and are skipped.

> The agentskills.io spec is **not versioned** and contains **no security
> provisions** — nothing about trust, sandboxing, or tool permissions. This gate
> is a hygiene check that keeps progressive disclosure working; never treat
> conformance as a trust signal.

### Bulk install via bundles

`tausik skill install <name>` installs one skill at a time. A repository may publish optional **bundles**; inspect them before bulk installation — see **[Skill Bundles](skill-bundles.md)**:

```bash
.tausik/tausik skill bundle list                    # discover bundles
.tausik/tausik skill bundle install <name>           # install every member of that bundle
```

## What's Next

- **[Workflow](workflow.md)** — how skills compose into a work day
- **[CLI Commands](cli.md)** — calling TAUSIK from the terminal directly
- **[MCP Tools](mcp.md)** — programmatic surface for agents
- **[Vendor Skills](vendor-skills.md)** — installing and authoring skill packages
