**English** | [Русский](/ru/docs/skill-bundles)

# Skill Bundles

Skill bundles are a logical grouping of vendor skills from `tausik-skills` (the official `Kibertum/tausik-skills` repo, mirrored under `skills-official/` in dev). One CLI call installs every skill in a bundle — useful for matching a project's domain (integrations, data extraction, deep quality) without remembering individual skill names.

> **Where bundles come from (changed in v1.8):** a bundle's composition belongs
> to the store that ships the skills. `bundles.json` travels *inside* a
> tausik-skills-format repo, next to its `tausik-skills.json`, and
> `tausik skill bundle` reads the repos you have added with
> `tausik skill repo add`.
>
> Until v1.8 resolution looked only for a `skills-official/` directory beside
> the core checkout. That directory exists while developing the framework and
> never in a project you bootstrapped, so the command failed with "no bundles
> manifest" for every actual user. It survives as a development fallback only.
>
> **Bundles with the same name across stores union their skill lists.** This is
> what keeps a private store private: a public store can declare a bundle and
> leave it empty while a private one fills it, and neither manifest ever names
> the other's contents. A bundle stops counting as a placeholder the moment any
> store fills it. Keeping the list in the core instead was rejected for exactly
> this reason — the core is publicly mirrored, so a core-side membership list
> would mean naming private skills in a published file.

## The 6 bundles

| Bundle | Skills | When to install |
|--------|--------|-----------------|
| `integrations` | `jira`, `bitrix24`, `confluence`, `sentry` | External-service projects: ticket workflows, CRM, docs publishing, error monitoring. Each skill needs environment credentials. |
| `data-formats` | `excel`, `pdf`, `markitdown` | Document-processing projects: read/extract/convert binary formats. |
| `quality-pro` | `audit`, `security`, `optimize`, `zero-defect`, `ultra` | Anything where "looks fine" is not an acceptable bar — security-sensitive code, perf bottlenecks, precision-mode work. |
| `automation` | `run`, `loop-task`, `dispatch` | Batch / loop / multi-worker workflows — autonomous execution beyond single-task work. |
| `workflow-helpers` | `daily`, `retro`, `presale`, `skill-test`, `docs` | Productivity, retrospectives, presale estimation, doc generation, meta tooling. |
| `ru-locale` | *(empty placeholder)* | Reserved for Russian-language-specific skills. Will be populated as RU-specific skills are authored. |

## CLI

```bash
.tausik/tausik skill bundle list                    # all bundles + skill counts
.tausik/tausik skill bundle list --json             # machine-readable

.tausik/tausik skill bundle show integrations       # human-readable bundle body
.tausik/tausik skill bundle show integrations --json

.tausik/tausik skill bundle install integrations    # installs all 4 skills
.tausik/tausik skill bundle uninstall integrations  # removes all 4
```

`bundle install` reuses the existing `tausik skill install <name>` pipeline per skill — same vendor cache, same pip dependency resolution, same activation step. Bundle install:

- Routes each skill through the standard install code path (so per-skill safeguards still apply).
- Continues on per-skill error — one missing dep doesn't abort the rest. Errors land as `[ERR]` rows in the report.
- Skips deprecated skill names with a clear migration message (see "Deprecated skills" below).
- For the `ru-locale` placeholder, returns a single `placeholder` row and exits without installing anything.

## Deprecated skills

Five skills are removed from `skills-official/` and `registry.json` in v1.4 — they were duplicating built-in functionality.

| Removed | Replacement |
|---------|-------------|
| `go` | Use `/plan` + `/task` (built-in skills with QG-0 enforcement). |
| `next` | Use the CLI `tausik task next` (no skill install required). |
| `diff` | Use `git diff` and `/review` (already analyzes diffs). |
| `onboard` | Built-in `/start` covers session onboarding; first-time setup uses `python bootstrap/bootstrap.py --init`. |
| `init` | First-time project setup is `python bootstrap/bootstrap.py --init`. |

If you try to install a deprecated skill via `tausik skill bundle install <bundle>` (which can happen if a stale third-party manifest still references it), the CLI prints `[SKIP] <name>: deprecated: <migration message>` and continues with the rest of the bundle.

For migration steps if you currently have these skills installed locally, see [Skill Bundles Migration](skill-bundles-migration.md).

## Authoring a custom bundles file

If you maintain your own skill repo, ship a `bundles.json` next to `tausik-skills.json`. Schema:

```json
{
  "version": 1,
  "bundles": {
    "<bundle-name>": {
      "title": "Human-readable title",
      "description": "One-paragraph description.",
      "skills": ["skill-a", "skill-b"],
      "placeholder": false
    }
  },
  "deprecated": {
    "old-skill-name": "Migration message shown when bundle install hits this name."
  }
}
```

- `bundles.<name>.skills` is a list of skill names that must exist as `<repo>/<skill-name>/SKILL.md`.
- `bundles.<name>.placeholder = true` makes bundle install/uninstall a no-op (useful for reserving a future bundle slot).
- `deprecated` entries are advisory — they only affect the printed message during bundle install; CLI never deletes anything based on this.

## What's next

- **[Vendor skills](vendor-skills.md)** — repo trust, manifest format, three-tier system
- **[Skill ecosystem](skill-ecosystem.md)** — how bundles fit alongside core skills + Claude-native sub-agents
- **[Skill Bundles Migration](skill-bundles-migration.md)** — for users with the deprecated 5 skills installed
