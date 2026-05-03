**English** | [Русский](../ru/skill-adaptation.md)

# Adapting Skills for TAUSIK

This guide explains how to make any skill repository compatible with TAUSIK. Whether you're adapting a Claude-native plugin, a Cursor skill, or building from scratch — follow these steps to create a TAUSIK-compatible skill repo.

## Why Adapt?

TAUSIK provides:
- **One-command install**: `tausik skill install <name>`
- **Cross-IDE support**: same skill works in Claude Code, Cursor, Windsurf, Codex
- **Dependency management**: pip packages auto-installed into isolated `.tausik/venv/`
- **Activate/deactivate**: load only the skills you need — zero context overhead for inactive skills
- **Centralized catalog**: `tausik skill list` shows all available skills

Incompatible repos get a clear error:

```
Repository 'my-repo' is not TAUSIK-compatible (tausik-skills.json not found).
See docs/en/skill-adaptation.md for how to adapt a skill repo.
```

## Quick Start

1. Fork the skill repo
2. Add `tausik-skills.json` to the root
3. Ensure each skill has `SKILL.md` with frontmatter
4. Test with `tausik skill repo add <your-fork-url>`

## Repository Structure

A TAUSIK-compatible skill repo looks like this:

```
my-skills/
├── tausik-skills.json          # REQUIRED — manifest (see spec below)
├── jira/
│   ├── SKILL.md                # REQUIRED — skill instructions
│   ├── references/             # optional — additional docs
│   │   └── api.md
│   ├── scripts/                # optional — helper scripts
│   │   └── create_issue.py
│   ├── data/                   # optional — CSV, JSON data files
│   ├── templates/              # optional — code templates
│   └── requirements.txt        # optional — pip deps (alternative to manifest "requires")
├── bitrix24/
│   ├── SKILL.md
│   └── ...
└── seo/
    ├── SKILL.md
    └── ...
```

## tausik-skills.json Specification

This is the manifest file that makes a repo TAUSIK-compatible. Place it in the repository root.

```json
{
  "format": "tausik-skills",
  "version": 1,
  "skills": {
    "jira": {
      "path": "jira/",
      "description": "Jira issue management — create, update, search issues",
      "triggers": ["jira", "sprint", "issues", "backlog"],
      "requires": ["jira-python>=3.0"]
    },
    "seo-audit": {
      "path": "seo/",
      "description": "SEO analysis and site audit",
      "triggers": ["SEO", "site audit", "meta tags"],
      "requires": []
    }
  }
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `format` | yes | Must be `"tausik-skills"` |
| `version` | yes | Manifest version, currently `1` |
| `skills` | yes | Dictionary of skill definitions |

### Skill Entry Fields

| Field | Required | Description |
|-------|----------|-------------|
| `path` | yes | Relative path to skill directory (must end with `/`) |
| `description` | yes | One-line description (shown in `skill list`) |
| `triggers` | no | Keywords that suggest this skill (for agent auto-suggestions) |
| `requires` | no | pip packages to install (e.g. `["httpx>=0.27", "jira-python"]`) |

## SKILL.md Format

Every skill needs a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: jira
description: "Jira issue management — create, update, search issues via REST API"
---

# /jira — Jira Integration

## Algorithm

1. Check if JIRA_URL and JIRA_TOKEN are set
2. ...

## Examples

...
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Skill identifier (kebab-case, e.g. `seo-audit`) |
| `description` | yes | One-line summary |

The body of SKILL.md contains the instructions the AI agent will follow. Write it in English for best agent comprehension across all AI models.

## Adapting Scripts

Skills can include helper scripts in `scripts/` directory.

### Python Scripts

```
my-skill/
  scripts/
    fetch_data.py
    process.py
```

**Important for cross-IDE compatibility:**
- Use `#!/usr/bin/env python3` shebang
- Keep scripts self-contained — import only from stdlib or packages listed in `requires`
- Don't assume `.claude/` paths — use relative paths from the script location
- Prefer Python over Bash for cross-platform compatibility (Windows support)

### Bash Scripts

Bash scripts work on macOS/Linux but **not natively on Windows**. If your skill targets all platforms:
- Provide Python alternatives, or
- Document that the skill requires WSL/Git Bash on Windows

## Adapting Hooks

Claude Code hooks are **IDE-specific** and are **not installed automatically** by TAUSIK.

If the source repo contains hooks (e.g. security-guardian):
- **Do not** include them in the skill directory
- Instead, document them in SKILL.md under a "Hooks" section
- Users can install hooks manually by copying to their `.claude/hooks/` directory

**Why?** TAUSIK has its own hooks (task_gate, bash_firewall, etc.). Foreign hooks can conflict with these, causing blocked operations or false positives.

### If You Want to Provide Hooks

Create a separate `hooks/` directory at the repo root (not inside any skill) and document installation:

```markdown
## Optional Hooks

This repo includes optional Claude Code hooks in `hooks/`.
To install manually:

1. Copy `hooks/my-hook/` to your project's `.claude/hooks/`
2. Add hook config to `.claude/settings.json`
3. Test that it doesn't conflict with existing hooks
```

## Adapting MCP Servers

If the source skill has its own MCP server:

1. Place server code in the skill's `scripts/` or a `mcp/` subdirectory
2. Document the server setup in SKILL.md
3. Add any pip dependencies to `requires` in the manifest
4. Users will need to manually add the MCP server to their `.mcp.json`

**Example SKILL.md section:**

```markdown
## MCP Server Setup

This skill includes an MCP server for real-time data access.
After installing, add to your `.mcp.json`:

\```json
{
  "mcpServers": {
    "my-skill-mcp": {
      "command": ".tausik/venv/bin/python",
      "args": [".claude/skills/my-skill/mcp/server.py"]
    }
  }
}
\```
```

## Handling Dependencies

### pip Packages

List dependencies in the `requires` field of `tausik-skills.json`:

```json
{
  "requires": ["httpx>=0.27", "beautifulsoup4>=4.12"]
}
```

TAUSIK installs these into `.tausik/venv/` automatically during `skill install`. The user's system Python is never modified.

### npm / Other Package Managers

TAUSIK currently only manages pip dependencies. For npm or other package managers:
- Document the requirement in SKILL.md
- Provide a setup script in `scripts/setup.sh` or `scripts/setup.py`

### Environment Variables

If the skill requires API keys or configuration:
- Include a `config/.env.example` file showing required variables
- Document the setup in SKILL.md
- **Never** include actual credentials in the repo

## Adapting Data Files

Skills can include data files (CSV, JSON, etc.) in `data/` or `templates/` directories:

```
my-skill/
  data/
    styles.csv
    palettes.json
  templates/
    component.tsx.template
```

These are copied as-is during installation. Reference them in SKILL.md with relative paths.

## Adaptation Examples

### Example 1: Claude-Native Plugin (ui-ux-pro-max)

**Source structure:**
```
.claude/skills/design/SKILL.md
.claude/skills/ui-styling/SKILL.md
.claude-plugin/plugin.json
```

**Adapted structure:**
```
tausik-skills.json
design/SKILL.md
ui-styling/SKILL.md
```

**Steps:**
1. Move skills from `.claude/skills/` to root level
2. Create `tausik-skills.json` listing each skill
3. Remove `.claude-plugin/` (TAUSIK-specific, not needed)
4. Remove any `CLAUDE.md` (TAUSIK generates its own)

### Example 2: Plugin Monorepo (polyakov-claude-skills)

**Source structure:**
```
plugins/jira/skills/jira/SKILL.md
plugins/seo/skills/seo/SKILL.md
plugins/telegram/.claude-plugin/plugin.json
```

**Adapted structure:**
```
tausik-skills.json
jira/SKILL.md
seo/SKILL.md
telegram/SKILL.md
```

**Steps:**
1. Flatten: copy each `plugins/{name}/skills/{name}/` to `{name}/`
2. Include `scripts/`, `references/`, `data/` from each plugin
3. Create `tausik-skills.json` with all skills listed
4. Skip `hooks/` and `.claude-plugin/` directories
5. Add pip dependencies from each plugin to `requires`

### Example 3: Simple Single Skill

**Source:**
```
SKILL.md
scripts/run.py
```

**Adapted:**
```
tausik-skills.json
my-skill/
  SKILL.md
  scripts/run.py
```

Wrap the skill in a named directory and create the manifest.

## Testing Your Adapted Repo

```bash
# 1. Push your fork to GitHub
git push origin main

# 2. In any TAUSIK project, add the repo
.tausik/tausik skill repo add https://github.com/you/my-adapted-skills

# 3. Verify it was recognized
.tausik/tausik skill repo list

# 4. Install a skill
.tausik/tausik skill install my-skill

# 5. Check it appears
.tausik/tausik skill list

# 6. Activate and test in your IDE
# Restart IDE to load the new skill
```

## Checklist

- [ ] `tausik-skills.json` exists in repo root with `"format": "tausik-skills"`
- [ ] Each skill has its own directory with `SKILL.md`
- [ ] `SKILL.md` has YAML frontmatter (`name`, `description`)
- [ ] `SKILL.md` body is in English (best agent comprehension)
- [ ] Scripts use `#!/usr/bin/env python3` shebang
- [ ] pip dependencies listed in `requires` array
- [ ] No hooks in skill directories (document separately)
- [ ] No `.claude-plugin/`, `CLAUDE.md`, or IDE-specific files in skill dirs
- [ ] API keys documented in `.env.example`, not hardcoded
- [ ] Tested with `tausik skill repo add` + `tausik skill install`
