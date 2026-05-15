# tausik.tech — VitePress site (dev guide)

> **Dev-only.** This README is excluded from the published site via `srcExclude` in `.vitepress/config.ts`. It is the contributor reference for the site itself.

## Stack

- **VitePress 1.6** — Markdown → static HTML, bilingual (EN at `/`, RU at `/ru/`)
- **Node 22 + pnpm 10.33** (managed by Corepack; pinned via `package.json#packageManager`)
- **nginx:alpine** in production (`Dockerfile` multi-stage build → `site/nginx.conf`)
- **Deploy**: internal CI pipeline (Docker build + nginx container), `tausik-site` on port `8900:80`

## Source of truth

Docs live in the repo root, not inside `site/`:

- `docs/en/*.md` — English documentation
- `docs/ru/*.md` — Russian documentation

`scripts/sync-docs.mjs` (run automatically by `pnpm predev` / `pnpm prebuild`) copies them into `site/docs/` and `site/ru/docs/` before each VitePress build. Both target folders are gitignored — never edit them by hand.

## Landing copy

- `site/index.md` — EN home (`layout: home` with VitePress `hero` + `features`)
- `site/ru/index.md` — RU home (parallel translation)
- `site/_archive/landing-snapshot.html` — frozen reference: Claude Design original landing export, kept for visual reference but not served

## Local dev

```bash
cd site
corepack pnpm install            # one-off
corepack pnpm dev                # http://localhost:5173/
corepack pnpm build              # site/.vitepress/dist/
corepack pnpm preview            # http://localhost:4173/
```

`predev` / `prebuild` automatically run `scripts/sync-docs.mjs`. To sync without building: `corepack pnpm sync`.

## Local Docker

```bash
# From repo root
DOCKER_BUILDKIT=1 docker build -t tausik-site:test .
docker run -d --name tausik-site-test -p 8900:80 tausik-site:test
curl http://localhost:8900/                 # EN home
curl http://localhost:8900/ru/              # RU home
curl http://localhost:8900/docs/quickstart  # docs page
docker stop tausik-site-test && docker rm tausik-site-test
```

## CI/CD

The repo's CI config (root, intentionally not detailed here) defines a two-stage pipeline on `main` only:

1. **build** — `docker build --cache-from $IMAGE_LATEST` → push `:short-sha` and `:latest` to the container registry.
2. **deploy** — pull image, recreate `tausik-site` container on host port `8900:80`, smoke `curl http://localhost:8900/`.

DNS: `tausik.tech` points at the reverse proxy on the deploy host. The container exposes port 80; the proxy terminates TLS and forwards to host port 8900.

## Known limitations (intentional, tracked as TAUSIK memory)

- `lastUpdated: false` — VitePress wants `git log` per page; the Docker build stage doesn't ship git. See gotcha #127.
- `ignoreDeadLinks: true` — 103 dead refs in source docs (relative paths to `scripts/*.py`, cross-language refs). See gotcha #126.

Both are eligible for a follow-up cleanup pass; neither blocks deploy.

## GitHub mirror

The site is **not** deployed via GitHub Actions or Pages. The mirror at `github.com/Kibertum/tausik-core` ships the source files as part of the codebase but no build/deploy automation is registered there. Canonical deploy is handled by the internal CI pipeline.
