**English** | [Русский](/ru/docs/adding-new-ide)

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

And wire it into the dispatch block in `bootstrap/bootstrap.py` (search for the `if ide == "claude"` / `elif ide == "cursor"` chain, around line 170 — add an `elif ide == "myide"` branch that calls your generator).

### 3. (Optional) Add Override Files

If the IDE requires specific rules, create:
```
harness/overrides/myide/rules.md
```

This file is **automatically appended** to the generated `CLAUDE.md` /
`.cursorrules` / `QWEN.md` (whichever matches the `ide=` argument passed
to `bootstrap_templates.build_full_body`). The block lands right before
the `<!-- DYNAMIC:START -->` marker, so the doctor's drift checker still
ignores user-side state but treats the override as canonical body. Pass
`ide="myide"` from your `generate_myiderules()` call so the override is
picked up — passing `ide=None` (used by `AGENTS.md` on purpose, since it
is host-agnostic) drops the block entirely.

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
harness/
├── skills/          # 12 core auto-deployed (+ /brain conditional) + 20 vendor opt-in (--include-official)
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

Bootstrap lookup chain: `harness/skills/` → `harness/{ide}/skills/` → `harness/claude/skills/`
