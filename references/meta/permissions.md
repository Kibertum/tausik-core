# Permission Strategies

## Permission File Location

```
~/.claude/settings.json           # Global defaults
.claude/settings.local.json       # Project-specific (gitignored)
```

## Permission Structure

```json
{
  "permissions": {
    "allow": [],
    "deny": [],
    "ask": [],
    "defaultMode": "ask"
  }
}
```

## Default Modes

| Mode | Behavior |
|------|----------|
| `"ask"` | Prompt for everything not in allow/deny |
| `"acceptEdits"` | Auto-approve file edits, ask for bash |
| `"full"` | Trust fully (use with caution) |

## Permission Pattern Syntax

```
Tool(command:args)
Tool(pattern:*)      # Wildcard
```

Examples:
```json
"Bash(npm install:*)"        // Any npm install
"Bash(git status:*)"         // Git status only
"Read(./.env)"               // Specific file
"Read(**/*.md)"              // Glob pattern
```

## Recommended Configuration

```json
{
  "permissions": {
    "allow": [
      "Edit",
      "Write",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(npm:*)",
      "Bash(pnpm:*)",
      "Bash(pip:*)",
      "Bash(pytest:*)",
      "Bash(ls:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(rm -r:*)",
      "Bash(sudo:*)",
      "Bash(git push --force:*)",
      "Bash(git reset --hard:*)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(~/.ssh/**)"
    ],
    "ask": [
      "Bash(git commit:*)",
      "Bash(git push:*)",
      "Bash(docker:*)",
      "Bash(rm:*)"
    ],
    "defaultMode": "acceptEdits"
  }
}
```

## Permission Categories

### Safe to Allow

```json
[
  "Edit",
  "Write",
  "Bash(git status:*)",
  "Bash(git diff:*)",
  "Bash(git log:*)",
  "Bash(npm:*)",
  "Bash(pip:*)",
  "Bash(ls:*)",
  "Bash(cat:*)"
]
```

### Always Deny

```json
[
  "Bash(rm -rf:*)",
  "Bash(rm -r:*)",
  "Bash(sudo:*)",
  "Bash(git push --force:*)",
  "Bash(git reset --hard:*)",
  "Read(./.env)",
  "Read(~/.ssh/**)",
  "Read(~/.aws/**)"
]
```

### Should Ask

```json
[
  "Bash(git commit:*)",
  "Bash(git push:*)",
  "Bash(docker:*)",
  "Bash(rm:*)"
]
```

## Best Practices

1. **Start restrictive** — Add permissions as needed
2. **Deny secrets** — Never auto-allow reading sensitive files
3. **Ask for git writes** — Review commits before they happen
4. **Use wildcards carefully** — `Bash(*)` is very permissive
5. **Gitignore local settings** — Keep `.claude/settings.local.json` out of repo
