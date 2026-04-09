# Skill Specification

Formal contract for SKILL.md files in the KAI framework.

## File Structure

Every skill is a directory `skills/{name}/` containing `SKILL.md`.

### Required Format

```markdown
---
name: skill-name
description: "Trigger description for Claude Code skill discovery."
---

# /skill-name — Human Title

Brief description. Always respond in the user's language.

## Algorithm

### 1. First Step
Instructions...

### 2. Second Step
Instructions...
```

### Frontmatter (Required)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Kebab-case slug matching directory name |
| `description` | string | Trigger phrase list for Claude Code's skill matcher |

The `description` field is critical — Claude Code uses it to decide when to invoke the skill.
Include trigger phrases: "Use when user says 'X', 'Y', 'Z'."

### Body Sections

| Section | Required | Purpose |
|---------|----------|---------|
| `# /name — Title` | Yes | H1 heading with slash command and human title |
| `## Algorithm` | Yes | Step-by-step execution instructions |
| `## Rules` | No | Constraints and invariants |
| `## Context` | No | Auto-loaded shell data (via `!` prefix) |

## Skill Categories

| Category | Skills | Bootstrap Handling |
|----------|--------|--------------------|
| Core | start, plan, task, end, checkpoint | Always copied, not selectable |
| Service | init | Always copied, excluded from interactive |
| Extension | review, test, security, docs, etc. | Selected via --smart or --interactive |
| Plugin | ui-ux-pro-max | Large skills, manual selection |

## Conventions

1. **References over inline**: Large tables and protocols → extract to `references/meta/` and link
2. **Shared patterns**: Use `skill-patterns.md` for cross-skill patterns (handoff, CLAUDE.md update, etc.)
3. **CLI reference**: Always link to `project-cli.md`, never duplicate CLI syntax
4. **Parallel batching**: Explicitly mark independent tool calls for parallel execution
5. **Token budget**: Keep SKILL.md under 300 lines; extract reference data to separate files
6. **Language**: Skills respond in the user's language (detect from conversation)

## Creating a New Skill

1. Create `skills/my-skill/SKILL.md` following the format above
2. Add to `.claude-bootstrap.json` under appropriate category:
   - `extension_skills` for standard extensions
   - `plugin_skills` for large/specialized skills
3. Run `python bootstrap/bootstrap.py` to copy to `.claude/skills/`
4. Claude Code discovers it automatically by SKILL.md presence

### Template

```markdown
---
name: my-skill
description: "Brief purpose. Use when user says 'trigger1', 'trigger2'."
---

# /my-skill — My Skill Title

One-line description. Always respond in the user's language.

**CLI Reference:** `.claude/references/project-cli.md`

## Algorithm

### 1. Gather Context
Describe what to read/search before acting.

### 2. Execute
Core logic steps.

### 3. Output
What to show the user.

## Rules
- Rule 1
- Rule 2
```
