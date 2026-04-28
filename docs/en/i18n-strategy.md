**English** | [Русский](../ru/i18n-strategy.md)

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
├── en/            ← English docs (13 files)
│   ├── quickstart.md, workflow.md, skills.md, hooks.md
│   ├── cli.md, mcp.md, architecture.md, adding-new-ide.md
│   ├── vendor-skills.md, senar-compliance-matrix.md, i18n-strategy.md
├── ru/            ← Russian docs (13 files, mirrors en/)
│   └── ...
└── README.md      ← Navigation hub (bilingual)

references/        ← Agent context (compact, loaded into AI context)
├── QUICKSTART.md / .en.md
├── architecture.md / .en.md
└── project-cli.md
```

## What's localized

| Location | RU | EN | Notes |
|----------|----|----|-------|
| `README.md` / `README.ru.md` | ✓ | ✓ (main) | Entry point for GitHub |
| `docs/en/` + `docs/ru/` (13 files each) | ✓ | ✓ | All docs fully localized |
| `references/QUICKSTART.md` / `.en.md` | ✓ | ✓ | Agent onboarding |
| `references/architecture.md` / `.en.md` | ✓ | ✓ | System design |

## What's NOT localized

- **CLAUDE.md** — project-internal instructions, follows user's language preference
- **CHANGELOG.md** — historical record, stays in original language
- **Skills (SKILL.md)** — agent instructions, English frontmatter + Russian content
- **CLI help text** — stays in Russian (follows user locale)
- **Code comments** — English
- **references/project-cli.md** — technical reference, Russian primary

## How to add a new language

1. Create `docs/{lang}/` directory
2. Copy files from `docs/en/`, translate prose content
3. Add language switcher to all files: ``[English](../en/file.md) | [Язык](../lang/file.md)`` (example, replace `lang` with your language code)
4. Keep all code blocks, paths, and technical terms as-is
5. Update `docs/README.md` navigation hub
