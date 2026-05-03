# Stack Detection Tables

Used by /plan skill to auto-detect project stacks.

## File Detection

| Detect Files | Stack Name | Reference |
|-------------|------------|-----------|
| requirements.txt, pyproject.toml + fastapi | fastapi | agents/stacks/fastapi.md |
| manage.py, django in requirements | django | agents/stacks/django.md |
| composer.json + laravel | laravel | agents/stacks/laravel.md |
| composer.json + symfony | symfony | agents/stacks/symfony.md |
| package.json + express/fastify | node | agents/stacks/node.md |
| go.mod | go | agents/stacks/go.md |
| mix.exs | elixir | agents/stacks/elixir.md |
| nuxt.config.ts | nuxt | agents/stacks/nuxt.md |
| next.config.* | next | agents/stacks/next.md |
| svelte.config.js + @sveltejs/kit | sveltekit | agents/stacks/sveltekit.md |
| svelte.config.js (no kit) | svelte | agents/stacks/svelte.md |
| package.json + react (no next) | react | agents/stacks/react.md |
| pubspec.yaml + flutter | flutter | agents/stacks/flutter.md |
| *.xcodeproj, Package.swift | ios | agents/stacks/ios.md |
| *.csproj + Unity | unity | agents/stacks/unity.md |
| build.gradle + android | android | agents/stacks/android.md |
| package.json + react-native | react-native | agents/stacks/react-native.md |
| Cargo.toml | rust | agents/stacks/rust.md |
| pyproject.toml (no fastapi) | python | agents/stacks/python.md |
| composer.json (no framework) | php | agents/stacks/php.md |
| docker-compose.yml, Dockerfile, k8s/ | devops | agents/stacks/devops.md |
| SQL files, migrations/ | db | agents/stacks/db.md |
| OWASP, security configs | security | agents/stacks/security.md |
| SLO, monitoring configs | sre | agents/stacks/sre.md |
| CSS, design tokens, a11y | ux | agents/stacks/ux.md |
| architecture, ADR | lead | agents/stacks/lead.md |
| Unity + game design docs | game-designer | agents/stacks/game-designer.md |
| narrative docs, lore | narrative | agents/stacks/narrative.md |
| pixel art, sprites, ComfyUI | pixel-artist | agents/stacks/pixel-artist.md |
| audio, FMOD, sound assets | sound-designer | agents/stacks/sound-designer.md |

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
