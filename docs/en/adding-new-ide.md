**English** | [Русский](../ru/adding-new-ide.md)

# Adding a New IDE to TAUSIK

TAUSIK supports multiple IDEs through the abstraction in `scripts/ide_utils.py`.

## Steps for Adding a New IDE

### 1. Register IDE in the Registry

Add an entry to `IDE_REGISTRY` in `scripts/ide_utils.py`:

```python
IDE_REGISTRY["myide"] = {
    "config_dir": ".myide",        # IDE configuration directory
    "rules_file": ".myiderules",   # agent rules file
    "skills_subdir": "skills",     # skills subdirectory
}
```

### 2. Add a Rules Generator

In `bootstrap/bootstrap_generate.py` add a function:

```python
def generate_myiderules(project_dir, project_name, stacks):
    # Generate .myiderules
    ...
```

And register it in `generate_ide_rules()`.

### 3. (Optional) Add Override Files

If the IDE requires specific rules, create:
```
agents/overrides/myide/rules.md
```

### 4. Add Auto-Detection

In `detect_ide()` in `ide_utils.py` add an env var or directory check:

```python
if os.environ.get("MYIDE_DIR"):
    return "myide"
```

### 5. Add Tests

In `tests/test_ide_utils.py` add tests for the new IDE.

## Currently Supported IDEs

| IDE | Config dir | Rules file | Hooks | Auto-detect |
|-----|-----------|------------|-------|-------------|
| Claude Code | `.claude` | `CLAUDE.md` | 4 hooks | default |
| Cursor | `.cursor` | `.cursorrules` | — | `CURSOR_DIR` env |
| Qwen Code | `.qwen` | `QWEN.md` | 4 hooks | `--ide qwen` |
| Windsurf | `.windsurf` | `.windsurfrules` | — | `WINDSURF_DIR` env |
| Codex/OpenCode | `.codex` | `AGENTS.md` | — | — |

## How It Works

```
agents/
├── skills/          # 13 core skills (auto-deployed) + 25 vendor (on demand)
├── roles/           # roles (all IDEs)
├── stacks/          # stacks (all IDEs)
├── overrides/       # IDE-specific override files
│   ├── claude/
│   ├── cursor/
│   └── qwen/
├── claude/mcp/      # MCP servers for Claude Code
├── cursor/mcp/      # MCP servers for Cursor
└── qwen/ → claude/  # Qwen Code (falls back to Claude MCP)
```

Bootstrap lookup chain: `agents/skills/` → `agents/{ide}/skills/` → `agents/claude/skills/`
