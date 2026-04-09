**English** | [Русский](../ru/vendor-skills.md)

# Custom Skills

TAUSIK supports external skill packages from GitHub repos. Skills are cloned once, cached in `.tausik/vendor/`, and installed on demand with automatic dependency management.

## Quick Start

```bash
# 1. Add a skill repository
.tausik/tausik skill repo add https://github.com/Kibertum/tausik-skills

# 2. Install a skill (copies files + installs pip deps)
.tausik/tausik skill install jira

# 3. Restart IDE to load the new skill
```

That's it — one repo, one install, one restart.

## Skill Repo Management

### Adding repos

```bash
# TAUSIK-compatible repos (have tausik-skills.json)
.tausik/tausik skill repo add https://github.com/Kibertum/tausik-skills

# See what's available
.tausik/tausik skill repo list
```

### Removing repos

```bash
.tausik/tausik skill repo remove tausik-skills
```

### Default repos

TAUSIK ships with `Kibertum/tausik-skills` as a pre-configured default repo. Run `skill repo list` to see it.

## Installing and Uninstalling Skills

```bash
# Install: clone repo (if needed) → copy skill → install pip deps
.tausik/tausik skill install jira

# Uninstall: remove files and config entry
.tausik/tausik skill uninstall jira

# List everything: active, vendored, and available from repos
.tausik/tausik skill list
```

### MCP tools (for AI agents)

```
tausik_skill_repo_add     — add a repo
tausik_skill_repo_remove  — remove a repo
tausik_skill_repo_list    — list repos and their skills
tausik_skill_install      — install a skill
tausik_skill_uninstall    — uninstall a skill
tausik_skill_list         — list all skills (active + vendored + available)
tausik_skill_activate     — activate a vendored skill
tausik_skill_deactivate   — deactivate (unload from context)
```

## Three-Tier Skill System

Skills live at three levels — from "ready to use" to "not yet cloned":

| Tier | Location | In Agent Context? | How to Use |
|------|----------|-------------------|------------|
| **Active** | `.{ide}/skills/` | Yes — loaded every conversation | Used automatically |
| **Installed** | `.tausik/vendor/` | No — cached on disk, zero context cost | `skill activate <name>` |
| **Available** | In repo, not yet cloned | No — not downloaded | `skill repo add` + `skill install` |

**Why three tiers?** Active skills consume agent context. If you activate 50 skills, the agent has less room for your code. Keep only daily-use skills active; installed skills are one command away.

## How It Works

```
skill repo add <url>
      ↓
git clone --depth 1 → .tausik/vendor/{repo}/
      ↓
skill install <name>
      ↓
copy to .{ide}/skills/{name}/ + pip install deps
      ↓
Active (loaded into agent context)
```

### Activate / Deactivate (without reinstalling)

```bash
# Remove from context (keeps files in vendor)
.tausik/tausik skill deactivate jira

# Reload into context
.tausik/tausik skill activate jira
```

## tausik-skills.json Format

TAUSIK-compatible repos must have `tausik-skills.json` in the root:

```json
{
  "format": "tausik-skills",
  "version": 1,
  "skills": {
    "jira": {
      "path": "jira/",
      "description": "Jira issue management",
      "triggers": ["jira", "sprint", "issues"],
      "requires": ["jira-python>=3.0"]
    }
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `format` | Yes | Must be `"tausik-skills"` |
| `version` | Yes | Manifest version (`1`) |
| `skills.{name}.path` | Yes | Relative path to skill directory |
| `skills.{name}.description` | Yes | One-line description |
| `skills.{name}.triggers` | No | Keywords for agent auto-suggestions |
| `skills.{name}.requires` | No | pip packages (auto-installed into `.tausik/venv/`) |

For repos that don't follow this format, see the [Skill Adaptation Guide](skill-adaptation.md).

## Dependencies

pip dependencies listed in `requires` are automatically installed into `.tausik/venv/` during `skill install`. Your system Python is never modified.

```bash
# Example: installing a skill with deps
.tausik/tausik skill install jira
# → Copies jira/ to .claude/skills/jira/
# → pip install jira-python>=3.0 into .tausik/venv/
```

## Security

- Repos cloned via HTTPS with URL scheme validation
- Path traversal protection on skill copy
- pip dependency warning: packages from external manifests flagged for review
- No hooks auto-installed from external repos (prevents conflicts)
- Vendor scripts namespaced to prevent core overwrites

## Legacy: skills.json + bootstrap

The older mechanism using `skills.json` + `bootstrap --update-deps` still works for backward compatibility. See `skills.example.json` for the format. The new `skill repo add` + `skill install` is recommended for new projects.
