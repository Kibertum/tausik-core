**English** | [Русский](../ru/claude-md-guide.md)

# How to Write an Effective CLAUDE.md

## Golden Rules

### 1. Keep it under 50 lines

Every token counts. A bloated CLAUDE.md = less room for real work.

### 2. Rules, not documentation

CLAUDE.md is a **reference**, not a manual.

```markdown
# BAD
## Authentication system
Our auth uses JWT tokens stored in HTTP-only cookies.
The flow works as follows: first the user submits credentials...
[200 more lines]

# GOOD
## Auth
- JWT in HTTP-only cookies
- Details: docs/auth.md
- Entry point: server/auth/
```

### 3. Document what Claude gets wrong

Add rules reactively, based on actual mistakes:

```markdown
# BAD: Pre-documenting everything
- Use tabs instead of spaces
- Variable names should be descriptive

# GOOD: Rules drawn from real mistakes
- NEVER use inline styles — use CSS classes from assets/css/
- API routes MUST be validated through Zod before processing
```

### 4. Explain the why, suggest the alternative

```markdown
# BAD
- Never use any

# GOOD
- Never use `any` — use `unknown` and narrow the type, or define the right type
  Why: `any` breaks type safety and hides bugs
```

### 5. Link, don't copy

Point to documentation; don't copy it.

```markdown
# BAD: Full API documentation in CLAUDE.md

# GOOD
## API Development
- Read: docs/api-patterns.md when creating endpoints
- Read: docs/database.md when changing the schema
```

## Recommended Structure

```markdown
# {Project Name}

## Vision
{One sentence describing the project's purpose}

## Stack
- Frontend: {framework} | Entry point: {path}
- Backend: {framework} | Entry point: {path}
- Database: {type}

## Critical Rules
- {Rule 1 with rationale}
- {Rule 2 with rationale}
- Git: Ask before commit/push

## Patterns
{Example of a mandatory pattern}

## Commands
{dev command}
{test command}
{build command}

## Context
Read: .claude-project/context.md
```

## What NOT to Include

- Generic advice ("write clean code")
- Default Claude behaviour ("handle errors properly")
- Entire documentation pages
- Contradictory rules
- More than 50 lines

## What to Include

- Project-specific constraints
- Critical patterns that differ from defaults
- Entry points and key files
- Dev/test/build commands
- A pointer to the context file

## Maintenance

1. **Add rules when Claude makes mistakes**
2. **Remove rules that no longer apply**
3. **Review monthly** for cleanup

## Negative — Common Anti-Patterns

- Treating CLAUDE.md as a wiki — pile of architecture, history, and feature docs.
- Re-stating Claude's defaults — wastes tokens and adds noise.
- Vague rules ("be careful with auth") — Claude can't act on those.
- No examples of good vs bad — rules without examples drift fast.
- Never updating it — a stale CLAUDE.md is worse than none.

## See also

- [SENAR Compliance Matrix](senar-compliance-matrix.md) — what TAUSIK enforces around tasks/AC
- [Workflow](workflow.md) — how CLAUDE.md fits into the day
- [Configuration](configuration.md) — where CLAUDE.md ties into runtime behaviour
