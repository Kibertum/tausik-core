**English** | [Русский](../ru/roles.md)

# Roles

Roles describe **who** is doing the work. They drive task routing, skill recommendations, and the agent profile that gets injected when you start a task.

In TAUSIK roles are **free text** on tasks (`task add ... --role developer`), backed by an optional **registry** that pairs SQLite metadata with a markdown profile.

## Storage Model — Hybrid

| Layer | Where | What |
|-------|-------|------|
| Metadata | `roles` table in `.tausik/tausik.db` | slug, title, description, base/extends |
| Profile | `agents/roles/{slug}.md` | Behavioural prompt the agent reads when claiming a task with that role |

A role exists in either layer independently. `role list` merges both views, marking rows as **registered** (DB), **profile-only** (markdown without DB row), or **db-only** (DB row without profile).

You don't need to register a role before assigning it — `--role qa-lead` works whether or not `qa-lead` is in the registry. The registry exists to centralize profiles and seed defaults across teams.

## Default Profiles

After bootstrap, `agents/roles/` ships with five default profiles:

- `architect.md` — system design, trade-offs, decision records
- `developer.md` — implementation, refactoring, debugging
- `qa.md` — test design, coverage, fake-test detection
- `tech-writer.md` — documentation, parity, examples
- `ui-ux.md` — interaction design, accessibility, microcopy

Run `tausik role seed` to bootstrap rows in the DB from these markdown files plus any role names already used on tasks.

## CLI

```bash
role list                                    # list roles (DB + profile-only)
role show <slug>                             # show role record + profile path
role create <slug> <title> [--description T] [--extends BASE_ROLE]
role update <slug> [--title T] [--description D]
role delete <slug>
role seed                                    # bootstrap from agents/roles/*.md + task usage
```

`--extends` clones the profile from a base role. For example:

```bash
.tausik/tausik role create senior-dev "Senior Developer" --extends developer
```

This copies `agents/roles/developer.md` to `agents/roles/senior-dev.md` so you can refine it. The DB row tracks the `extends` relationship.

## MCP

| Tool | Description |
|------|-------------|
| `tausik_role_list` | List roles |
| `tausik_role_show` | Show role record + profile path |
| `tausik_role_create` | Create role (optionally extends a base) |
| `tausik_role_update` | Update title/description |
| `tausik_role_delete` | Delete role row (profile file is preserved) |
| `tausik_role_seed` | Bootstrap from `agents/roles/*.md` + existing task `role` values |

## Common Patterns

**Add a domain-specific role for a vertical**

```bash
.tausik/tausik role create payment-engineer "Payment Engineer" \
  --description "PCI-DSS-aware backend dev with strong audit/security instincts" \
  --extends developer
```

**Use the role on a task**

```bash
.tausik/tausik task add "Refund flow webhook" --story payments \
  --slug refund-webhook --role payment-engineer --stack go --complexity medium
```

**Filter the backlog**

```bash
.tausik/tausik task list --role qa --status active
```

## Negative Cases

- Roles are **not** restricted to a fixed enum. Any string is accepted on `--role`. The validator does not reject unregistered roles.
- `role delete` does **not** remove `agents/roles/{slug}.md`. The profile is preserved so you can re-seed later. To delete the file, remove it manually.
- `role seed` is **idempotent**: re-running it does not duplicate rows.

## What's Next

- **[CLI Commands](cli.md)** — `task add --role`, `task list --role`
- **[MCP Tools](mcp.md)** — programmatic surface for role management
- **[Skills](skills.md)** — skills can read role profiles to tailor behaviour
