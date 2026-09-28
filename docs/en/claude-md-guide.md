**English** | [Русский](../ru/claude-md-guide.md)

# How to Write an Effective CLAUDE.md

<!-- doc-map: reader=maintainer; zone=ide-and-skills -->

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

## The ceiling is a budget, not a wall

TAUSIK's own CLAUDE.md caps its static portion at 4096 bytes: the file is loaded into
context every turn, so a kilobyte above the cap is roughly 250 tokens per turn -- about 25K
across a hundred-turn session. `tests/test_claude_md_size.py` holds the cap.

**MEASURED, session #277: 13 bytes were free.** No new pointer fit, and the ceiling had
silently become a ban on any addition -- the worst kind of limit, because it does not refuse
anything, it just leaves no room, and the next author finds out from a failing test.

The admission rule that gave the headroom back: **a line earns a place in CLAUDE.md only if
the agent would do the wrong thing without it.** Reference prose does not change behaviour --
`--help` and error messages carry it, and an agent reads those at the moment of use. The one
exception is a declaration a standard requires where readers look: the SENAR conformance
claim has to sit there, and its own test keeps it.

Removed under that rule (246 bytes; headroom 13 -> 254):

| What | Why it had no place |
|---|---|
| the stack line | every clause of it is stated where it is used |
| the memory type list | a closed enum the CLI validates and names in its own error |
| the five-command crib | four lines repeated a constraint above; the fifth is in the CLI reference |
| a second address for the contract | one address, named once; the full description is under Reference |

No hard constraint was dropped: the list of bold rules before and after is the same,
nineteen for nineteen.

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

## Compaction contract
{What must survive a context compaction, by name: the active task and slug,
the declared scope and verify receipt, this session's measurements, retired
rules, owner prohibitions, open forks. TAUSIK's bootstrap template ships one.}

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
