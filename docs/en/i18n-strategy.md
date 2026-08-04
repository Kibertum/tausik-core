**English** | [Русский](/ru/docs/i18n-strategy)

# Localization Strategy

## Approach

TAUSIK uses **directory-based localization**: `docs/en/` (English) + `docs/ru/` (Russian).

- **Main language** for GitHub: English (`README.md`)
- Each localized file has a language switcher linking to the other version
- All documentation is fully localized (EN + RU)

## Structure

```
README.md          ← English (main)
README.ru.md       ← Russian

docs/
├── en/            ← English docs (~45 files: quickstart, workflow, skills,
│                    hooks, cli, mcp, architecture, adding-new-ide,
│                    vendor-skills, senar-compliance-matrix, i18n-strategy,
│                    brain-*, skill-*, plan-*, cost-telemetry, environment,
│                    permissions, security, etc.)
├── ru/            ← Russian docs (~44 files; mirrors en/ minus a few EN-only
│                    docs like plan-review/plan-stacks/skill-spec/skill-patterns,
│                    plus RU-only agent-contract.md)
├── en/research/   ← Research notes, NOT paired: each stays in the language it
├── ru/research/      was written in (1 EN vs 10 RU today). See "What's NOT
│                     localized" below — this diagram used to claim the pair.
└── README.md      ← Navigation hub (bilingual)
```

## What's localized

| Location | RU | EN | Notes |
|----------|----|----|-------|
| `README.md` / `README.ru.md` | ✓ | ✓ (main) | Entry point for GitHub |
| `docs/en/` + `docs/ru/` | ✓ | ✓ | All user docs fully localized |

## What's NOT localized

- **CLAUDE.md** — project-internal instructions, follows user's language preference
- **CHANGELOG.md** — historical record, stays in original language
- **Skills (SKILL.md)** — agent instructions, English frontmatter + Russian content
- **CLI help text** — stays in Russian (follows user locale)
- **Code comments** — English
- **`docs/research/`**, **`docs/en/research/`**, **`docs/ru/research/`** —
  technical notes and measurements, kept in the language they were written in. A
  research note records what someone measured on a date; translating it invites
  the two copies to drift, and a drifted measurement is worse than an unread one.
  `audit_stale_docs` excludes all three research homes from its mirror check for
  this reason — the exclusion matches the rule rather than hiding a gap, and it
  stays.

## How to add a new language

1. Create `docs/{lang}/` directory
2. Copy files from `docs/en/`, translate prose content
3. Add language switcher to all files: ``[English](../en/file.md) | [Язык](../lang/file.md)`` (example, replace `lang` with your language code)
4. Keep all code blocks, paths, and technical terms as-is
5. Update `docs/README.md` navigation hub
