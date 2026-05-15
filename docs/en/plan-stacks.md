# Stack Detection Tables

Used by /plan skill to auto-detect project stacks. Each row maps a detection
hint to a stack profile under `stacks/<name>/` (which ships `stack.json`
plus `guide.md`). Roles (`security`, `sre`, `lead`, `ux`, `game-designer`,
`narrative`, `pixel-artist`, `sound-designer`) live under `harness/roles/`
instead of `stacks/` — see `roles.md` for that taxonomy.

## File Detection

| Detect Files | Stack Name | Reference |
|-------------|------------|-----------|
| pyproject.toml + fastapi import / dependency | fastapi | stacks/fastapi/guide.md |
| manage.py, django in requirements | django | stacks/django/guide.md |
| pyproject.toml / requirements.txt + flask | flask | stacks/flask/guide.md |
| pyproject.toml / requirements.txt (no fastapi/flask/django) | python | stacks/python/guide.md |
| composer.json + laravel | laravel | stacks/laravel/guide.md |
| composer.json (no framework) | php | stacks/php/guide.md |
| `.blade.php` templates | blade | stacks/blade/guide.md |
| go.mod | go | stacks/go/guide.md |
| Cargo.toml | rust | stacks/rust/guide.md |
| build.gradle / *.kt | kotlin | stacks/kotlin/guide.md |
| pom.xml / build.gradle + *.java | java | stacks/java/guide.md |
| *.swift, Package.swift | swift | stacks/swift/guide.md |
| pubspec.yaml + flutter | flutter | stacks/flutter/guide.md |
| tsconfig.json | typescript | stacks/typescript/guide.md |
| package.json (no ts/framework) | javascript | stacks/javascript/guide.md |
| next.config.* | next | stacks/next/guide.md |
| nuxt.config.ts | nuxt | stacks/nuxt/guide.md |
| svelte.config.js | svelte | stacks/svelte/guide.md |
| package.json + react (no next) | react | stacks/react/guide.md |
| package.json + vue (no nuxt) | vue | stacks/vue/guide.md |
| Dockerfile, docker-compose.yml | docker | stacks/docker/guide.md |
| ansible.cfg, playbooks/ | ansible | stacks/ansible/guide.md |
| *.tf, terraform.tfstate | terraform | stacks/terraform/guide.md |
| Chart.yaml, templates/ (Helm) | helm | stacks/helm/guide.md |
| *.yaml under k8s/ or manifests/ | kubernetes | stacks/kubernetes/guide.md |

## Keyword Mapping

| Keywords | Stack |
|----------|-------|
| API, endpoint, FastAPI, async | fastapi |
| Django, ORM, admin | django |
| Flask, blueprint, jinja | flask |
| CLI, daemon, systemd | python |
| Laravel, Eloquent | laravel |
| Blade template, `@yield`, `@section` | blade |
| PHP, vanilla php | php |
| Go, Chi, Gin, goroutine | go |
| Rust, tokio, async, cargo | rust |
| Kotlin, coroutines, Compose | kotlin |
| Java, Spring, Maven | java |
| Swift, SwiftUI, Combine | swift |
| Flutter, Dart, GetX | flutter |
| TypeScript, type, interface, generic | typescript |
| JavaScript, vanilla js, web API | javascript |
| Next, app router, server actions | next |
| Nuxt, page, layout, useFetch | nuxt |
| Svelte, store, runes | svelte |
| React, hooks, JSX | react |
| Vue, composition API, ref/reactive | vue |
| Docker, container, image | docker |
| Ansible, playbook, role | ansible |
| Terraform, plan, apply, state | terraform |
| Helm, chart, values.yaml | helm |
| Kubernetes, pod, deployment, service | kubernetes |

## Coordination for Complex Tasks

For tasks that span multiple stacks, `/plan` picks one primary stack and
lists supporting stacks for completion-time review. Roles (security,
sre, lead, ux, design-leaning ones) layer on top of the chosen stack —
they aren't stack profiles themselves.

| Concern | Layer |
|---------|-------|
| User-facing changes | role: ux |
| Auth / sensitive data | role: security |
| API changes | primary stack |
| UI changes | primary stack |
| Deploy affected | docker / kubernetes / terraform / helm |
| Architecture / ADR | role: lead |

```
Primary Stack:    Does the implementation
Supporting Stacks: Review specific aspects on completion
Role (optional):  Cross-cutting concern (security audit, ux review, …)
```
