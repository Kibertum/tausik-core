**English** | [Русский](../ru/skills.md)

# Skills

Skills are instructions that define the AI agent's behavior. You don't need
to memorize skill names or syntax — just write what you want to do,
and the agent will pick the appropriate skill.

## Core Skills

### /plan — Task Planning

**When:** You describe a task in free form.

```
fix the authorization bug
add an "Export to PDF" button
refactor the payment module
```

The agent starts with an **interview phase** — asking 3+ clarifying questions about expected behavior, edge cases, and constraints. Then it estimates complexity, creates a task with goal and acceptance criteria, and breaks it into steps. Skip the interview with `--skip-interview` or by providing a detailed spec upfront.

### /ship — Completion

**When:** The work is done and everything needs to be wrapped up.

```
done, ship it
close and commit
ship it
```

The agent will review the code, run tests, verify that acceptance criteria are met,
close the task, and offer to commit. After commit, it checks for structural changes and suggests updating project documentation. All in one operation.

### /start — Session Start

**When:** You sit down to work (usually at the start of the day).

```
start working
start
```

The agent will open a session, show what was done last time,
which tasks are waiting, and suggest what to work on.

### /end — Session End

**When:** You're done working.

```
that's all for today
finish
```

The agent will save metrics, record a handoff for the next session,
capture unresolved questions.

## Analysis and Quality

### /review — Code Review

```
review my code
review src/auth/
```

Checks against a 28-point SENAR checklist: scope creep, phantom imports,
hardcoded values, security, tests, edge cases, backward compatibility.

### /test — Tests

```
run tests
write tests for the auth module
```

Runs existing tests or writes new ones. Tracks coverage.

### /explore — Exploration

```
figure out how their API works
explore caching options
```

Time-limited exploration (30 minutes by default) without writing production code.
Results are recorded, and a task can be created from the findings.

### /interview — Socratic Q&A (v1.2)

```
interview me about this task
уточни, что я хочу сделать
```

Asks **at most 3** clarifying questions before a complex task (prompt-master principle). Picks the questions that actually change the implementation plan — drops the rest. Stops as soon as enough context is collected. `/plan` and `/go` invoke this automatically for complex/unclear requests.

## Auxiliary

### /daily — Daily Summary

```
what did I do today?
summary
```

Shows completed tasks, commits, and metrics for the day.

### /next — Next Task

```
what should I do next?
next task
```

Picks the best task to work on, shows context and dead ends.

### /commit — Commit

```
commit
```

Creates a commit with gates and scope checks.

### /checkpoint — Context Save

```
checkpoint
```

Saves the current state without ending the session. Useful during long work sessions.

### /diff — Changes

```
what changed?
show diff
```

Analyzes git diff with risk highlighting.

## Specialized Skills

| Skill | When to Use |
|-------|-------------|
| `/debug` | Systematic debugging with root cause analysis |
| `/security` | Security audit per OWASP Top 10 |
| `/retro` | Retrospective: what worked, what didn't |
| `/ultra` | Deep analysis of a complex architectural decision |
| `/onboard` | Quick onboarding to an unfamiliar codebase |
| `/skill-test` | Auto-generate and validate test scenarios for any skill |

## Extending with Custom Skills

Everything above is **built-in** — these 34 skills ship with TAUSIK and are always available after bootstrap.

Beyond the built-in skills, TAUSIK has a **skill install system** for adding skill packages from GitHub. These extend the agent with new capabilities: Jira/Bitrix24 integration, Confluence publishing, Sentry monitoring, presale estimation, and more.

```bash
# Add a TAUSIK-compatible skill repository
.tausik/tausik skill repo add https://github.com/Kibertum/tausik-skills

# Install a skill (copies files + installs pip deps)
.tausik/tausik skill install jira

# List all skills: active, installed, available
.tausik/tausik skill list

# Deactivate (removes from agent context, keeps files)
.tausik/tausik skill deactivate jira
```

The official skill repo (`Kibertum/tausik-skills`) contains 22 additional skills ready to install.

See **[Custom Skills Guide](vendor-skills.md)** for installation, and **[Skill Adaptation Guide](skill-adaptation.md)** for creating your own skill packages.

## What's Next

- **[Workflow](workflow.md)** — how skills fit into a work day
- **[CLI Commands](cli.md)** — calling TAUSIK from the terminal directly
- **[MCP Tools](mcp.md)** — technical documentation for agent developers
