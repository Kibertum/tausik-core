**English** | [Русский](../ru/cli.md)

# TAUSIK CLI — Command Reference (v1.3)

All commands are invoked via the wrapper: `.tausik/tausik <command> [subcommand] [arguments]`.
On Windows the wrapper is `.tausik/tausik.cmd`. The same surface is also available via MCP (`tausik_*` tools); see `mcp.md`.

## Initialization

```bash
init --name <slug>             # Initialize project (creates .tausik/tausik.db)
status                         # Project overview + SENAR session duration warning (active vs wall)
metrics                        # SENAR metrics: Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task
metrics record-session         # Persist LLM usage (tokens/cost/tool/model) for current or explicit session
doctor                         # Health check: venv + DB + MCP + skills + drift
```

## Hierarchy

```bash
epic add <slug> <title> [--description TEXT]
epic list
epic done <slug>
epic delete <slug>             # CASCADE: deletes all stories + tasks

story add <epic_slug> <slug> <title> [--description TEXT]
story list [--epic EPIC_SLUG]
story done <slug>
story delete <slug>            # CASCADE: deletes all tasks
```

## Tasks

```bash
task add <title> [--story STORY_SLUG] [--slug SLUG] [--stack STACK]
                 [--complexity {simple,medium,complex}] [--goal TEXT] [--role ROLE]
                 [--defect-of PARENT_SLUG]
                 [--call-budget N] [--tier {trivial,light,moderate,substantial,deep}]
task quick <title> [--goal TEXT] [--role ROLE] [--stack STACK]
task next [--agent AGENT_ID]    # Pick next planning task (by score)
task list [--status STATUS] [--story STORY] [--epic EPIC] [--role ROLE] [--stack STACK] [--limit N]
task show <slug>                # Full info: plan, notes, decisions, defect_of, AC
task start <slug> [--force]     # planning -> active (QG-0: requires goal + AC + negative scenario)
                                # --force bypasses session capacity gate (audit event + note)
task done <slug> --ac-verified [--no-knowledge] [--relevant-files FILE1 FILE2 ...] [--evidence "..."]
                                # QG-2: --ac-verified confirms AC verification (requires evidence in notes
                                #       OR --evidence inline). Runs scoped pytest gate (basename match
                                #       on tests/test_<file>.py for each relevant file). Verify cache
                                #       (10 min TTL) skips re-runs with same files_hash. There is NO --force.
task block <slug> [--reason TEXT]
task unblock <slug>             # blocked -> active
task review <slug>              # active -> review
task update <slug> [--title T] [--goal G] [--notes N] [--acceptance-criteria AC]
                  [--scope S] [--scope-exclude S] [--stack S] [--complexity C] [--role ROLE]
                  [--call-budget N] [--tier TIER]
task delete <slug>
task plan <slug> <step1> <step2> ...   # Set plan steps
task step <slug> <step_number>  # Mark step N as completed (1-indexed)
task log <slug> <message>       # Append timestamped note (crash-safe journal)
task logs <slug> [--phase PHASE] # Read structured log entries (planning/implementation/review/testing/done)
task move <slug> <new_story>    # Move task to another story
task claim <slug> <agent_id>    # Multi-agent: claim a task
task unclaim <slug>             # Release a task
```

**Allowed stacks (DEFAULT_STACKS, 25):** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker. Custom stacks are added via `.tausik/config.json` → `custom_stacks`.

**Tier ↔ call_budget map:** trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400. Budgets >400 are accepted; tier label caps at `deep`.

## Verification

```bash
verify [--task SLUG] [--scope {lightweight,standard,high,critical,manual}]
                                # Run scoped quality gates ad-hoc; records hit in verify cache
```

## Quality Gates

```bash
gates status                    # Show all quality gates and their configuration
gates list                      # List gates with enabled/disabled status
gates enable <name>             # Enable gate
gates disable <name>            # Disable gate
```

## Stacks

```bash
stack info <stack>              # Show resolved stack: gates per language + user override info
stack list                      # List built-in + custom stacks
stack export <stack>            # Print resolved stack declaration as JSON
stack diff <stack>              # Diff between built-in and user override
stack reset <stack>             # Remove user override at .tausik/stacks/<stack>/
stack lint                      # Validate user-override stack.json files against schema
stack scaffold <name>           # Create .tausik/stacks/<name>/{stack.json,guide.md} skeleton
```

## Roles

```bash
role list
role show <slug>
role create <slug> <title> [--description TEXT] [--extends BASE_ROLE]
role update <slug> [--title T] [--description D]
role delete <slug>
role seed                       # Bootstrap role rows from agents/roles/*.md and existing task usage
```

Role storage is hybrid: SQLite metadata + `agents/roles/{role}.md` profile markdown. Roles remain free-text on tasks (`--role developer/architect/qa/...`).

## Sessions

```bash
session start                   # Start new session (returns ID)
session end [--summary TEXT]    # End active session
session current                 # Show active session
session list [--limit N]        # Recent sessions (default: 10)
session handoff <json_data>     # Save handoff JSON for next session
session last-handoff            # Get handoff from last session
session extend [--minutes N]    # Extend session beyond 180-min active limit (SENAR Rule 9.2)
session recompute               # Retro: compare wall-clock vs active (gap-based) minutes for past sessions
```

Session limit is 180 min **active** time (gap-based, paused after 10 min idle). Threshold is configurable via `.tausik/config.json` → `session_idle_threshold_minutes`. See `session-active-time.md`.
On `session end`, TAUSIK also performs a best-effort usage capture via `scripts/hooks/session_metrics.py --auto --record` (supports both Claude and Cursor transcript roots).

## Knowledge

```bash
decide <text> [--task SLUG] [--rationale TEXT]
decisions [--limit N]           # List decisions (default: 20)

memory add <type> <title> <content> [--tags T1 T2 ...] [--task SLUG]
memory list [--type TYPE] [--limit N]
memory search <query>           # FTS5 full-text search
memory show <id>
memory delete <id>

# Graph memory (Graphiti-inspired)
memory link <source_type> <source_id> <target_type> <target_id> <relation>
            [--confidence 0.0-1.0] [--created-by AGENT]
memory unlink <edge_id> [--replacement EDGE_ID]   # Soft-invalidate (never deletes)
memory related <node_type> <node_id> [--hops N] [--include-invalid]
memory graph [--type {memory,decision}] [--id N]
             [--relation {supersedes,caused_by,relates_to,contradicts}]
             [--include-invalid] [--limit N]

# Aggregators
memory block [--max-decisions N] [--max-conventions N] [--max-deadends N] [--max-lines N]
memory compact [--last N]
```

**Memory types:** pattern, gotcha, convention, context, dead_end
**Graph node types:** memory, decision
**Relation types:** supersedes, caused_by, relates_to, contradicts

## Dead End Documentation (SENAR Rule 9.4)

```bash
dead-end <approach> <reason> [--task SLUG] [--tags T1 T2 ...]
# Documents a failed approach with reason. Saved as memory type dead_end.
```

## Exploration (SENAR Section 5.1)

```bash
explore start <title> [--time-limit MINUTES]    # Start investigation (default: 30 min)
explore end [--summary TEXT] [--create-task]    # End (--create-task creates a task from findings)
explore current                                 # Show active exploration with elapsed time
```

## Periodic Audit (SENAR Rule 9.5)

```bash
audit check                     # Show whether periodic audit is overdue
audit mark                      # Mark audit as completed
```

## Multi-agent

```bash
team                            # Tasks grouped by agents (claimed_by)
```

## Skills

```bash
skill list                      # List skills: active, vendored, available
skill install <name>            # Install from repo (clone + copy + deps)
skill uninstall <name>          # Remove skill completely
skill activate <name>           # Activate installed skill
skill deactivate <name>         # Deactivate skill (keep files)
skill repo add <url>            # Add TAUSIK-compatible skill repo
skill repo remove <name>        # Remove skill repo
skill repo list                 # List configured repos and their skills
```

## Shared Brain (cross-project)

```bash
brain init                      # Initialize brain: 4 Notion DBs + config
brain status                    # Mirror freshness, sync state, registered projects
brain move <source_id> --to-brain --kind {decision,pattern,gotcha} [--keep-source]
brain move <notion_page_id> --to-local --category {decisions,patterns,gotchas,web_cache} [--force]
```

## Search and Navigation

```bash
roadmap [--include-done]        # Full tree epic -> story -> task
search <query> [--scope {all,tasks,memory,decisions}]
```

## Batch Execution

```bash
run <plan-file.md>              # Parse and display batch-run plan summary
```

Plans are markdown files with numbered tasks, goals, and file lists. Use `/run plan.md` in an interactive session to execute autonomously.

## Document Extraction

```bash
doc extract <path>              # Convert DOCX/PPTX/XLSX/HTML/EPUB/PDF to markdown via markitdown
```

Opt-in: requires `markitdown` and Python ≥3.11. See `docs/en/markitdown-integration.md`.

## Events (Audit Log)

```bash
events [--entity {task,epic,story}] [--id SLUG] [--limit N]
```

## Maintenance

```bash
update-claudemd [--claudemd PATH]     # Update <!-- DYNAMIC --> section in CLAUDE.md
fts optimize                          # Optimize FTS5 indexes
hud                                   # Live one-screen dashboard: task + session + gates + logs
suggest-model [complexity]            # Recommend Claude model: simple→Haiku, medium→Sonnet, complex→Opus
```

## Constants

| Concept | Values |
|---------|--------|
| Task statuses | `planning -> active -> blocked <-> active -> review -> done` |
| Slug format | `^[a-z0-9][a-z0-9-]*$` (max 64 characters) |
| Complexity → SP | simple=1, medium=3, complex=8 |
| Tiers (call calls) | trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400 |
| Memory types | pattern, gotcha, convention, context, dead_end |
| Roles | Free text (no enum); registry under `agents/roles/{slug}.md` |
| SENAR gates | QG-0 (Context Gate on `task start`), QG-2 (Implementation Gate on `task done`) |
| Session limit | 180 min **active** by default (configurable: `session_max_minutes`, idle threshold: `session_idle_threshold_minutes`) |
