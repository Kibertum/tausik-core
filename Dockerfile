# syntax=docker/dockerfile:1.7
# tausik.tech static site — same pattern as SENAR (node build → nginx serve).

FROM node:22.14.0-alpine AS build

# Quiet, reproducible npm/pnpm: no audit/fund/notifier noise.
ENV NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FETCH_RETRIES=5 \
    NPM_CONFIG_FETCH_RETRY_MINTIMEOUT=20000 \
    NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT=120000

# Install deps first in an isolated layer. Unchanged site/package.json + lockfile
# → Docker reuses the entire pnpm install layer. BuildKit cache mount keeps the
# pnpm content-addressable store warm across builds on the same runner.
WORKDIR /repo/site
COPY site/package.json site/pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    corepack enable && \
    pnpm install --frozen-lockfile

# Pull in source content (docs/{en,ru}, docs/_generated, site/) — this layer
# changes often but no longer triggers a reinstall. docs/_generated/constants.json
# is required: HomeLanding.vue imports it for live numbers (review_agents_count,
# hooks_count, skills_core_count, mcp_main_tools, test_count, stacks_count).
WORKDIR /repo
COPY docs/en docs/en
COPY docs/ru docs/ru
COPY docs/_generated docs/_generated
COPY site/ site/

# VitePress build (prebuild hook syncs docs/{en,ru} → site/{docs,ru/docs} via sync-docs.mjs).
WORKDIR /repo/site
RUN pnpm build

FROM nginx:alpine
COPY --from=build /repo/site/.vitepress/dist /usr/share/nginx/html
COPY site/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
