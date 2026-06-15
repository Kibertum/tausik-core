**English** | [Русский](/ru/docs/skill-bundles-migration)

# Migrating to Skill Bundles (v1.4)

Short read for users who installed any of the 5 vendor skills now removed from `tausik-skills`. If you've never run `tausik skill install go|next|diff|onboard|init`, **nothing changes for you** — bundles are purely additive.

## What changed in v1.4

1. **5 vendor skills removed** from `skills-official/` and `registry.json`: `go`, `next`, `diff`, `onboard`, `init`. Each duplicated built-in functionality (see [Skill Bundles](skill-bundles.md) for the replacement table).
2. **New `tausik skill bundle` CLI** for bulk install/uninstall — see [Skill Bundles](skill-bundles.md).
3. **No physical reorganization** of `skills-official/` — every other skill keeps its existing path. `tausik skill install <name>` still works for the 20 remaining skills.

## If you have any of the 5 removed skills installed

### Step 1 — Inspect what you have

```bash
.tausik/tausik skill list
```

Look in the `[ACTIVE]` and `[VENDORED]` sections for any of: `go`, `next`, `diff`, `onboard`, `init`.

### Step 2 — Uninstall them

```bash
.tausik/tausik skill uninstall go        # repeat per name
```

This drops the skill from `.claude/skills/` and from `installed_skills` in `.tausik/config.json`. The vendor cache under `.tausik/vendor/tausik-skills/` is shared with other skills — leave it alone.

### Step 3 — Switch to the replacement

| Removed | What to use instead |
|---------|---------------------|
| `go` | Run `/plan <free-form description>` then `/task <slug>` — the same one-phrase flow with QG-0 enforcement. |
| `next` | Run `.tausik/tausik task next` — no skill install needed. |
| `diff` | Run `git diff` directly, or `/review diff` (the standard `/review` already understands diffs). |
| `onboard` | Run `/start` (built-in) — covers project state, recent work, suggested next action. For first-time setup of a fresh project, use `python bootstrap/bootstrap.py --init`. |
| `init` | Run `python bootstrap/bootstrap.py --init` — creates `.tausik/`, `.claude/`, project DB. No skill required. |

### Step 4 — Re-bootstrap (only if your `skills-official/` checkout is local)

If you're tracking the source repo (TAUSIK contributors), pull the latest and re-bootstrap so the deleted skill directories disappear from your `.claude/`:

```bash
git pull
python bootstrap/bootstrap.py --ide claude
```

Consumer projects (those that vendored `tausik` via the bootstrap script) will pick up the change on the next `python .tausik-lib/bootstrap/bootstrap.py` automatically — no manual cleanup needed.

## What if a third-party repo still references a deprecated skill?

The bundle install CLI is defensive: when it hits a deprecated skill name, it prints

```
[SKIP] <name>: deprecated: <migration message>
```

and continues with the rest of the bundle. Nothing breaks — the install just skips the deprecated entry. If you're maintaining a custom bundles file, drop the deprecated names from `bundles.<name>.skills` to avoid the warning.

## Why these 5 specifically

All five duplicated functionality that already exists in built-in core skills or the CLI itself. Removing them:

- Cuts ~15-20 KB of vendor surface area users had to reason about.
- Makes the "what skill should I use" question simpler — every remaining vendor skill addresses something the core doesn't.
- Removes the install/activate friction for behavior the agent has on day one.

## Q: Will the bundles list change later?

The `tausik-skills` marketplace push (the public-facing version of `bundles.json`) is **deferred until after v1.4 ships** per the polish moratorium. Once it lands publicly, the 6 bundles documented here are the v1.4 baseline. Future versions may add bundles (the empty `ru-locale` slot is the obvious next candidate); existing bundles are stable.
