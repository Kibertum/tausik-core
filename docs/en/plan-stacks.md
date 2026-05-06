# Stack Detection Tables

Used by /plan skill to auto-detect project stacks.

## File Detection

| Detect Files | Stack Name | Reference |
|-------------|------------|-----------|
| requirements.txt, pyproject.toml + fastapi | fastapi | harness/stacks/fastapi.md |
| manage.py, django in requirements | django | harness/stacks/django.md |
| composer.json + laravel | laravel | harness/stacks/laravel.md |
| composer.json + symfony | symfony | harness/stacks/symfony.md |
| package.json + express/fastify | node | harness/stacks/node.md |
| go.mod | go | harness/stacks/go.md |
| mix.exs | elixir | harness/stacks/elixir.md |
| nuxt.config.ts | nuxt | harness/stacks/nuxt.md |
| next.config.* | next | harness/stacks/next.md |
| svelte.config.js + @sveltejs/kit | sveltekit | harness/stacks/sveltekit.md |
| svelte.config.js (no kit) | svelte | harness/stacks/svelte.md |
| package.json + react (no next) | react | harness/stacks/react.md |
| pubspec.yaml + flutter | flutter | harness/stacks/flutter.md |
| *.xcodeproj, Package.swift | ios | harness/stacks/ios.md |
| *.csproj + Unity | unity | harness/stacks/unity.md |
| build.gradle + android | android | harness/stacks/android.md |
| package.json + react-native | react-native | harness/stacks/react-native.md |
| Cargo.toml | rust | harness/stacks/rust.md |
| pyproject.toml (no fastapi) | python | harness/stacks/python.md |
| composer.json (no framework) | php | harness/stacks/php.md |
| docker-compose.yml, Dockerfile, k8s/ | devops | harness/stacks/devops.md |
| SQL files, migrations/ | db | harness/stacks/db.md |
| OWASP, security configs | security | harness/stacks/security.md |
| SLO, monitoring configs | sre | harness/stacks/sre.md |
| CSS, design tokens, a11y | ux | harness/stacks/ux.md |
| architecture, ADR | lead | harness/stacks/lead.md |
| Unity + game design docs | game-designer | harness/stacks/game-designer.md |
| narrative docs, lore | narrative | harness/stacks/narrative.md |
| pixel art, sprites, ComfyUI | pixel-artist | harness/stacks/pixel-artist.md |
| audio, FMOD, sound assets | sound-designer | harness/stacks/sound-designer.md |

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
