# Stack: Ansible

## Testing & Validation
- **Linter**: `ansible-lint` (auto-enabled by Tausik on `ansible.cfg` / `playbooks/` / `roles/`)
- **Syntax check**: `ansible-playbook --syntax-check playbook.yml`
- **Dry run**: `ansible-playbook --check --diff` (show what would change)
- **Role tests**: `molecule` framework — actual VM/container runs
- **Schema**: `ansible-lint` covers it; for stricter, `ansible-doc-extractor` + JSON schema

## Review Checklist
- [ ] Tasks named meaningfully (`name:` field on every task)
- [ ] Idempotency: tasks must converge, not accumulate (e.g., `lineinfile` not `shell: echo >>`)
- [ ] Handlers used for restart-on-change; `notify:` chained correctly
- [ ] No `shell:` / `command:` when a module exists (`apt`, `service`, `template`)
- [ ] Secrets in `ansible-vault`, never plaintext in vars
- [ ] `become: yes` scoped to tasks needing it, not whole play
- [ ] Tags on tasks/blocks for selective runs (`--tags db,deploy`)
- [ ] `failed_when` / `changed_when` explicit when default heuristics wrong

## Conventions
- **Layout**: `playbooks/<name>.yml`, `roles/<role>/{tasks,handlers,templates,vars,defaults,meta}/main.yml`
- **Inventory**: separate file per environment (`inventory/prod`, `inventory/staging`)
- **Vars precedence**: defaults → group_vars → host_vars → playbook → CLI `-e`
- **Naming**: `snake_case` for vars, `kebab-case` for role names

## Common Pitfalls
- **YAML gotchas**: `yes`/`no`/`on`/`off` parsed as booleans — quote them when you mean strings
- **Loops with `with_items` are deprecated** — use `loop:` with `loop_control:`
- **Become escalation**: forgetting `become_user` defaults to root, not the user you wanted
- **Templates not idempotent** — `template:` is, but `lineinfile` with regex can drift
- **No policy-as-code shipped** — for compliance scans add OPA / Conftest as a custom gate
