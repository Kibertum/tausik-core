# Stack: Docker

## Testing & Validation
- **Linter**: `hadolint` (auto-enabled by Tausik on `Dockerfile` / `Containerfile`)
- **Vulnerability scan**: NOT shipped — add `trivy`, `grype`, or `docker scout` as custom gate
- **Build test**: `docker build --no-cache --pull .` in CI
- **Image size**: `dive` to inspect layers, `docker history`
- **Compose validation**: `docker compose config -q`

## Review Checklist
- [ ] Multi-stage builds for compiled languages — final image has only runtime
- [ ] `USER` directive set (not running as root); UID/GID explicit
- [ ] `.dockerignore` covers `.git`, `node_modules`, secrets, build artifacts
- [ ] Pinned base image — `FROM python:3.11.7-slim`, not `:latest` or `:3`
- [ ] Layers ordered by change frequency (deps before code) for cache efficiency
- [ ] `HEALTHCHECK` defined for long-running services
- [ ] `LABEL` includes maintainer, version, source repo URL
- [ ] No secrets in build args or final image — use `--secret` mount or runtime env
- [ ] `COPY --chown=user:group` to avoid post-COPY chown layers
- [ ] `EXPOSE` documents intent, doesn't actually open ports

## Conventions
- **Filename**: `Dockerfile` (canonical) or `Containerfile` (Podman convention; both work in modern Docker)
- **Tag scheme**: `<service>:<version>` for releases, `<service>:<git-sha>` for CI builds
- **Compose vs Kubernetes**: compose for local dev only; production goes through K8s manifests

## Common Pitfalls
- **`apt-get update` without `&& apt-get install`** in same RUN → cache stales, packages stale
- **`COPY . .`** before installing deps → cache busted on every code change
- **CMD vs ENTRYPOINT confusion** — ENTRYPOINT sets the command, CMD sets default args
- **Signal handling**: shell-form CMD doesn't forward SIGTERM → use exec-form `["program", "arg"]`
- **Build context size**: forgetting `.dockerignore` ships gigabytes to daemon
- **Hadolint catches lint, NOT vulnerabilities** — Trivy/Grype required for CVE coverage
