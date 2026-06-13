# Таблицы определения стека

Используется скиллом /plan для авто-определения стеков проекта. Каждая строка
сопоставляет признак обнаружения с профилем стека в `stacks/<name>/` (который
поставляет `stack.json` плюс `guide.md`). Роли (`security`, `sre`, `lead`, `ux`,
`game-designer`, `narrative`, `pixel-artist`, `sound-designer`) живут в
`harness/roles/`, а не в `stacks/` — см. `roles.md` для этой таксономии.

## Определение по файлам

| Detect Files | Stack Name | Reference |
|-------------|------------|-----------|
| pyproject.toml + fastapi import / dependency | fastapi | stacks/fastapi/guide.md |
| manage.py, django in requirements | django | stacks/django/guide.md |
| pyproject.toml / requirements.txt + flask | flask | stacks/flask/guide.md |
| pyproject.toml / requirements.txt (без fastapi/flask/django) | python | stacks/python/guide.md |
| composer.json + laravel | laravel | stacks/laravel/guide.md |
| composer.json (без фреймворка) | php | stacks/php/guide.md |
| `.blade.php` templates | blade | stacks/blade/guide.md |
| go.mod | go | stacks/go/guide.md |
| Cargo.toml | rust | stacks/rust/guide.md |
| build.gradle / *.kt | kotlin | stacks/kotlin/guide.md |
| pom.xml / build.gradle + *.java | java | stacks/java/guide.md |
| *.swift, Package.swift | swift | stacks/swift/guide.md |
| pubspec.yaml + flutter | flutter | stacks/flutter/guide.md |
| tsconfig.json | typescript | stacks/typescript/guide.md |
| package.json (без ts/фреймворка) | javascript | stacks/javascript/guide.md |
| next.config.* | next | stacks/next/guide.md |
| nuxt.config.ts | nuxt | stacks/nuxt/guide.md |
| svelte.config.js | svelte | stacks/svelte/guide.md |
| package.json + react (без next) | react | stacks/react/guide.md |
| package.json + vue (без nuxt) | vue | stacks/vue/guide.md |
| Dockerfile, docker-compose.yml | docker | stacks/docker/guide.md |
| ansible.cfg, playbooks/ | ansible | stacks/ansible/guide.md |
| *.tf, terraform.tfstate | terraform | stacks/terraform/guide.md |
| Chart.yaml, templates/ (Helm) | helm | stacks/helm/guide.md |
| *.yaml в k8s/ или manifests/ | kubernetes | stacks/kubernetes/guide.md |

## Сопоставление по ключевым словам

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

## Координация для сложных задач

Для задач, охватывающих несколько стеков, `/plan` выбирает один основной стек и
перечисляет вспомогательные стеки для ревью на момент завершения. Роли (security,
sre, lead, ux, дизайн-ориентированные) накладываются поверх выбранного стека —
сами по себе они не являются профилями стека.

| Concern | Layer |
|---------|-------|
| Изменения, видимые пользователю | role: ux |
| Auth / чувствительные данные | role: security |
| Изменения API | основной стек |
| Изменения UI | основной стек |
| Затронут деплой | docker / kubernetes / terraform / helm |
| Архитектура / ADR | role: lead |

```
Primary Stack:    Делает реализацию
Supporting Stacks: Ревьюят конкретные аспекты на завершении
Role (optional):  Сквозная забота (security audit, ux review, …)
```
