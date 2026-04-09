# Stack Detection Tables

Used by /plan skill to auto-detect project stacks.

## File Detection

| Detect Files | Stack Name | Reference |
|-------------|------------|-----------|
| requirements.txt, pyproject.toml + fastapi | fastapi | .claude/references/stacks/plan/fastapi.md |
| manage.py, django in requirements | django | .claude/references/stacks/plan/django.md |
| composer.json + laravel | laravel | .claude/references/stacks/plan/laravel.md |
| composer.json + symfony | symfony | .claude/references/stacks/plan/symfony.md |
| package.json + express/fastify | node | .claude/references/stacks/plan/node.md |
| go.mod | go | .claude/references/stacks/plan/go.md |
| mix.exs | elixir | .claude/references/stacks/plan/elixir.md |
| nuxt.config.ts | nuxt | .claude/references/stacks/plan/nuxt.md |
| next.config.* | next | .claude/references/stacks/plan/next.md |
| svelte.config.js + @sveltejs/kit | sveltekit | .claude/references/stacks/plan/sveltekit.md |
| svelte.config.js (no kit) | svelte | .claude/references/stacks/plan/svelte.md |
| package.json + react (no next) | react | .claude/references/stacks/plan/react.md |
| pubspec.yaml + flutter | flutter | .claude/references/stacks/plan/flutter.md |
| *.xcodeproj, Package.swift | ios | .claude/references/stacks/plan/ios.md |
| *.csproj + Unity | unity | .claude/references/stacks/plan/unity.md |
| build.gradle + android | android | .claude/references/stacks/plan/android.md |
| package.json + react-native | react-native | .claude/references/stacks/plan/react-native.md |
| Cargo.toml | rust | .claude/references/stacks/plan/rust.md |
| pyproject.toml (no fastapi) | python | .claude/references/stacks/plan/python.md |
| composer.json (no framework) | php | .claude/references/stacks/plan/php.md |
| docker-compose.yml, Dockerfile, k8s/ | devops | .claude/references/stacks/plan/devops.md |
| SQL files, migrations/ | db | .claude/references/stacks/plan/db.md |
| OWASP, security configs | security | .claude/references/stacks/plan/security.md |
| SLO, monitoring configs | sre | .claude/references/stacks/plan/sre.md |
| CSS, design tokens, a11y | ux | .claude/references/stacks/plan/ux.md |
| architecture, ADR | lead | .claude/references/stacks/plan/lead.md |
| Unity + game design docs | game-designer | .claude/references/stacks/plan/game-designer.md |
| narrative docs, lore | narrative | .claude/references/stacks/plan/narrative.md |
| pixel art, sprites, ComfyUI | pixel-artist | .claude/references/stacks/plan/pixel-artist.md |
| audio, FMOD, sound assets | sound-designer | .claude/references/stacks/plan/sound-designer.md |

## Keyword Mapping

| Keywords | Stack |
|----------|-------|
| API, endpoint, FastAPI, async | fastapi |
| Django, ORM, admin | django |
| Laravel, Eloquent, Blade | laravel |
| Express, Node, middleware | node |
| Go, Chi, Gin | go |
| Phoenix, Elixir, OTP | elixir |
| page, component, Vue, Nuxt | nuxt |
| React, Next, hooks | next / react |
| Svelte, SvelteKit | sveltekit / svelte |
| Flutter, Dart, GetX | flutter |
| iOS, Swift, SwiftUI | ios |
| Android, Kotlin, Compose | android |
| React Native, Expo | react-native |
| database, SQL, query, index | db |
| security, auth, OWASP, JWT | security |
| docker, CI/CD, deploy, k8s | devops |
| SLO, monitoring, incident | sre |
| UI/UX, design, accessibility | ux |
| architecture, planning | lead |
| CLI, daemon, systemd | python |
| Rust, tokio, async | rust |
| Symfony, Doctrine | symfony |
| PHP, vanilla php | php |
| Unity, C#, MonoBehaviour | unity |
| game design, balance, systems | game-designer |
| narrative, lore, story | narrative |
| pixel art, sprites | pixel-artist |
| sound, audio, music | sound-designer |

## Coordination for Complex Tasks

| Concern | Stack |
|---------|-------|
| User-facing changes | ux |
| Auth/sensitive data | security |
| API changes | backend stack |
| UI changes | frontend stack |
| Deploy affected | devops |

```
Primary Stack:    Does the implementation
Supporting Stacks: Review specific aspects on completion
```
