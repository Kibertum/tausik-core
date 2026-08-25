---
slug: standalone-docs-site-fetch-docs-from-drugogo-repo-agent
title: "Standalone docs-site: fetch docs from другого репо + agent-readiness"
type: pattern
tags:
  - agent-readiness
  - deploy-token
  - gitlab-ci
  - llms.txt
  - mcp
  - nginx
  - runner-tags
  - site
  - vitepress
task: site-followup-exec
edges: []
---

VitePress-сайт, чей контент живёт в другом репо (tausik/site рендерит docs из tausik/core): docs НЕ вендорятся. fetch-docs.mjs/CI клонирует source-репо read-only DEPLOY TOKEN'ом (scope read_repository, создаётся через GitLab API POST /projects/:id/deploy_tokens с username; CI vars CORE_DEPLOY_USER не-masked + CORE_DEPLOY_TOKEN masked) в dot-каталог .docs-src/ (VitePress не сканирует dot-dirs, gitignored). sync-docs.mjs: .docs-src/{en,ru}→docs/,ru/docs/. HomeLanding импортит .docs-src/_generated/constants.json. GOTCHA: GitLab runners часто run_untagged=false — отдельный untagged job висит pending вечно; клади fetch в тегированный job. `common`-раннер обычно SHELL-executor с host docker+git (build делает docker build напрямую без dind) → `image:` игнорируется, но host git есть → клонируй inline в build. AGENT-READINESS (isitagentready.com): sitemap через config `sitemap:{hostname}`; public/robots.txt с AI-bot Allow + Sitemap-директивой; public/llms.txt (курированный, llmstxt.org) + dist/llms-full.txt (postbuild concat .docs-src); markdown content negotiation = postbuild копирует сырые .md в dist (/docs/x.md) + nginx `location ~* \.md$ {default_type text/markdown;}`; public/.well-known/mcp.json (MCP Server Card) — nginx `location ^~ /.well-known/` ОБЯЗАН предшествовать `location ~ /\.{deny}` (иначе 404); JSON-LD через config transformHead (SoftwareApplication на home, TechArticle на doc). Project id по пути 301-редиректит на numeric (tausik%2Fcore→/projects/61). Пример: pipeline 3307, 8/8 endpoints 200.
