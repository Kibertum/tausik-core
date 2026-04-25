# Stack: Terraform

## Testing & Validation
- **Built-in**: `terraform validate` (syntax + types), `terraform fmt -check`
- **Tausik gate**: `terraform-validate` (auto-enabled on `*.tf` / `*.tfvars`)
- **Plan testing**: `terratest` (Go), `kitchen-terraform`, `pytest-terraform`
- **Policy-as-code**: NOT included by default — add `checkov`, `tfsec`, or `Sentinel` as custom gate via `.tausik/config.json`
- **Run**: `terraform init -backend=false && terraform validate`

## Review Checklist
- [ ] No hardcoded credentials — use `var.` or `data` sources from a secrets manager
- [ ] State backend configured (S3 / GCS / Terraform Cloud), never local in shared repos
- [ ] `terraform.lock.hcl` committed (provider version pinning)
- [ ] Resources tagged consistently — `Environment`, `Owner`, `CostCenter`
- [ ] Module inputs typed (`type = string` etc.) and documented (`description`)
- [ ] No `count` + `for_each` mixing — pick one
- [ ] `lifecycle.prevent_destroy` on stateful resources (RDS, S3 with data)
- [ ] No `terraform apply -auto-approve` in CI without separate approval gate

## Conventions
- **File layout**: `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` per module
- **Naming**: `snake_case` resources, `PascalCase`/`kebab-case` for tags by convention
- **Module structure**: `modules/<name>/{main,variables,outputs}.tf`
- **State isolation**: separate workspaces or backends per environment

## Common Pitfalls
- **State drift**: someone edits in console — `terraform plan` shows diff but tempted to ignore. Reconcile or import.
- **Provider version drift**: `terraform init -upgrade` accidentally bumps majors. Pin in `versions.tf`.
- **Implicit dependencies**: `depends_on` needed when resource X uses runtime data from Y but has no direct ref
- **Sensitive outputs**: `sensitive = true` only hides from log — value still in state file (encrypt the backend)
- **Loops with side effects**: `for_each` with computed keys → "Invalid for_each argument" until first apply
