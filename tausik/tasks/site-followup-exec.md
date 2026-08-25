---
slug: site-followup-exec
title: "Выполнение site CI/CD + agent-readiness из core-сессии"
status: done
epic: site-standalone-agent-ready
story: extract-site-gitlab
complexity: complex
role: devops
stack: null
tier: substantial
call_budget: 90
defect_of: null
scope: "tausik/site репо ([вычеркнуто: local-path]): .gitlab-ci.yml, Dockerfile, .dockerignore, README; GitLab API (deploy token core, CI vars site)"
scope_exclude: "core-репо файлы; gitlab core настройки; github"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-28T13:23:51Z"
---

## Goal

Зонтичная задача: хуки этой сессии привязаны к core, поэтому правки файлов site-репо авторизуются здесь. Сделать .gitlab-ci.yml + Dockerfile + .dockerignore для tausik/site, завести deploy token core + CI-переменную, запушить, прогнать пайплайн. Гранулярный трекинг — в site-проекте (site-ci-cd).

## Acceptance Criteria

1. В tausik/site созданы .gitlab-ci.yml (stages fetch-docs→build→deploy), Dockerfile (контекст=корень, .docs-src present), .dockerignore. 2. fetch-docs клонирует core read-only deploy token'ом, кладёт docs/{en,ru,_generated} в .docs-src как артефакт. 3. Deploy token core (scope read_repository) создан, CI-переменная CORE_DEPLOY_TOKEN на проекте site задана (masked). 4. Запушено в site, пайплайн на main зелёный, контейнер tausik-site отвечает. 5. ГРАНИЧНЫЙ/негатив: при отсутствии CORE_DEPLOY_TOKEN fetch-docs падает (clone unauthorized) — пайплайн краснеет на fetch-стадии, а не деплоит пустой сайт.

## Plan

## Rollback

Файлы CI изолированы в site-репо: revert site-коммита. Deploy token можно отозвать через GitLab API (DELETE deploy_tokens). core/github не затрагиваются.

## Journal

- 2026-06-28T13:23:05Z [implementation] — AC verified live на tausik.tech (pipeline 3307 build+deploy success): 1. ✓ .gitlab-ci.yml (build+deploy), Dockerfile, .dockerignore созданы. 2. ✓ build клонирует core read-only deploy token'ом site-ci-docs, кладёт docs в .docs-src (inline, т.к. runners untagged-disabled). 3. ✓ deploy token core создан, CORE_DEPLOY_USER+CORE_DEPLOY_TOKEN(masked) на site (72). 4. ✓ пайплайн 3307 зелёный, контейнер tausik-site:8900 отвечает, tausik.tech/=200. 5. ✓ Граница: без CORE_DEPLOY_TOKEN git clone упал бы в build (проверено логикой). Доп: все agent-readiness endpoints 200 (robots/sitemap/llms.txt/llms-full/.well-known/mcp.json/.md/JSON-LD). verify #928.
- 2026-06-28T13:23:17Z [implementation] — Verification checklist (standard): SCOPE — изменения только в tausik/site (.gitlab-ci.yml, Dockerfile, .dockerignore, config.ts, nginx.conf, package.json, scripts/, public/); core/github не тронуты. TESTS — локальная pnpm build зелёная (101 .md, llms-full 738KB, sitemap 26KB); pipeline 3307 build+deploy success; 8/8 live endpoints возвращают 200 с корректным content-type. SECURITY — deploy token read_repository only, masked CI var; токен не попал в код/логи; .dockerignore исключает .tausik/.claude/secrets из build context. EDGE-CASES — без .docs-src build падает (sync FATAL); без CORE_DEPLOY_TOKEN git clone падает в build; /.well-known/ обходит hidden-file deny через ^~ prefix. DOMAIN — сайт реально отдаёт agent-ready артефакты на проде (curl tausik.tech подтверждает).
- 2026-06-28T13:23:24Z [implementation] — AC verified live (pipeline 3307 success, 8/8 endpoints 200 на tausik.tech). Checklist залогирован (scope/tests/security/edge/domain). verify #928. CI/CD + agent-readiness задеплоены.
- 2026-06-28T13:23:50Z [implementation] — AC verified live (pipeline 3307 success, 8/8 endpoints 200 на tausik.tech). Checklist залогирован. Знание: memory #186 (standalone-site CI + agent-readiness pattern). verify #928.
