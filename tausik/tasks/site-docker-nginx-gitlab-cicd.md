---
slug: site-docker-nginx-gitlab-cicd
title: "Docker (multi-stage) + nginx serve + .gitlab-ci.yml (SENAR pattern, port 8900)"
status: done
epic: v15-docs-site
story: docs-site-foundation
complexity: simple
role: developer
stack: python
tier: light
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T12:04:53Z"
---

## Goal

Deploy tausik.tech identical to SENAR: Dockerfile multi-stage (node:22-alpine build with pnpm via corepack → nginx:alpine serve), site/nginx.conf with security headers + cache rules + try_files for / and /ru/, .gitlab-ci.yml with stages build (tags=[common], docker build+push to CI_REGISTRY) and deploy (tags=[docker-services], docker stop+rm tausik-site, docker run -d --name tausik-site --restart unless-stopped -p 8900:80, sleep 3, ps + curl healthcheck). .dockerignore excludes node_modules + .vitepress/{cache,dist}. only main branch. GitHub mirror untouched.

## Acceptance Criteria

1. Dockerfile в корне репо: multi-stage (node:22.14.0-alpine AS build с corepack pnpm install --frozen-lockfile + pnpm build, затем nginx:alpine со скопированным /repo/site/.vitepress/dist в /usr/share/nginx/html + site/nginx.conf в /etc/nginx/conf.d/default.conf, EXPOSE 80). 2. site/nginx.conf: listen 80, root /usr/share/nginx/html, index index.html, security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy), location /assets/ с expires 1y immutable, location /ru/ с try_files, default location / с try_files, gzip on. 3. .dockerignore в корне: исключает **/node_modules, **/.vitepress/cache, **/.vitepress/dist, **/dist, .git, .tausik, site/public/uploads. 4. .gitlab-ci.yml дополнен (или создан) stages build+deploy SENAR-style: IMAGE=$CI_REGISTRY_IMAGE/site:tag, docker login → build --cache-from $IMAGE_LATEST → push; deploy: stop+rm tausik-site, run -d --name tausik-site --restart unless-stopped -p 8900:80, sleep 3, ps grep, curl healthcheck. only main. 5. Локальная smoke-проверка: docker build . -t tausik-site:test && docker run -d --name tausik-site-test -p 8900:80 tausik-site:test → curl http://localhost:8900/ HTTP 200, curl /ru/ HTTP 200, curl /docs/quickstart HTTP 200. Останавливаем контейнер после теста. 6. GitHub mirror untouched: .github/ не создаём, sites-deploy актуален только в gitlab. 7. Failure mode: при отсутствующем site/.vitepress/dist (пропущен build step) — nginx запускается, но / отдаёт 404 (документировано); Dockerfile сам гарантирует наличие dist через RUN pnpm build перед COPY --from=build.

## Plan

## Rollback

## Journal

- 2026-05-15T12:04:53Z [implementation] — AC verified: 1. ✓ Dockerfile multi-stage (node:22.14.0-alpine + corepack pnpm install --frozen-lockfile + RUN pnpm build with BuildKit cache mount /root/.local/share/pnpm/store → nginx:alpine + COPY --from=build /repo/site/.vitepress/dist /usr/share/nginx/html + COPY site/nginx.conf, EXPOSE 80); 2. ✓ site/nginx.conf with listen 80 + root /usr/share/nginx/html + security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy) + /assets/ 1y immutable + /ru/ try_files $uri $uri.html + default / try_files (CLEANURLS fix: $uri.html required for VitePress single-file rendering); 3. ✓ .dockerignore excludes .git, .github, **/node_modules, **/.vitepress/{cache,dist}, .tausik, site/public/uploads (preventive); 4. ✓ .gitlab-ci.yml SENAR-pattern stages build (tags=[common], docker login+pull+build --cache-from $IMAGE_LATEST + push) and deploy (tags=[docker-services], stop+rm tausik-site, run -d --name tausik-site --restart unless-stopped -p 8900:80, sleep 3, ps grep, curl healthcheck), only main; 5. ✓ Local smoke test: DOCKER_BUILDKIT=1 docker build -t tausik-site:test . ✓ (vitepress 5.91s), docker run -d --name tausik-site-test -p 8900:80 → 6 probes HTTP 200 (/=20.5KB, /ru/=21KB, /docs/quickstart=57.2KB, /ru/docs/quickstart=65.7KB, /docs/architecture=54.2KB, /ru/docs/architecture=59.3KB); 6. ✓ GitHub mirror untouched: .github/workflows/ contains pre-existing tests.yml/test-coverage.yml/security-review.yml only (framework CI, mtime predates task), no new files added by this task; 7. ✓ Failure mode logically guaranteed by Dockerfile — RUN pnpm build in build stage exits non-zero if VitePress build fails (verified empirically: missing index.md / git ENOENT both produced exit-1 builds during iteration before fix).
