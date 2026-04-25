# Customization Guide

> **Contract:** TAUSIK never touches your `.tausik/` directory. Anything you put under `.tausik/stacks/<name>/` survives every framework upgrade.

## What you can customize

| Goal | Where |
|---|---|
| Add a new stack just for your project | `.tausik/stacks/<name>/stack.json` |
| Tweak a built-in stack (more file extensions, custom gate command, disabled gate) | `.tausik/stacks/<name>/stack.json` with `"extends": "builtin:<name>"` |
| Stack-specific gates (e.g. `ruff --select=E,W`) | Override the gate inside a stack's `gates` map |
| Process-wide gate flags (enabled/disabled) | `.tausik/config.json` under `"gates"` |

## Quickstart: override an existing stack

Say the built-in `python` stack ships with a `pytest` gate, but your project also wants Pyright type-checking and an extra `.pyi` extension treated as Python.

1. Create the override file:

   ```bash
   mkdir -p .tausik/stacks/python
   ```

2. Drop your `stack.json` in there:

   ```json
   {
     "name": "python",
     "extends": "builtin:python",
     "extensions_extra": [".pyi"],
     "gates": {
       "pyright": {
         "enabled": true,
         "severity": "warn",
         "trigger": ["task-done"],
         "command": "pyright {files}",
         "description": "Pyright type check (custom)",
         "stacks": ["python"]
       }
     }
   }
   ```

3. Verify:

   ```bash
   .tausik/tausik stack lint           # validates your stack.json
   .tausik/tausik stack export python  # shows resolved (built-in + override) decl
   .tausik/tausik stack diff python    # shows what your override changes
   ```

## Merge semantics

When you declare `"extends": "builtin:NAME"`:

- **`extensions_extra`** — additive. Appended to the inherited `extensions` list. Use this to *add* extensions; use `extensions` itself only if you want a full replace.
- **`gates`** — per-key override. Keys present in your decl override the inherited entries. A key with value `null` **disables** an inherited gate.
- **`detect`, `filenames`, `path_hints`, `version`, `guide_path`** — replace if present in your override; otherwise inherited unchanged.

A user decl **without** `extends` and with a name that matches a built-in is a **full replace** — the built-in is dropped entirely.

A user decl with a new name is a **standalone** stack — it's added to the registry independently.

## Disabling an inherited gate

```json
{
  "name": "python",
  "extends": "builtin:python",
  "gates": { "pytest": null }
}
```

That's it. `null` removes the gate from the resolved decl. The built-in stays untouched on disk.

## When to reach for `.tausik/config.json` instead

Use `config.json → gates.<name>.enabled` when you just want to flip a gate on/off project-wide without changing its command, severity, or stack scope. Use `.tausik/stacks/<name>/stack.json` when you need to alter the gate definition itself or add new ones.

## Resetting an override

```bash
.tausik/tausik stack reset python      # prompts for confirmation
.tausik/tausik stack reset python --yes
```

This deletes `.tausik/stacks/python/`. The built-in stack is unaffected.

## Validation tools

| Command | Purpose |
|---|---|
| `tausik stack lint` | Validates every `.tausik/stacks/*/stack.json` against `_schema.json`. |
| `tausik stack export <name>` | Prints the resolved decl as JSON (so you can confirm the merge). |
| `tausik stack diff <name>` | Unified diff between built-in and your override. |

## What you must NOT do

- **Don't edit `stacks/<name>/stack.json` directly.** That tree is owned by bootstrap. Your edits will be overwritten on the next `python bootstrap/bootstrap.py` (and CI may force-bootstrap). Always go through `.tausik/stacks/`.
- **Don't put per-task overrides in stack.json.** Per-task knobs belong in `.tausik/config.json`.

## Adding a brand-new stack

If your project uses a stack TAUSIK doesn't ship — say, Elixir:

```json
{
  "name": "elixir",
  "detect": [{ "file": "mix.exs", "type": "exact" }],
  "extensions": [".ex", ".exs"],
  "gates": {
    "mix-test": {
      "enabled": true,
      "severity": "block",
      "trigger": ["task-done"],
      "command": "mix test",
      "description": "Run Elixir tests",
      "stacks": ["elixir"],
      "timeout": 240
    }
  }
}
```

After `tausik stack lint` passes, you can use `--stack elixir` in `task add` and the registry will surface gates correctly.

## See also

- [Stacks Plugin Guide](stacks.md) — full schema reference.
- [Upgrade Safety](upgrade.md) — what bootstrap touches and what it doesn't.
