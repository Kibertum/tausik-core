**English** | [Русский](../ru/cli.md)

# TAUSIK CLI — Command Reference

All commands are invoked via the wrapper: `.tausik/tausik <command> [subcommand] [arguments]`

## Initialization

```bash
init --name <slug>             # Initialize project (creates .tausik/tausik.db)
status                         # Project overview + SENAR session duration warning
metrics                        # SENAR metrics: Throughput, Lead Time, FPSR, DER, Cycle Time, KCR
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
task add <title> [--group STORY_SLUG] [--slug SLUG] [--stack STACK] [--complexity {simple,medium,complex}] [--goal TEXT] [--role ROLE] [--defect-of PARENT_SLUG]
task quick <title> [--goal TEXT] [--role ROLE] [--stack STACK]
task next [--agent AGENT_ID]     # Pick next planning task (by score)
task list [--status STATUS] [--story STORY] [--epic EPIC] [--role ROLE] [--stack STACK]
task show <slug>               # Full info: plan, notes, decisions, defect_of
task start <slug>              # planning -> active (QG-0: requires goal + acceptance_criteria)
task done <slug> --ac-verified [--no-knowledge] [--relevant-files FILE1 FILE2 ...]
                               # QG-2: --ac-verified confirms AC verification (requires evidence in notes)
                               # --no-knowledge: explicitly confirm no knowledge to capture
task block <slug> [--reason TEXT]
task unblock <slug>            # blocked -> active
task review <slug>             # active -> review
task update <slug> [--title T] [--goal G] [--notes N] [--acceptance-criteria AC] [--scope S] [--scope-exclude S] [--stack S] [--complexity C] [--role ROLE]
task delete <slug>
task plan <slug> <step1> <step2> ...   # Set plan steps
task step <slug> <step_number>  # Mark step N as completed (1-indexed)
task log <slug> <message>      # Add timestamped note (crash-safe journal)
task move <slug> <new_story>   # Move task to another story
task claim <slug> <agent_id>   # Multi-agent: claim a task
task unclaim <slug>            # Release a task
```

**Allowed stacks:** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade

## Dead End Documentation (SENAR Rule 9.4)

```bash
dead-end <approach> <reason> [--task SLUG] [--tags T1 T2 ...]
# Documents a failed approach with reason. Saved in memory as dead_end type.
```

## Exploration (SENAR Section 5.1)

```bash
explore start <title> [--time-limit MINUTES]   # Start investigation (default: 30 min)
explore end [--summary TEXT] [--create-task]    # End (--create-task creates a task from findings)
explore current                                 # Show active exploration with elapsed time
```

## Multi-agent

```bash
team                           # Tasks grouped by agents (claimed_by)
```

## Sessions

```bash
session start                  # Start new session (returns ID)
session end [--summary TEXT]   # End active session
session extend [--minutes N]   # Extend session beyond 180 min limit (SENAR Rule 9.2)
session current                # Show active session
session list [--limit N]       # Recent sessions (default: 10)
session handoff <json_data>    # Save handoff JSON for next session
session last-handoff           # Get handoff from last session
```

## Knowledge

```bash
decide <text> [--task SLUG] [--rationale TEXT]
decisions [--limit N]          # List decisions (default: 20)

memory add <type> <title> <content> [--tags T1 T2 ...] [--task SLUG]
memory list [--type TYPE] [--limit N]
memory search <query>          # FTS5 full-text search
memory show <id>
memory delete <id>

# Graph memory (Graphiti-inspired)
memory link <source_type> <source_id> <target_type> <target_id> <relation> [--confidence 0.0-1.0] [--created-by AGENT]
memory unlink <edge_id> [--replacement EDGE_ID]  # Soft-invalidate (never deletes)
memory related <node_type> <node_id> [--hops N] [--include-invalid]
memory graph [--type {memory,decision}] [--id N] [--relation {supersedes,caused_by,relates_to,contradicts}] [--include-invalid] [--limit N]

# Aggregators (v1.2.0) — Memory Block re-injection + Dream-System-inspired consolidation
memory block [--max-decisions N] [--max-conventions N] [--max-deadends N] [--max-lines N]
memory compact [--last N]
```

**Memory types:** pattern, gotcha, convention, context, dead_end
**Graph node types:** memory, decision
**Relation types:** supersedes, caused_by, relates_to, contradicts

## Search and Navigation

```bash
roadmap [--include-done]       # Full tree epic -> story -> task
search <query> [--scope {all,tasks,memory,decisions}]
```

## Quality Gates

```bash
gates status                   # Show all quality gates and their configuration
gates list                     # List gates with enabled/disabled status
gates enable <name>            # Enable gate
gates disable <name>           # Disable gate
```

## Skills

```bash
skill list                     # List skills: active, vendored, available
skill install <name>           # Install from repo (clone + copy + deps)
skill uninstall <name>         # Remove skill completely
skill activate <name>          # Activate installed skill
skill deactivate <name>        # Deactivate skill (keep files)
skill repo add <url>           # Add TAUSIK-compatible skill repo
skill repo remove <name>       # Remove skill repo
skill repo list                # List configured repos and their skills
```

## Batch Execution

```bash
run <plan-file.md>             # Parse and display batch-run plan summary
```

Plans are markdown files with numbered tasks, goals, and file lists. Use `/run plan.md` in an interactive session to execute autonomously.

## Events (Audit Log)

```bash
events [--entity {task,epic,story}] [--id SLUG] [--limit N]
```

## Maintenance

```bash
update-claudemd [--claudemd PATH]     # Update <!-- DYNAMIC --> section in CLAUDE.md
fts optimize                          # Optimize FTS5 indexes
hud                                   # Live one-screen dashboard: task + session + gates + logs (v1.2.0)
suggest-model [complexity]            # Recommend Claude model: simple→Haiku, medium→Sonnet, complex→Opus (v1.2.0)
```

## Constants

| Concept | Values |
|---------|--------|
| Task statuses | `planning -> active -> blocked <-> active -> review -> done` |
| Slug format | `^[a-z0-9][a-z0-9-]*$` (max 64 characters) |
| Complexity -> SP | simple=1, medium=3, complex=8 |
| Memory types | pattern, gotcha, convention, context, dead_end |
| Roles | Free text (no restrictions) |
| SENAR gates | QG-0 (Context Gate on task start), QG-2 (Implementation Gate on task done) |
| Session limit | 180 min by default (configurable in config.json: session_max_minutes) |
