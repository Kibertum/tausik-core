# Skill Specification

Formal contract for SKILL.md files in the TAUSIK framework.

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

The canonical list lives in `.tausik/config.json` under `bootstrap.core_skills`
and `bootstrap.extension_skills`. As of v1.4:

| Category | Skills | Bootstrap Handling |
|----------|--------|--------------------|
| Core (11) | start, end, task, plan, checkpoint, commit, explore, review, test, ship, debug | Always copied, not selectable |
| Core (conditional) | brain | Copied when Notion is configured (`brain.enabled = true`) |
| Extension | docs (and any names added under `bootstrap.extension_skills`) | Selected via `--include-official` or `tausik skill install <name>` |
| Vendor / bundle | 20 skills under `skills-official/registry.json`, grouped into 6 bundles | Pulled per-skill or per-bundle via `tausik skill bundle install <name>` |

`init` was removed in v1.4 (replaced by `python bootstrap/bootstrap.py --init`).
The five legacy skills `/go`, `/next`, `/diff`, `/onboard`, `/init` were removed
in the same release — see `skill-bundles-migration.md`.

## Conventions

1. **References over inline**: Large tables and protocols → extract to a sibling reference file inside the skill dir and link
2. **Shared patterns**: Use `skill-patterns.md` for cross-skill patterns (handoff, CLAUDE.md update, etc.)
3. **CLI reference**: Always link to `docs/en/cli.md` (or `docs/ru/cli.md`), never duplicate CLI syntax
4. **Parallel batching**: Explicitly mark independent tool calls for parallel execution
5. **Token budget**: Keep SKILL.md under 300 lines; extract reference data to separate files
6. **Language**: Skills respond in the user's language (detect from conversation)

## Creating a New Skill

1. Create `harness/skills/my-skill/SKILL.md` following the format above
2. Add the slug to `.tausik/config.json` under `bootstrap.extension_skills`
   (or `bootstrap.core_skills` for always-deployed)
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

**CLI Reference:** [`docs/en/cli.md`](cli.md)

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
