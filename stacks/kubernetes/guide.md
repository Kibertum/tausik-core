# Stack: Kubernetes

## Testing & Validation
- **Schema validation**: `kubeval` (auto-enabled by Tausik on `k8s/` / `manifests/`)
- **Score / best-practice**: `kube-score` (add as custom gate)
- **Cluster-side**: `kubectl apply --dry-run=server` (validates against admission controllers)
- **Policy-as-code**: NOT shipped — add OPA Gatekeeper / Kyverno / Conftest as custom gate
- **E2E**: `kuttl`, `chainsaw` for declarative scenario tests

## Review Checklist
- [ ] Resource limits + requests on every container — no unbounded pods
- [ ] Probes: `livenessProbe`, `readinessProbe`, `startupProbe` where relevant
- [ ] No `latest` tags — pin image SHA or explicit version
- [ ] `securityContext`: `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, drop capabilities
- [ ] `NetworkPolicy` defined for pods that need egress restriction
- [ ] `PodDisruptionBudget` on multi-replica workloads
- [ ] HPA / VPA configured for autoscaling-eligible workloads
- [ ] Labels: `app.kubernetes.io/{name,instance,version,managed-by}`
- [ ] No `hostPath` volumes unless explicitly justified

## Conventions
- **Layout**: `k8s/<env>/<resource>.yaml` or `manifests/{base,overlays}/` for Kustomize
- **Naming**: lowercase + hyphen, no underscores
- **Namespaces**: per-team or per-env, never default in production
- **GitOps**: ArgoCD / Flux for cluster state — don't `kubectl apply` from laptops in prod

## Common Pitfalls
- **YAML anchors NOT supported** in plain manifests (Helm/Kustomize handle templating)
- **ConfigMap updates don't restart pods** — annotate Deployment with checksum or use Reloader
- **Service selectors**: must match Pod labels exactly — typos cause silent "no endpoints"
- **CRD ordering**: install CRDs first, then custom resources — apply ordering matters
- **Resource quotas**: hit them silently — pods stay Pending, no admission error in some configs
- **Schema validation only catches typos**, not policy — add OPA for "no privileged containers" rules
