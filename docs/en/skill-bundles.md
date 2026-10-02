**English** | [Русский](../ru/skill-bundles.md)

# Skill Bundles

<!-- doc-map: reader=user; zone=ide-and-skills -->

Skill bundles are optional groups declared by a skill repository. One CLI call installs every member, so use a bundle only when the project needs the complete group; otherwise install one skill to avoid unnecessary prompt surface.

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

## Availability

The official TAUSIK store does not publish bundles; it contains only `docs`, `excel`, and `pdf`, which are installed individually. Third-party repositories may publish bundles. Run `skill bundle list` after adding one. Core does not copy a store's bundle names or membership.

## CLI

```bash
.tausik/tausik skill bundle list                    # all bundles + skill counts
.tausik/tausik skill bundle list --json             # machine-readable

.tausik/tausik skill bundle show <name>             # human-readable bundle body
.tausik/tausik skill bundle show <name> --json

.tausik/tausik skill bundle install <name>           # installs every member
.tausik/tausik skill bundle uninstall <name>         # removes every member
```

`bundle install` reuses the existing `tausik skill install <name>` pipeline per skill — same vendor cache, same pip dependency resolution, same activation step. Bundle install:

- Routes each skill through the standard install code path (so per-skill safeguards still apply).
- Continues on per-skill error — one missing dep doesn't abort the rest. Errors land as `[ERR]` rows in the report.
- Skips names marked deprecated by the repository with its migration message.
- For a placeholder bundle, returns a single `placeholder` row and exits without installing anything.

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
