# Stack: Helm

## Testing & Validation
- **Linter**: `helm lint` (auto-enabled by Tausik on `Chart.yaml`)
- **Template render**: `helm template . --debug` — see what gets sent to the cluster
- **Diff**: `helm diff upgrade` (plugin) — review changes before applying
- **Dry run**: `helm install --dry-run --debug`
- **Schema validation**: `kubeval` / `kube-score` on rendered output (combine with `kubernetes` stack)

## Review Checklist
- [ ] `Chart.yaml` `version` bumped on every change, follows semver
- [ ] `values.yaml` has comments on every non-trivial setting
- [ ] No hardcoded image tags — `{{ .Values.image.tag | default .Chart.AppVersion }}`
- [ ] Resource limits + requests set (`resources.limits` + `resources.requests`)
- [ ] Probes configured: `livenessProbe`, `readinessProbe`, `startupProbe` where relevant
- [ ] Labels follow `app.kubernetes.io/*` convention (`name`, `version`, `managed-by`)
- [ ] Secrets via `Secret` references or external secret managers — never in `values.yaml`
- [ ] `_helpers.tpl` consolidates repeated label/annotation blocks

## Conventions
- **Layout**: `Chart.yaml` (metadata), `values.yaml` (defaults), `templates/*.yaml`, `charts/` (deps)
- **Naming**: chart names lowercase + hyphen
- **Values files**: `values.yaml` (defaults), `values-prod.yaml` etc. for env overrides
- **Subcharts**: prefer `dependencies:` in Chart.yaml over copying templates

## Common Pitfalls
- **Indentation in templates**: `nindent` vs `indent` — `nindent` adds newline first, almost always what you want
- **Empty values**: `{{ .Values.foo | default "bar" }}` doesn't catch empty string — use `| empty | ternary`
- **Resource hooks**: `helm.sh/hook` annotations run out-of-order with apply — read carefully
- **Rollback gotcha**: PVCs aren't removed on `helm uninstall` by default — delete manually
- **Templates can't read cluster state** — for that you need a controller, not Helm
