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
| Codex | `.codex` | `AGENTS.md` | — | `CODEX_SANDBOX_DIR` env |
| OpenCode | `.opencode` | `.opencode/tausik-rules.md` | QG-0 plugin | `.opencode/` dir (+ `OPENCODE_DIR` env, unverified) |

Rows with `—` under Hooks have no scaffold branch: TAUSIK does not generate their
config and does not install a QG-0 enforcement hook for them.

**OpenCode is a separate host, not a Codex alias** (before v1.7.0 `OPENCODE_DIR`
resolved to `codex`, so an OpenCode session was handed `.codex/` paths that OpenCode
never reads). It reads `opencode.json` (not `.codex/config.toml`), loads plugins from
`.opencode/plugins/` (plural), and merges extra rule files listed under the config's
`instructions` key.

Its enforcement is a plugin, not a process hook: `.opencode/plugins/tausik-qg0.js`
implements `tool.execute.before` and throws on `write`/`edit`/`apply_patch` when no
TAUSIK task is active — the same contract as Claude Code's PreToolUse hook.

OpenCode is also the only host whose rules file is not at the project root. Rules live
in `.opencode/tausik-rules.md` and are wired in through `instructions`, because
OpenCode resolves `AGENTS.md` first-matching-file-wins — a user's own AGENTS.md would
shadow ours forever. `instructions` files are merged with AGENTS.md instead, so
`--ide opencode` deliberately generates no AGENTS.md (it would duplicate the rules in
the context).

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
├── claude/mcp/      # MCP servers — CANONICAL for every IDE (copy_mcp falls back here)
└── opencode/plugins/ # QG-0 enforcement plugin (the one genuinely IDE-specific artifact)
```

Do **not** add a `harness/<your-ide>/mcp/` directory. `copy_mcp` prefers it over the canonical
tree, so a per-IDE copy silently keeps serving the old server the day someone patches only the
claude one. A byte-identical `harness/cursor/mcp/` existed for exactly that reason and was
deleted in v1.7.0; `tests/test_mcp_single_canonical_tree.py` now refuses to let one come back.

Bootstrap lookup chain: `harness/skills/` → `harness/{ide}/skills/` → `harness/claude/skills/`
